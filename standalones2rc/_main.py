# UNRESOLVED ISSUES:
# 	* Issues when slavesch has several dates inbetween two dates in Standalone input.

# This is an old, ugly script - to be cleaned.

import argparse
import shutil
import os
import numpy as np
import sys
import getpass
from datetime import datetime
import copy

from matplotlib.dates import strpdate2num, num2date

converter = strpdate2num("%d %b %Y %H:%M:%S")

master_template = (
    "-- Created by "
    + getpass.getuser()
    + " on "
    + datetime.now().strftime("%d %B %Y")
    + " using the following command:\n-- cd "
    + os.getcwd()
    + "; standalones2rc "
    + " ".join(sys.argv[1:])
    + """

--=======
RUNSPEC
--=======

TITLE
 '__CASE__NAME__'

DIMENS
 1 1 1 /

METRIC

OIL
WATER
GAS
DISGAS
VAPOIL

START
 __START__DATE__ /

--NOSIM

TABDIMS
 1  1  37  60  1*  60  4*  35 /

WELLDIMS
 1* 1*  __NUMBER__OF__MASTER__GROUPS__ /

VFPPDIMS
 70 15 10 15 15 700 /

VFPIDIMS
 20  20  600 /

ACTDIMS
-- MxActions  MxLines  MxLineLen   MxConditions
       120     1000       128          10 /

UDQDIMS
 12 12 2 150 2 2 0 2 /

UDQPARAM
 2 1e19 -1.0 /

UDADIMS
 100 1000 /

SMRYDIMS
 30000 /

ENDSCALE
 2* 25 /

NSTACK             
 25 /

UNIFIN
UNIFOUT

MESSAGES
 2* 2000 2*
 2* 2000  100000000 /

MSGFILE
 0 /

--=======
GRID
--=======

INCLUDE
 '../include/grid/master.dummy.inc' /

GRIDFILE
 0 1 /

--=======
PROPS
--=======

INCLUDE
 '../include/props/master.dummy.inc' /

--=======
SOLUTION
--=======

INCLUDE
 '../include/solution/master.dummy.inc' /

--=======
SUMMARY
--=======

INCLUDE
 '../include/summary/__SUMMARY__FILE__' /

--=======
SCHEDULE
--=======

INCLUDE
 '../include/schedule/master.sch' /

END
"""
)


####################
# HELPER FUNCTIONS #
####################


def section_dictionary(content):
    # Returns a dictionary which gives the current section given a line number in the .DATA file

    content = [x.strip() for x in content]

    sections = [
        "RUNSPEC",
        "GRID",
        "EDIT",
        "PROPS",
        "REGIONS",
        "SOLUTION",
        "SUMMARY",
        "SCHEDULE",
    ]

    dictionary = {}

    for section in sections:
        if content.count(section) > 0:
            dictionary[content.index(section)] = section

    current_section = None

    for i in range(len(content)):
        if i in dictionary:
            current_section = dictionary[i]

        dictionary[i] = current_section

    return dictionary


