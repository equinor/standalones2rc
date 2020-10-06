# This is an old, ugly script - to be cleaned.

import os
from datetime import datetime

from matplotlib.dates import date2num, num2date


def copy_include_files(
    filename,
    schfile,
    section,
    slavename,
    current_numdate,
    prev_numdate,
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
):

    # Copies the INCLUDE files in filename (is called recursively in order to accound for deeply nested INCLUDE files)

    try:
        # TODO: Do not hardcode this replacement.
        filename = filename.replace("$ECLPATH", "../include")

        f = open(filename, "r", encoding="utf-8", errors="ignore")
        content = f.readlines()
        f.close()
    except:
        raise RuntimeError("Could not read INCLUDE file " + filename)

    content = [x.strip() for x in content]

    IN_PARALLEL = False
    IN_INCLUDE = False
    IN_ACTION: int = (
        0  # Actions may be nested, therefore using a counter to track exit.
    )
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
            if cpus[slavenames.index(slavename)] > 1:
                content[j] = (
                    "PARALLEL\n "
                    + str(cpus[slavenames.index(slavename)])
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
                old_path,
                schfile,
                current_section,
                slavename,
                current_numdate,
                prev_numdate,
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

        ############## Process ACTIONS keywords ##############
        # Not allowing actions in slaves.
        elif (
            line in ["ACTION", "ACTIONR", "ACTIONW", "ACTIONS", "ACTIONX", "DELAYACT"]
            and "keep in reservoir coupled model" not in comment
            and "keep in rc model" not in comment
        ):
            IN_ACTION += 1  # Actions may be nested, therefore using a counter to track if we are in an action.
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif IN_ACTION > 0:
            if line == "ENDACTIO":
                IN_ACTION -= 1
            content[j] = "-- commented out by standalones2rc: " + content[j]
        elif line == "ENDACTION":  # ENDACTION without being in an action
            raise ValueError(
                "Encountered ENDACTIO without a preceding action keyword:"
                "ACTION, ACTIONR, ACTIONW, ACTIONS, ACTIONX, DELAYACT."
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
                print(
                    "WARNING: Group "
                    + groupname
                    + " is used in standalone corresponding to slave "
                    + slavename
                    + ", however this group is not mentioned in the GRUPTREE in "
                    + schfile
                    + ". If not corrected, this will give an ERROR in Eclipse."
                )

                MASTER_GRUPTREE[groupname] = {"numdate": -1, "warning_given": True}

            elif MASTER_GRUPTREE[groupname]["numdate"] > current_numdate:
                print(
                    "WARNING: Group "
                    + groupname
                    + " is used in standalone corresponding to slave "
                    + slavename
                    + " before it is defined in the GRUPTREE in "
                    + schfile
                    + ". If not corrected, this will give an ERROR in Eclipse."
                )

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

        elif line == "RPTRST" and not rptrst:
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

            START_NUMDATE[slavename] = date2num(
                datetime.strptime(start_date, "%d %b %Y %H:%M:%S")
            )

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

            current_numdate = date2num(datetime.strptime(date, "%d %b %Y %H:%M:%S"))

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

            if not wconprod and not "GRUP" in data[2]:
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

            if cpus[slavenames.index(slavename)] == 1:
                content[j] = "-- commented out by standalones2rc: " + content[j]

            PARALLEL[slavenames.index(slavename)] = True

        elif IN_PARALLEL and "/" in line:
            data = line.split()

            if cpus[slavenames.index(slavename)] == 1:
                content[j] = "-- commented out by standalones2rc: " + content[j]
            else:
                data[0] = str(cpus[slavenames.index(slavename)])
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
        current_section = section
        old_filename = os.path.basename(filename)

        if not old_filename.startswith(slavename.lower() + "."):
            new_filename = slavename.lower() + "." + old_filename
        else:
            new_filename = old_filename

        if not os.path.isdir(outputfolder + "/include/" + current_section.lower()):
            os.makedirs(outputfolder + "/include/" + current_section.lower())

        new_path = "../include/" + current_section.lower() + "/" + new_filename

        f = open(outputfolder + "/include/" + new_path, "w")
        f.write("\n".join(content))
        f.close()

    return (content, current_numdate, prev_numdate)
