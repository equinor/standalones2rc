# This is an old, ugly script - to be cleaned.


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