def copy_include_files(filename, section, slavename, current_numdate, prev_numdate):

    # Copies the INCLUDE files in filename (is called recursively in order to accound for deeply nested INCLUDE files)

    try:
        f = open(filename, "r")
        content = f.readlines()
        f.close()
    except:
        raise RuntimeError("Could not read INCLUDE file " + filename)

    content = [x.strip() for x in content]

    IN_PARALLEL = False
    IN_INCLUDE = False
    IN_WELSPECS = False
    IN_DATES = False
    IN_WELLDIMS = False
    IN_GRUPNET = False
    IN_GCONPROD = False
    IN_WCONPROD = False
    IN_WCONINJE = False
    IN_WCONINJH = False
    IN_START = False
    IN_RPTRST = False
    IN_GEFAC = False
    IN_WEFAC = False

    for j, line in enumerate(content):

        if isinstance(section, dict):
            current_section = section[j]

        else:
            current_section = section

        if current_section == "GRID" and not PARALLEL[slavename]:
            PARALLEL[slavename] = True
            if args.cpus[args.slavenames.index(slavename)] > 1:
                content[j] = (
                    "PARALLEL\n "
                    + str(args.cpus[args.slavenames.index(slavename)])
                    + " / -- added by standalones2rc\n\n"
                    + content[j]
                )

        if "--" in line:
            comment = "--" + line.partition("--")[1]
        else:
            comment = ""

        line = line.partition("--")[0].strip()

        ############## Process INCLUDE keywords ##############

        if line == "INCLUDE":
            IN_INCLUDE = True
        elif IN_INCLUDE and "/" in line:
            old_path = line[: line.rfind("/")].replace("'", "").strip()

            if old_path[0] != "/":  # Not absolute path
                old_path = os.path.dirname(standalone) + "/" + old_path

            old_filename = os.path.basename(old_path)

            if not old_filename.startswith(slavename.lower() + "."):
                new_filename = slavename.lower() + "." + old_filename
            else:
                new_filename = old_filename

            new_path = "../include/" + current_section.lower() + "/" + new_filename

            content[j] = "'" + new_path + "' / " + comment

            IN_INCLUDE = False

            # Ensures we include deeply nested INCLUDE files:

            (_, current_numdate, prev_numdate) = copy_include_files(
                old_path, current_section, slavename, current_numdate, prev_numdate
            )

        ############## Process WELSPECS keywords ##############

        elif line == "WELSPECS":
            IN_WELSPECS = True
            WELSPECS_LINE_INDEX = j
            GRUPSLAV = "\n\n--added by standalones2rc:\nGRUPSLAV\n"  # GRUPSLAV keyword to be added just after WELSPECS keyword in slave
            GRUPTREE_SLAVE = "\n--added by standalones2rc:\nGRUPTREE\n"  # GRUPTREE keyword to be added just before WELSPECS keyword in slave
            GRUPNET_SLAVE = "\n--added by standalones2rc:\nGRUPNET\n"  # GRUPNET keyword to be added just before WELSPECS keyword in slave

        elif IN_WELSPECS and line.startswith("/"):
            IN_WELSPECS = False

            if GRUPSLAV != "\n\n--added by standalones2rc:\nGRUPSLAV\n":
                content[j] = content[j] + GRUPSLAV + "/\n\n"

                # Adding an extra date is a workaround due to an Eclipse bug when there are too long time between two dates with GRUPSLAV inbetween:
                if current_numdate - prev_numdate["prev_numdate"] > 1:
                    prev_numdate["prev_numdate"] = current_numdate - 1
                    if not prev_numdate["file"] in EXTRA_DATES:
                        EXTRA_DATES[prev_numdate["file"]] = []

                    EXTRA_DATES[prev_numdate["file"]].append(
                        {
                            "linenumber": prev_numdate["linenumber"],
                            "numdate": current_numdate - 1,
                        }
                    )

            content[WELSPECS_LINE_INDEX] = (
                GRUPTREE_SLAVE
                + "/\n\n"
                + GRUPNET_SLAVE
                + "/\n\n"
                + content[WELSPECS_LINE_INDEX]
            )

        elif IN_WELSPECS and "/" in line:
            data = line.replace("'", "").split()

            wellname = data[0].strip()
            groupname = data[1].strip()

            if not current_numdate in GRUPTREE:
                GRUPTREE[current_numdate] = []

            GRUPTREE[current_numdate].append((wellname, groupname))
            GRUPTREE_SLAVE += "  '" + wellname + "' '" + groupname + "' /\n"
            GRUPNET_SLAVE += (
                "  '"
                + wellname
                + "' 1 / -- fixed dummy pressure (required by GRUPSLAV/GRUPMAST)\n"
            )

            if not groupname in MASTER_GRUPTREE:
                print("WARNING: Group " + groupname + " is used in standalone corresponding to slave " + slavename + ", however this group is not mentioned in the GRUPTREE in " + args.schfile + ". If not corrected, this will give an ERROR in Eclipse.")

                MASTER_GRUPTREE[groupname] = {"numdate": -1, "warning_given": True}

            elif MASTER_GRUPTREE[groupname]["numdate"] > current_numdate:
                print("WARNING: Group " + groupname + " is used in standalone corresponding to slave " + slavename + " before it is defined in the GRUPTREE in " + args.schfile + ". If not corrected, this will give an ERROR in Eclipse.")

                MASTER_GRUPTREE[groupname]["warning_given"] = True

            # Change WELSPECS arguments for this well such that group name is the same as the well name:
            content[j] = " '" + wellname + "' '" + wellname + "'"
            for string in data[2:]:
                content[j] += " " + string
            content[j] += " / " + comment + "\n"

            # Add well/group to GRUPMAST. Raise error if well is already present in another slave/standalone.
            if not wellname in GRUPMAST:
                MISSING_WCON.add(wellname)

                KEYWORD_LINES[slavename]["WELLDIMS"]["arguments"][
                    2
                ] += 1  # Increase the number of GROUPS in the slave by 1
                MASTER_GRUPTREE[wellname] = {}

                GRUPMAST[wellname] = {
                    "numdate": current_numdate,
                    "slavename": slavename,
                    "groupname": groupname,
                }
                GRUPSLAV += "  '" + wellname + "' '" + wellname + "' /\n"
            elif GRUPMAST[wellname]["slavename"] != slavename:
                raise RuntimeError(
                    "Well "
                    + wellname
                    + " present in both "
                    + slavename
                    + " and "
                    + GRUPMAST[wellname]["slavename"]
                    + ". Please make sure it only is defined in one of them."
                )

        ############## Process RPTRST keyword ##############

        elif line == "RPTRST" and not args.rptrst:
            IN_RPTRST = True
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_RPTRST and "/" in line:
            IN_RPTRST = False
            content[j] = "-- commented out by standalones2rc: " + content[j]

        ############## Process START keyword ##############

        elif line == "START":
            IN_START = True
        elif IN_START and "/" in line:
            IN_START = False

            start_date = (
                line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()
            )

            if not ":" in start_date:
                start_date += " 00:00:00"

            START_NUMDATE[slavename] = converter(start_date)

        ############## Process DATES keywords ##############

        elif line == "DATES":
            IN_DATES = True
            FIRST_DATE = (True, j)
        elif IN_DATES and line.startswith("/"):
            IN_DATES = False
        elif IN_DATES and "/" in line:

            date = line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()

            if not ":" in date:
                date += " 00:00:00"

            prev_numdate = current_numdate
            prev_numdate = {
                "prev_numdate": prev_numdate,
                "file": filename,
                "linenumber": j,
            }

            current_numdate = converter(date)

            for numdate in sorted(SLAVE_SCH):
                if (
                    prev_numdate["prev_numdate"] == numdate
                    and numdate < current_numdate
                ):
                    if FIRST_DATE[0]:
                        content[FIRST_DATE[1]] = (
                            SLAVE_SCH[numdate] + "\n" + content[FIRST_DATE[1]]
                        )
                    else:
                        content[j] = (
                            "/\n" + SLAVE_SCH[numdate] + "\n\nDATES\n" + content[j]
                        )

                    del SLAVE_SCH[numdate]

                elif (
                    prev_numdate["prev_numdate"] < numdate and numdate < current_numdate
                ):

                    datestring = (
                        num2date(numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
                    )
                    if "00:00:00" in datestring:
                        datestring = datestring[: datestring.find(" 00:00:00")]

                    if FIRST_DATE[0]:
                        content[FIRST_DATE[1]] = (
                            "DATES\n"
                            + datestring
                            + "/\n/\n\n"
                            + SLAVE_SCH[numdate]
                            + "\n"
                            + content[FIRST_DATE[1]]
                        )
                    else:
                        content[j] = (
                            datestring
                            + "/\n/\n\n"
                            + SLAVE_SCH[numdate]
                            + "\n\nDATES\n"
                            + content[j]
                        )

                    del SLAVE_SCH[numdate]

            FIRST_DATE = (False, None)

        ############## Process GCONPROD keywords #############

        elif line == "GCONPROD":
            IN_GCONPROD = True
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_GCONPROD and line == "/":
            IN_GCONPROD = False
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_GCONPROD:
            content[j] = "-- commented out by standalones2rc: " + content[j]

        ############## Process GEFAC keywords #############

        elif line == "GEFAC":
            IN_GEFAC = True
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_GEFAC and line == "/":
            IN_GEFAC = False
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_GEFAC:
            content[j] = "-- commented out by standalones2rc: " + content[j]

        ############## Process WEFAC keywords #############

        elif line == "WEFAC":
            IN_WEFAC = True
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_WEFAC and line == "/":
            IN_WEFAC = False
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_WEFAC:
            content[j] = "-- commented out by standalones2rc: " + content[j]

        ############## Process WCONPROD keywords #############

        elif line == "WCONPROD":
            IN_WCONPROD = True
        elif IN_WCONPROD and line.startswith("/"):
            IN_WCONPROD = False
        elif IN_WCONPROD and "/" in line:
            if not current_numdate in GCONPROD:
                GCONPROD[current_numdate] = []

            data = line.strip().split()
            dummy_well_group = data[0].replace("'", "")
            GCONPROD[current_numdate].append(dummy_well_group)

            MISSING_WCON.discard(dummy_well_group)

            if not args.wconprod and not "GRUP" in data[2]:
                control_mode = data[2]
                if "*" in data[2] and data[2] != "*":
                    data[2] = "'GRUP' " + str(int(data[2][0]) - 1) + "*"
                else:
                    data[2] = "'GRUP'"

                content[j] = (
                    " ".join(data)
                    + " "
                    + comment
                    + " -- control mode changed to 'GRUP' by standalones2rc"
                )

        ############## Process WCONINJE keywords #############

        elif line == "WCONINJE":
            IN_WCONINJE = True
        elif IN_WCONINJE and line.startswith("/"):
            IN_WCONINJE = False
        elif IN_WCONINJE and "/" in line:
            if not current_numdate in GCONPROD:
                GCONPROD[current_numdate] = []
            if not current_numdate in GCONINJE:
                GCONINJE[current_numdate] = []

            dummy_well_group = line.strip().split()[0].replace("'", "")
            phase = line.strip().split()[1].replace("'", "")

            INJECTORS.add(dummy_well_group)

            GCONPROD[current_numdate].append(dummy_well_group)
            GCONINJE[current_numdate].append((dummy_well_group, phase))

            MISSING_WCON.discard(dummy_well_group)

        ############## Process WCONINJH keywords #############

        elif line == "WCONINJH":
            IN_WCONINJH = True
        elif IN_WCONINJH and line.startswith("/"):
            IN_WCONINJH = False
        elif IN_WCONINJH and "/" in line:
            dummy_well_group = line.strip().split()[0].replace("'", "")

            INJECTORS.add(dummy_well_group)

        ############## Process GRUPNET keywords ##############

        elif line == "GRUPNET":
            IN_GRUPNET = True
            content[j] = "--" + content[j] + " " + comment
        elif IN_GRUPNET and line == "/":
            IN_GRUPNET = False
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_GRUPNET:
            content[j] = "-- commented out by standalones2rc: " + content[j]

        ############## Process WELLDIMS keyword ##############

        elif line == "WELLDIMS":
            IN_WELLDIMS = True
            KEYWORD_LINES[slavename]["WELLDIMS"] = {
                "filename": filename,
                "start_index": j,
            }
        elif IN_WELLDIMS and "/" in line:
            KEYWORD_LINES[slavename]["WELLDIMS"]["end_index"] = j
            KEYWORD_LINES[slavename]["WELLDIMS"]["arguments"] = (
                line[: line.find("/")].strip().split()
            )
            KEYWORD_LINES[slavename]["WELLDIMS"]["arguments"][2] = int(
                KEYWORD_LINES[slavename]["WELLDIMS"]["arguments"][2]
            )  # Maximum number of groups

            IN_WELLDIMS = False

        ############## Process PARALLEL keyword ##############

        elif line == "PARALLEL":
            IN_PARALLEL = True

            if args.cpus[args.slavenames.index(slavename)] == 1:
                content[j] = "-- commented out by standalones2rc: " + content[j]

            PARALLEL[args.slavenames[i]] = True

        elif IN_PARALLEL and "/" in line:
            data = line.split()

            if args.cpus[args.slavenames.index(slavename)] == 1:
                content[j] = "-- commented out by standalones2rc: " + content[j]
            else:
                data[0] = str(args.cpus[args.slavenames.index(slavename)])
                content[j] = (
                    " "
                    + " ".join(data)
                    + " "
                    + comment
                    + " -- changed by standalones2rc"
                )

            IN_PARALLEL = False

    if (
        "WELLDIMS" in KEYWORD_LINES[slavename]
        and KEYWORD_LINES[slavename]["WELLDIMS"]["filename"] == filename
    ):
        content[
            KEYWORD_LINES[slavename]["WELLDIMS"]["start_index"] : KEYWORD_LINES[
                slavename
            ]["WELLDIMS"]["end_index"]
            + 1
        ] = ["INCLUDE\n '../include/runspec/" + slavename.lower() + ".welldims.inc' /"]

    if filename in EXTRA_DATES:
        for extra_date in EXTRA_DATES[filename]:
            if START_NUMDATE[slavename] < extra_date["numdate"]:
                datestring = (
                    num2date(extra_date["numdate"])
                    .strftime("%d '%b' %Y %H:%M:%S")
                    .upper()
                )
                if "00:00:00" in datestring:
                    datestring = datestring[: datestring.find(" 00:00:00")]
                datestring = datestring + " / -- added by standalones2rc\n"

                content[extra_date["linenumber"]] = (
                    datestring + content[extra_date["linenumber"]]
                )

    if not isinstance(section, dict):
        old_filename = os.path.basename(filename)

        if not old_filename.startswith(slavename.lower() + "."):
            new_filename = slavename.lower() + "." + old_filename
        else:
            new_filename = old_filename

        if not os.path.isdir(args.outputfolder + "/include/" + current_section.lower()):
            os.makedirs(args.outputfolder + "/include/" + current_section.lower())

        new_path = "../include/" + current_section.lower() + "/" + new_filename

        f = open(args.outputfolder + "/include/" + new_path, "w")
        f.write("\n".join(content))
        f.close()

    return (content, current_numdate, prev_numdate)


def master_datafile():

    summary_filename = os.path.basename(args.summaryfile)
    if not summary_filename.startswith("master."):
        summary_filename = "master." + summary_filename
    shutil.copyfile(
        args.summaryfile, args.outputfolder + "/include/summary/" + summary_filename
    )

    master_start_numdate = np.inf
    for slave in START_NUMDATE:
        if START_NUMDATE[slave] < master_start_numdate:
            master_start_numdate = START_NUMDATE[slave]

    datestring = num2date(master_start_numdate).strftime("%d '%b' %Y %H:%M:%S").upper()
    if "00:00:00" in datestring:
        datestring = datestring[: datestring.find(" 00:00:00")]

    content = (
        master_template.replace("__START__DATE__", datestring)
        .replace("__CASE__NAME__", args.casename)
        .replace("__SUMMARY__FILE__", summary_filename)
        .replace("__NUMBER__OF__MASTER__GROUPS__", str(len(MASTER_GRUPTREE)))
        .split("\n")
    )

    IN_SCHEDULE = False

    # content = [x.strip() for x in content]

    SCHEDULE = content.index("SCHEDULE") + 1

    #######################################
    # ADD CHANGES TO THE SCHEDULE SECTION #
    #######################################

    SLAVES = "\n\nSLAVES\n"

    for i in range(len(args.slavenames)):
        SLAVES += (
            " '"
            + args.slavenames[i]
            + "'    '"
            + args.casename
            + "_"
            + args.slavenames[i]
            + "'    '*'    './'      "
            + str(args.cpus[i])
            + " /\n"
        )

    SLAVES += "/\n\n"

    content = content[:SCHEDULE] + [SLAVES] + content[SCHEDULE:]

    return "\n".join(content)


###################
# Parse arguments #
###################

def main():
    parser = argparse.ArgumentParser(
        description="Creates a RC (Reservoir Coupled) model from different stand alone models."
    )

    parser.add_argument("outputfolder", type=str, help="Output directory for the RC model.")
    parser.add_argument("casename", type=str, help="Case name (without .DATA extension).")
    parser.add_argument("schfile", type=str, help="Master schedule file.")
    parser.add_argument("summaryfile", type=str, help="Master summary file.")
    parser.add_argument(
        "--datafiles",
        type=str,
        nargs="+",
        help="Path to standalone .DATA files.",
        required=True,
    )
    parser.add_argument(
        "--slavenames",
        type=str,
        nargs="+",
        help="Names of the different slaves in the RC model.",
        required=True,
    )
    parser.add_argument(
        "--cpus",
        type=int,
        nargs="+",
        help="Number of CPUs to be used for the different slaves.",
        required=True,
    )
    parser.add_argument(
        "--rptrst",
        action="store_true",
        help="Keep RPTRST keywords from the standalone input.",
        default=False,
    )
    parser.add_argument(
        "--wconprod",
        action="store_true",
        help="Keep original item 3 in WCONPRODs in slaves (i.e. do not change to 'GRUP').",
        default=False,
    )
    parser.add_argument(
        "--slavesch",
        type=str,
        help="File containing additional schedule keywords for the slaves.",
        default=None,
    )

    args = parser.parse_args()

    args.slavenames = [x.upper().replace("'", "") for x in args.slavenames]

    if args.outputfolder[-1] == "/":
        args.outputfolder = args.outputfolder[:-1]

    if not len(args.datafiles) == len(args.slavenames):
        raise ValueError(
            'The arguments "datafiles" and "slavenames" must have the same number of entries.'
        )

    if not len(args.datafiles) == len(args.cpus):
        raise ValueError(
            'The arguments "datafiles" and "cpus" must have the same number of entries.'
        )
    
    if len(args.slavenames) > len(set(args.slavenames)):
        raise ValueError('All the names in "slavenames" must be unique.')
    
    for slavename in args.slavenames:
        if len(slavename) > 8:
            raise ValueError("Slavename " + slavename + " contains more than 8 characters.")

    if "MASTER" in args.slavenames:
        raise ValueError(
            "Please do not have a slavename called MASTER (this name is restricted to the automatically created RC MASTER .DATA-file)."
        )

    #################
    ### MAIN PART ###
    #################
    
    # Create output directory if it doesn't already exist:
    
    if not os.path.isdir(args.outputfolder):
        os.makedirs(args.outputfolder)
        print("Created empty RC model directory (" + args.outputfolder + ")")

    # Create directory tree structure:
    
    os.makedirs(args.outputfolder + "/model")
    os.makedirs(args.outputfolder + "/include/runspec")
    
    # Parse the GRUPTREE in the user given master .sch file:
    
    f = open(args.schfile, "r")
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
    
            numdate = converter(date)

    # Parse the data in slave .sch file (if given by user):
    
    slave_keywords = {}
    
    if not args.slavesch is None:
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
    
                date = line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()
    
                if not ":" in date:
                    date += " 00:00:00"
    
                numdate = converter(date)
    
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
    
    for i, standalone in enumerate(args.datafiles):
    
        GRUPSLAV = {args.slavenames[i]: {}}
        KEYWORD_LINES[args.slavenames[i]] = {}
        PARALLEL[args.slavenames[i]] = False
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
            section_dictionary(content),
            args.slavenames[i],
            0,
            {"prev_numdate": 0, "file": None, "linenumber": 0},
        )

        # DO CHANGES TO THE CONTENT
    
        f = open(
            args.outputfolder
            + "/model/"
            + args.casename
            + "_"
            + args.slavenames[i]
            + ".DATA",
            "w",
        )
        f.write("\n".join(content))
        f.close()

        if len(MISSING_WCON) > 0:
            print("WARNING: The following wells in standalone " + args.slavenames[
                i
            ] + " do not have a WCONPROD or WCONINJE: " + ", ".join(
                sorted(list(MISSING_WCON))
            ) + ". You should add a WCONPROD and/or WCONINJE for these wells and run standalones2rc again (standalones2rc only creates the RC required GCONPROD/GCONINJE entries for each WCONPROD/WCONINJE it meets in the standalones).")
    
        print("Copied over all INCLUDE files to be used for slave " + args.slavenames[i])

    # Create the different automatically created include files:

    for i, standalone in enumerate(args.datafiles):

        f = open(
            args.outputfolder
            + "/include/runspec/"
            + args.slavenames[i].lower()
            + ".welldims.inc",
            "w",
        )
        f.write("WELLDIMS\n ")
        for argument in KEYWORD_LINES[args.slavenames[i]]["WELLDIMS"]["arguments"]:
            f.write(str(argument) + " ")
        f.write(" /\n")
        f.close()

    ##################################
    ## CREATE THE MASTER .DATA FILE ##
    ##################################
    
    f = open(args.outputfolder + "/model/" + args.casename + "_MASTER.DATA", "w")
    f.write("".join(master_datafile()))
    f.close()
    
    # Create the GRUPTREE keyword in a schedule file
    
    f = open(args.outputfolder + "/include/schedule/master.gruptree.sch", "w")
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

    f = open(args.outputfolder + "/include/schedule/master.gconprod.sch", "w")
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

    f = open(args.outputfolder + "/include/schedule/master.gconinje.sch", "w")
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
    
    f = open(args.outputfolder + "/include/schedule/master.grupmast.sch", "w")

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
    
    os.system(
        "merge_schedule "
        + args.outputfolder
        + "/include/schedule/master.gruptree.sch "
        + args.outputfolder
        + "/include/schedule/master.grupmast.sch "
        + args.outputfolder
        + "/include/schedule/master.gconprod.sch "
        + args.outputfolder
        + "/include/schedule/master.gconinje.sch "
        + args.schfile
        + " "
        + args.outputfolder
        + "/include/schedule/master.sch > /dev/null"
    )

    #####################################
    # CREATE DUMMY MASTER INCLUDE FILES #
    #####################################
    
    f = open(args.outputfolder + "/include/solution/master.dummy.inc", "w")
    f.write(
        """DATUM
 4300  /

EQUIL
 4300. 493.   3700.    0. 3700.    0.    1    1   20    /

PBVD
 4060.01  468.51
 5174.48  354.91
/

PDVD
 3659.93  400.52
 4060.00  468.51
/
"""
)
    f.close()

    ########

    f = open(args.outputfolder + "/include/grid/master.dummy.inc", "w")
    f.write(
    """NOWARN

-- Dummy reservoir properties

TOPS 
 4400 /
 
DX
 100 /
  
DY
 100 /

DZ
 10 /

PERMX
 100 /

COPY
 PERMX PERMY /
 PERMX PERMZ /
/

PORO
 0.15 /

NTG
 0.90 /

WARN
"""
    )
    f.close()

    ########

    f = open(args.outputfolder + "/include/props/master.dummy.inc", "w")
    f.write(
    """NOWARN

-- Water PVT data
PVTW
-- 8 PVT-regions
--  Pref      Bw          Cw        Visc.    (dV/dP)/V
-- Garn, Ile & Tofte
   466.5     1.0694      5.72E-05   0.2207    1.32E-04 /

--
DENSITY 
 800.0  1035.0  0.920 / Garn, well 6506/12-1 DST 7

--
PVTO

--  RSO   PRESSURE   B-OIL  VISCOSITY
--          (BAR)            (CP)



   50.93   100.00    1.282  0.60584
           150.00    1.257  0.73000
           200.00    1.237  0.85906
           250.00    1.220  0.99232
           300.00    1.206  1.12912
           350.00    1.193  1.26883   /


   87.20   150.00    1.397  0.41954
           200.00    1.367  0.50383
           250.00    1.343  0.59226
           300.00    1.323  0.68443
           350.00    1.305  0.77988
           400.00    1.290  0.87822   /


  115.72   200.00    1.459  0.30634
           250.00    1.425  0.36392
           300.00    1.397  0.42459
           350.00    1.373  0.48811
           400.00    1.353  0.55422
           450.00    1.335  0.62267   /


  144.24   250.00    1.520  0.23568
           300.00    1.481  0.27580
           350.00    1.450  0.31809
           400.00    1.423  0.36241
           450.00    1.400  0.40861
           500.00    1.380  0.45654   /


  172.76   300.00    1.582  0.19195
           350.00    1.540  0.22089
           400.00    1.506  0.25131
           450.00    1.477  0.28312
           500.00    1.451  0.31624
           550.00    1.429  0.35058   /


  184.17   320.00    1.607  0.18025
           370.00    1.565  0.20604
           420.00    1.530  0.23308
           470.00    1.500  0.26132
           520.00    1.474  0.29069
           570.00    1.451  0.32111   /


  195.58   340.00    1.631  0.17193
           390.00    1.589  0.19521
           440.00    1.554  0.21956
           490.00    1.523  0.24494
           540.00    1.497  0.27128
           590.00    1.474  0.29853   /


  206.98   360.00    1.656  0.16730
           410.00    1.614  0.18869
           460.00    1.579  0.21099
           510.00    1.549  0.23416
           560.00    1.523  0.25815
           610.00    1.500  0.28291   /


  218.39   380.00    1.681  0.16671
           430.00    1.641  0.18676
           480.00    1.608  0.20758
           530.00    1.579  0.22914
           580.00    1.554  0.25139
           630.00    1.531  0.27427   /


  229.80   400.00    1.705  0.16985
           450.00    1.668  0.18900
           500.00    1.637  0.20879
           550.00    1.610  0.22919
           600.00    1.586  0.25015   /


  241.21   420.00    1.730  0.17522
           470.00    1.697  0.19370
           520.00    1.668  0.21270
           570.00    1.643  0.23218
           620.00    1.620  0.25211   /


  252.62   440.00    1.755  0.18074
           490.00    1.724  0.19858
           540.00    1.698  0.21684
           590.00    1.675  0.23549
           640.00    1.654  0.25448   /


  257.44   448.46    1.765  0.18272
           498.46    1.736  0.20028
           548.46    1.710  0.21823
           598.46    1.688  0.23652
           648.46    1.668  0.25512   /


  267.39   465.90    1.787  0.18480
           515.90    1.760  0.20173
           565.90    1.735  0.21898
           615.90    1.714  0.23651   /


  275.54   480.19    1.804  0.18429
           530.19    1.776  0.20065
           580.19    1.753  0.21730
           630.19    1.732  0.23420
           680.19    1.713  0.25133
           730.19    1.696  0.26867   /


  282.34   492.11    1.819  0.18256
           542.11    1.792  0.19843
           592.11    1.768  0.21456
           642.11    1.747  0.23094   /


  289.47   502.20    1.835  0.18023
           552.20    1.808  0.19566
           602.20    1.784  0.21136   /


  297.09   510.82    1.852  0.17760
           560.82    1.825  0.19265
           610.82    1.801  0.20796   /


  304.96   518.23    1.872  0.17484
           568.23    1.844  0.18955   /


  304.961  600.00    1.828  0.19904
           650.00    1.805  0.21375   /
/

--
PVTG
-- PRESSURE       RSG        B-GAS     VISCOSITY                                
--  BAR                                 (CP)                                    
                                                                                
                                                                                
                                                                                
    100.00    0.00016644   0.013978     0.01621                                 
              0.00000000   0.013909     0.01605 /                               
                                                                                
                                                                                
    150.00    0.00018950   0.009243     0.01849                                 
              0.00000000   0.009250     0.01769 /                               
                                                                                
                                                                                
    200.00    0.00023797   0.007011     0.02177                                 
              0.00000000   0.007024     0.01975 /                               
                                                                                
                                                                                
    250.00    0.00030785   0.005779     0.02607                                 
              0.00000000   0.005756     0.02207 /                               
                                                                                
                                                                                
    300.00    0.00040104   0.005046     0.03133                                 
              0.00000000   0.004953     0.02449 /                               
                                                                                
                                                                                
    320.00    0.00044562   0.004841     0.03370                                 
              0.00000000   0.004710     0.02545 /                               
                                                                                
                                                                                
    340.00    0.00049391   0.004674     0.03623                                 
              0.00000000   0.004499     0.02641 /                               
                                                                                
                                                                                
    360.00    0.00054459   0.004539     0.03891                                 
              0.00000000   0.004315     0.02736 /                               
                                                                                
                                                                                
    380.00    0.00059499   0.004428     0.04167                                 
              0.00000000   0.004153     0.02830 /                               
                                                                                
                                                                                
    400.00    0.00064154   0.004335     0.04444                                 
              0.00000000   0.004009     0.02922 /                               
                                                                                
                                                                                
    420.00    0.00068203   0.004255     0.04714                                 
              0.00000000   0.003880     0.03012 /                               
                                                                                
                                                                                
    440.00    0.00071702   0.004185     0.04979                                 
              0.00000000   0.003764     0.03101 /                               
                                                                                
                                                                                
    448.46    0.00073073   0.004158     0.05090                                 
              0.00000000   0.003719     0.03138 /                               
                                                                                
                                                                                
    465.90    0.00076126   0.004110     0.05332                                 
              0.00000000   0.003631     0.03213 /                               
                                                                                
                                                                                
    480.19    0.00079116   0.004078     0.05553                                 
              0.00000000   0.003564     0.03274 /                               
                                                                                
                                                                                
    492.11    0.00082044   0.004058     0.05757                                 
              0.00000000   0.003511     0.03324 /                               
                                                                                
                                                                                
    502.20    0.00084913   0.004047     0.05949                                 
              0.00000000   0.003469     0.03367 /                               
                                                                                
                                                                                
    510.82    0.00087725   0.004041     0.06131                                 
              0.00000000   0.003435     0.03402 /                               
                                                                                
                                                                                
    518.23    0.00090480   0.004040     0.06304                                 
              0.00000000   0.003406     0.03433 /                               
                                                                                
                                                                                
    520.00    0.00090480   0.004035     0.06322                                 
              0.00000000   0.003399     0.03440 /                               
                                                                                
                                                                                
    540.00    0.00090480   0.003979     0.06523                                 
              0.00000000   0.003326     0.03522 /                               
                                                                                
                                                                                
    560.00    0.00090480   0.003928     0.06727                                 
              0.00000000   0.003259     0.03603 /                               
                                                                                
                                                                                
    580.00    0.00090480   0.003879     0.06934                                 
              0.00000000   0.003197     0.03683 /                               
                                                                                
                                                                                
    600.00    0.00090480   0.003834     0.07144                                 
              0.00000000   0.003140     0.03762 /                               
/       


--     P(DATUM)              CR
ROCK
         475.0            4.E-05 /
--
SWOF
-- Chlorite&Flood   Garn
--Sw     Krw      Krow     J o/w imb
0.122697        0        1 16.54618
       1        1        0 -3.70455
/

SGOF
--Chlorite&Flood    Garn
--Sg     Krg      Krog     Pc satt t
       0        0        1        0
0.033865     0.03 0.857375        0
0.877303        1        0        0
/

EQUALS
 SOWCR 0.186 4*  1  1  /   --
 SWL 0.28  4*  1  1  /
 SWU 0.856 4*  1  1  /
 SGU 0.72  4*  1  1  /
 SGCR 0.144 4*  1  1  /
 SOGCR 0.1224 4*  1  1  /
/

COPY
 SWL SWCR /
/

WARN
"""
    )
    f.close()
