import os
import sys
import shutil
import jinja2
import getpass
from datetime import datetime

import numpy as np
from matplotlib.dates import num2date

template_environment = jinja2.Environment(  # nosec
    loader=jinja2.PackageLoader("standalones2rc", "templates"),
    undefined=jinja2.StrictUndefined,
    autoescape=False,
)

master_template = template_environment.get_template("RC_MASTER.DATA.jinja2")


def master_datafile(
    summaryfile,
    outputfolder,
    START_NUMDATE,
    casename,
    slavenames,
    cpus,
    MASTER_GRUPTREE,
):

    summary_filename = os.path.basename(summaryfile)
    if not summary_filename.startswith("master."):
        summary_filename = "master." + summary_filename
    shutil.copyfile(summaryfile, outputfolder + "/include/summary/" + summary_filename)

    master_start_numdate = np.inf
    for slave in START_NUMDATE:
        if START_NUMDATE[slave] < master_start_numdate:
            master_start_numdate = START_NUMDATE[slave]

    datestring = num2date(master_start_numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
    if "00:00:00" in datestring:
        datestring = datestring[: datestring.find(" 00:00:00")]

    content = master_template.render(
        {
            "user": getpass.getuser(),
            "datetime_now": datetime.now().strftime("%d %B %Y"),
            "command": f"cd { os.getcwd() }; standalones2rc { ' '.join(sys.argv[1:]) }",
            "start_date": datestring,
            "case_name": casename,
            "summary_filename": summary_filename,
            "number_of_master_groups": str(len(MASTER_GRUPTREE)),
        }
    ).split("\n")

    IN_SCHEDULE = False

    SCHEDULE = content.index("SCHEDULE") + 1

    #######################################
    # ADD CHANGES TO THE SCHEDULE SECTION #
    #######################################

    SLAVES = "\n\nSLAVES\n"

    for i in range(len(slavenames)):
        SLAVES += (
            " '"
            + slavenames[i]
            + "'    '"
            + casename
            + "_"
            + slavenames[i]
            + "'    '*'    './'      "
            + str(cpus[i])
            + " /\n"
        )

    SLAVES += "/\n\n"

    content = content[:SCHEDULE] + [SLAVES] + content[SCHEDULE:]

    return "\n".join(content)
