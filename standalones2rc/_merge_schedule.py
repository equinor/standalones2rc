import os
from matplotlib.dates import strpdate2num, num2date


def read_schedule_file(filename):
    converter = strpdate2num("%d %b %Y %H:%M:%S")

    f = open(filename, "r")
    content = f.readlines() + [
        "\n\n"
    ]  # Added extra line break to cope with text files saved on Windows
    f.close()

    dates = [0]
    keywords = [""]

    in_dates_keyword = False

    for line in content:
        line = line.partition("--+")[0]  # Remove special merge_schedule keywords.

        if line.partition("--")[0].strip() == "DATES":
            in_dates_keyword = True
        elif in_dates_keyword and "/" in line and line.strip()[0] == "/":
            in_dates_keyword = False
        elif in_dates_keyword and line.partition("--")[0].strip() != "":
            date = line.replace("'", "").replace("/", "").replace("JLY", "JUL").strip()

            if not ":" in date:
                date += " 00:00:00"

            dates.append(converter(date))
            keywords.append("")
        else:
            keywords[-1] += line

    return dates, keywords


def merge_schedule(inputfiles, outputfile):

    ###################
    # Parse arguments #
    ###################

    dates = []
    keywords = []

    # Read inputfiles:

    for filename in inputfiles:

        [dates_, keywords_] = read_schedule_file(filename)

        dates += dates_
        keywords += keywords_

    # Sort the schedule keywords based on the DATES keyword (if several instances have the same DATES, then the ordering follows the file input order):

    sorted_list = [
        list(x) for x in zip(*sorted(zip(dates, keywords), key=lambda pair: pair[0]))
    ]

    ########################
    # Write to output file #
    ########################

    f = open(outputfile, "w")
    previous_date = 0

    for i in range(len(sorted_list[0])):
        if (
            sorted_list[0][i] != previous_date
        ):  # do not print DATE keyword if it's the same as the previous one
            datestring = (
                num2date(sorted_list[0][i]).strftime("%d '%b' %Y %H:%M:%S").upper()
            )

            if "00:00:00" in datestring:
                datestring = datestring[: datestring.find(" 00:00:00")]

            f.write("DATES\n  " + datestring + " /\n/\n\n")

        f.write(sorted_list[1][i])

        previous_date = sorted_list[0][i]

    f.close()
