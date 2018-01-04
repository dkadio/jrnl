#!/usr/bin/env python3
# coding: utf-8
"""Source code for jrnl."""

import datetime
import os
import subprocess
import sys
import dateutil.parser
from jrnl import helpers
from jrnl import runoptions


def main():
    """Main program for jrnl."""
    # Parse runtime options
    runtimeArgs = runoptions.parseRuntimeArguments()

    # Open up config file
    configDict = runoptions.getConfig()

    if not configDict:
        print("No config file found!", file=sys.stderr)
        sys.exit(1)

    # Figure out what editor to use
    if helpers.isProgramAvailable(configDict["editor"]):
        editorName = configDict["editor"]
    elif helpers.isProgramAvailable("sensible-editor"):
        editorName = "sensible-editor"
    else:
        print(configDict["editor"] + " not available!", file=sys.stderr)
        sys.exit(1)

    # Make sure journal root directory exists
    if not os.path.isdir(configDict["journal_path"]):
        if helpers.prompt("Create '" + configDict["journal_path"] + "'?"):
            os.makedirs(configDict["journal_path"])
        else:
            sys.exit(0)

    # Build datetime objects for the relevant dates
    if runtimeArgs.dates:
        # Parse dates given in runtime argument
        dates = []

        for datestring in runtimeArgs.dates:
            # Check for negative offsetting first
            try:
                offset = int(datestring)

                # Limits for the offset so we don't misinterpret a date
                # as an offset
                if offset > 1e6:
                    raise ValueError

                # Create datetime object using offset from current day
                dates.append(datetime.datetime.today()
                                + datetime.timedelta(days=offset))
            except ValueError:
                dates.append(dateutil.parser.parse(datestring, fuzzy=True))

    else:
        # Use today's date (or previous day if hour early enough)
        today = datetime.datetime.today()

        if today.hour < configDict["hours_past_midnight_included_in_day"]:
            today = today - datetime.timedelta(days=1)

        dates = [today]

    # Determine whether to write timestamp based on runtime args and
    # whether to only open existing files
    writetimestamp = (runtimeArgs.timestamp
                        or (configDict["write_timestamp"]
                                and not runtimeArgs.no_timestamp))
    readmode = bool(runtimeArgs.dates)

    # Open journal entries corresponding to the current date
    for date in dates:
        openEntry(date, editorName, configDict["journal_path"],
                  writetimestamp, readmode)

    # Exit
    sys.exit(0)


def writeTimestamp(entrypath, todayDatetime=datetime.datetime.today()):
    """Write timestamp to journal entry, if one doesn't already exist.

    Modifies a text file to include today's time and possibly date in
    ISO 8601. How this works depends on the file being created/modified:

    (1) If the journal entry text file doesn't already exist, create it
        and write the date and time to the top of the file.
    (2) If the journal entry already exists, look inside and see if
        today's date is already written.  If today's date is not
        written, append the date and time to the file, ensuring at least
        one empty line between the date and time and whatever text came
        before it.  If today's date *is* written, follow the same steps
        as but omit writing the date; i.e., write only the time.

    Args:
        entrypath: A string containing a path to a journal entry,
            already created or not.
        todayDatetime: An optional datetime.datetime object representing
            today's date.
    """
    # Get strings for today's date and time
    todayDate = todayDatetime.strftime('%Y-%m-%d')
    todayTime = todayDatetime.strftime("%H:%M")

    # Check if journal entry already exists. If so write, the date and
    # time to it.
    if not os.path.isfile(entrypath):
        with open(entrypath, 'x') as jrnlentry:
            jrnlentry.write(todayDate + "\n" + todayTime + "\n")
    else:
        # Find if date already written
        entrytext = open(entrypath).read()

        if todayDate in entrytext:
            printDate = False
        else:
            printDate = True

        # Find if we need to insert a newline at the bottom of the file
        if entrytext.endswith("\n\n"):
            printNewLine = False
        else:
            printNewLine = True

        # Write to the file
        with open(entrypath, 'a') as jrnlentry:
            jrnlentry.write(printNewLine * "\n"
                            + (todayDate + "\n") * printDate
                            + todayTime + "\n\n")


def openEntry(datetimeobj, editor, journalPath, dotimestamp, inreadmode,
              errorstream=sys.stderr):
    """Try opening a journal entry.

    Args:
        datetimeobj: A datetime.datetime object containing which day's
            journal entry to open.
        editor: A string containing the name of the editor to use.
        journalPath: A string containing the path to the journal's base
            directory.
        dotimestamp: A boolean signalling whether to append a timestamp
            to a journal entry before opening.
        inreadmode: A boolean signalling whether to only open existing
            entries ("read mode").
        errorstream: An optional TextIO object to send error messages
            to. Almost certainly you want to use the default standard
            error output.
    """

    # Determine path the journal entry text file
    yearDirPath = os.path.join(journalPath, str(datetimeobj.year))
    entryPath = os.path.join(yearDirPath, datetimeobj.strftime('%Y-%m-%d') + '.txt')

    # If in read mode, only open existing entries
    if inreadmode and not os.path.exists(entryPath):
        print("%s does not exist!" % entryPath, file=errorstream)
        return

    # Make the year directory if necessary
    if not os.path.isdir(yearDirPath):
        os.makedirs(yearDirPath)

    # Append timestamp to journal entry if necessary
    if dotimestamp:
        writeTimestamp(entryPath)

    # Open the date's journal
    subprocess.Popen([editor, entryPath]).wait()
