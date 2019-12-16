# This is an old, ugly script - to be cleaned.


import os
import copy
import shutil
import pathlib
from datetime import datetime

from matplotlib.dates import date2num, num2date

from ._copy_include_files import copy_include_files
from ._section_dictionary import section_dictionary
from ._master_datafile import master_datafile
from ._merge_schedule import merge_schedule

MODULE_FOLDER = pathlib.Path(__file__).parent.absolute()


def create_rc_model(
    outputfolder,
    casename,
    schfile,
    summaryfile,
    datafiles,
    slavenames,
    cpus,
    rptrst,
    wconprod,
    slavesch=None,
):

    # Create output directory if it doesn't already exist:

    if not os.path.isdir(outputfolder):
        os.makedirs(outputfolder)
        print("Created empty RC model directory (" + outputfolder + ")")

    # Create directory tree structure:

    os.makedirs(outputfolder + "/model")
    os.makedirs(outputfolder + "/include/runspec")

    # Parse the GRUPTREE in the user given master .sch file:

    f = open(schfile, "r", encoding="utf-8", errors="ignore")
    content = f.readlines()
    f.close()

    content = [x.strip() for x in content]

    IN_GRUPTREE = False
    IN_DATES = False

    MASTER_GRUPTREE = {}

    numdate = 0

    for line in content:

        line = line.partition("--")[0].strip()

        ############## Process WCONPROD keywords #############

        if line == "GRUPTREE":
            IN_GRUPTREE = True
        elif IN_GRUPTREE and line.startswith("/"):
            IN_GRUPTREE = False
        elif IN_GRUPTREE and "/" in line:
            group_name1 = line.strip().split()[0].replace("'", "")
            group_name2 = line.strip().split()[1].replace("'", "")

            for group_name in [group_name1, group_name2]:
                if not group_name in MASTER_GRUPTREE:
                    MASTER_GRUPTREE[group_name] = {
                        "numdate": numdate,
                        "warning_given": False,
                    }

        ############## Process DATES keywords ##############

        elif line == "DATES":
            IN_DATES = True
        elif IN_DATES and line.startswith("/"):
            IN_DATES = False
        elif IN_DATES and "/" in line:

            date = line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()

            if not ":" in date:
                date += " 00:00:00"

            numdate = date2num(datetime.strptime(date, "%d %b %Y %H:%M:%S"))

    # Parse the data in slave .sch file (if given by user):

    slave_keywords = {}

    if slavesch is not None:
        f = open(args.slavesch, "r")
        content = f.readlines()
        f.close()

        content = [x.strip() for x in content]

        IN_DATES = False

        numdate = 0

        for j, line in enumerate(content):

            line = line.partition("--")[0].strip()
            comment = line.partition("--")[1].strip()

            ############## Process DATES keywords ##############

            if line == "DATES":
                IN_DATES = True
            elif IN_DATES and line.startswith("/"):
                IN_DATES = False
            elif IN_DATES and "/" in line:

                date = (
                    line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()
                )

                if not ":" in date:
                    date += " 00:00:00"

                numdate = date2num(datetime.strptime(date, "%d %b %Y %H:%M:%S"))

            else:
                if not numdate in slave_keywords:
                    slave_keywords[numdate] = "" + "\n"
                else:
                    slave_keywords[numdate] += content[j] + " " + comment + "\n"

    # Create the different slave .DATA-files and copy over include files:

    GRUPMAST = {}
    GRUPTREE = {}
    GCONPROD = {}
    GCONINJE = {}
    PARALLEL = {}

    START_NUMDATE = {}
    KEYWORD_LINES = {}

    EXTRA_DATES = {}

    INJECTORS = set()

    for i, standalone in enumerate(datafiles):

        GRUPSLAV = {slavenames[i]: {}}
        KEYWORD_LINES[slavenames[i]] = {}
        PARALLEL[slavenames[i]] = False
        MISSING_WCON = set([])

        SLAVE_SCH = copy.copy(slave_keywords)
        try:
            f = open(standalone, "r")
            content = f.readlines()
            f.close()
        except:
            raise RuntimeError("Could not read standalone .DATA file " + standalone)

        (content, _, _) = copy_include_files(
            standalone,
            schfile,
            section_dictionary(content),
            slavenames[i],
            0,
            {"prev_numdate": 0, "file": None, "linenumber": 0},
            START_NUMDATE,
            standalone,
            KEYWORD_LINES,
            EXTRA_DATES,
            outputfolder,
            PARALLEL,
            cpus,
            slavenames,
            rptrst,
            GRUPTREE,
            MASTER_GRUPTREE,
            GRUPMAST,
            MISSING_WCON,
            SLAVE_SCH,
            GCONPROD,
            wconprod,
        )

        # DO CHANGES TO THE CONTENT

        f = open(
            outputfolder + "/model/" + casename + "_" + slavenames[i] + ".DATA", "w",
        )
        f.write("\n".join(content))
        f.close()

        if len(MISSING_WCON) > 0:
            print(
                "WARNING: The following wells in standalone "
                + slavenames[i]
                + " do not have a WCONPROD or WCONINJE: "
                + ", ".join(sorted(list(MISSING_WCON)))
                + ". You should add a WCONPROD and/or WCONINJE for these wells and run standalones2rc again (standalones2rc only creates the RC required GCONPROD/GCONINJE entries for each WCONPROD/WCONINJE it meets in the standalones)."
            )

        print("Copied over all INCLUDE files to be used for slave " + slavenames[i])

    # Create the different automatically created include files:

    for i, standalone in enumerate(datafiles):

        f = open(
            outputfolder
            + "/include/runspec/"
            + slavenames[i].lower()
            + ".welldims.inc",
            "w",
        )
        f.write("WELLDIMS\n ")
        for argument in KEYWORD_LINES[slavenames[i]]["WELLDIMS"]["arguments"]:
            f.write(str(argument) + " ")
        f.write(" /\n")
        f.close()

    ##################################
    ## CREATE THE MASTER .DATA FILE ##
    ##################################

    f = open(outputfolder + "/model/" + casename + "_MASTER.DATA", "w")
    f.write(
        "".join(
            master_datafile(
                summaryfile,
                outputfolder,
                START_NUMDATE,
                casename,
                slavenames,
                cpus,
                MASTER_GRUPTREE,
            )
        )
    )
    f.close()

    # Create the GRUPTREE keyword in a schedule file

    f = open(outputfolder + "/include/schedule/master.gruptree.sch", "w")
    f.write(
        "--+ The content in this file has already automatically been merged into ./master.sch\n\n"
    )

    for numdate in sorted(GRUPTREE):
        if numdate > 0:
            datestring = num2date(numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
            if "00:00:00" in datestring:
                datestring = datestring[: datestring.find(" 00:00:00")]
            datestring = "DATES\n  " + datestring + "/\n/\n\n"
            f.write(datestring)

        f.write("\n\n-- added by standalones2rc:\nGRUPTREE\n")
        for (group1, group2) in GRUPTREE[numdate]:
            f.write("  '" + group1 + "' '" + group2 + "' /\n")
        f.write("/\n\n")

        f.write("\n\n-- added by standalones2rc:\nGRUPNET\n")
        for (group1, group2) in GRUPTREE[numdate]:
            f.write("  '" + group1 + "'  1*  9999 /\n")
        f.write("/\n\n")

        GNETINJE = ""
        for (group1, group2) in GRUPTREE[numdate]:
            if group1 in INJECTORS:
                GNETINJE += "  '" + group1 + "' 'GAS'  1*  9999 /\n"

        if GNETINJE != "":
            f.write("\n\n-- added by standalones2rc:\nGNETINJE\n" + GNETINJE + "/\n\n")

    f.close()

    # Create the GCONPROD keyword in a schedule file

    f = open(outputfolder + "/include/schedule/master.gconprod.sch", "w")
    f.write(
        "--+ The content in this file has already automatically been merged into ./master.sch\n\n"
    )

    for numdate in sorted(GCONPROD):
        if numdate > 0:
            datestring = num2date(numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
            if "00:00:00" in datestring:
                datestring = datestring[: datestring.find(" 00:00:00")]
            datestring = "DATES\n  " + datestring + "/\n/\n\n"
            f.write(datestring)

        f.write("\n\n-- added by standalones2rc:\nGCONPROD\n")
        for group in GCONPROD[numdate]:
            f.write("  '" + group + "' 'FLD' 7* 'POTN' /\n")
        f.write("/\n\n")

    f.close()

    # Create the GCONINJE keyword in a schedule file

    f = open(outputfolder + "/include/schedule/master.gconinje.sch", "w")
    f.write(
        "--+ The content in this file has already automatically been merged into ./master.sch\n\n"
    )

    for numdate in sorted(GCONINJE):
        if numdate > 0:
            datestring = num2date(numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
            if "00:00:00" in datestring:
                datestring = datestring[: datestring.find(" 00:00:00")]
            datestring = "DATES\n  " + datestring + "/\n/\n\n"
            f.write(datestring)

        f.write("\n\n-- added by standalones2rc:\nGCONINJE\n")
        for (group, phase) in GCONINJE[numdate]:
            f.write("  '" + group + "' '" + phase + "'  'FLD'  5*  1  'RATE' /\n")
        f.write("/\n\n")

    f.close()

    # Create the GRUPMAST keywords in a schedule file:

    numdates = {}
    for well_name in GRUPMAST:
        if not GRUPMAST[well_name]["numdate"] in numdates:
            numdates[GRUPMAST[well_name]["numdate"]] = []

        numdates[GRUPMAST[well_name]["numdate"]].append(well_name)

    f = open(outputfolder + "/include/schedule/master.grupmast.sch", "w")

    for numdate in sorted(numdates):
        if numdate > 0:
            datestring = num2date(numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
            if "00:00:00" in datestring:
                datestring = datestring[: datestring.find(" 00:00:00")]
            datestring = "DATES\n  " + datestring + "/\n/\n\n"
            f.write(datestring)

        f.write("-- added by standalones2rc:\nGRUPMAST\n")
        for well_name in numdates[numdate]:
            f.write(
                "  '"
                + well_name
                + "' '"
                + GRUPMAST[well_name]["slavename"]
                + "' '"
                + well_name
                + "' 0.1 /\n"
            )

        f.write("/\n\n")

    f.close()

    # Merge the different schedule files:

    inputfiles = [
        outputfolder + "/include/schedule/master.gruptree.sch",
        outputfolder + "/include/schedule/master.grupmast.sch",
        outputfolder + "/include/schedule/master.gconprod.sch",
        outputfolder + "/include/schedule/master.gconinje.sch",
        schfile,
    ]

    merge_schedule(inputfiles, outputfolder + "/include/schedule/master.sch")

    #####################################
    # CREATE DUMMY MASTER INCLUDE FILES #
    #####################################

    shutil.copy(
        MODULE_FOLDER / "static" / "master_dummy_solution.inc",
        outputfolder + "/include/solution/master.dummy.inc",
    )
    shutil.copy(
        MODULE_FOLDER / "static" / "master_dummy_grid.inc",
        outputfolder + "/include/grid/master.dummy.inc",
    )
    shutil.copy(
        MODULE_FOLDER / "static" / "master_dummy_props.inc",
        outputfolder + "/include/props/master.dummy.inc",
    )
