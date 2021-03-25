#! /usr/bin/env python
"""
This is the front end for lilypond .notes file to .midi conversion

The named (or current) directory is searched for a .notes file and
this is then transformed to midi events which are written out to a
.midi file
"""
import argparse
import glob
import logging
import os
import re

NOTES_FILE = re.compile(r"\/([^/.]+\.notes)")
NOTES_STAFF = re.compile(r"([^.-]+)-(.+).notes")


def read_args():
    """
    read arguments passed to the program
    """
    arg_parser = argparse.ArgumentParser(
        description=(
            ""
            "Produce midi output from a lilypond score by processing events"
            "produced when petes-event-listener.ly is included in processing"
        )
    )
    arg_parser.add_argument(
        "--force", help="do the full function", action="store_true"
    )
    arg_parser.add_argument(
        "-v",
        "--verbose",
        help="log more information",
        action="count",
        dest="verbosity",
        default=0,
    )
    arg_parser.add_argument(
        "dir",
        nargs="?",
        default=os.getcwd(),
        help="the name of the directory to search for .notes files",
    )
    args = arg_parser.parse_args()
    return args


def start_logging(log_level):
    """
    map the verbosity level into logging messages to show
    -v : info
    -vv: error
    -vvv: debug
    """
    name = {
        1: logging.WARNING,
        2: logging.INFO,
        3: logging.ERROR,
        4: logging.DEBUG,
    }[log_level]
    logging.basicConfig(  # filename='example.log',
        encoding="utf-8",
        force=True,
        level=name,
        #                    level=logging.WARNING
        #                    level=logging.INFO
        #                    level=logging.DEBUG
    )


def parse_file_name(name):
    """
    break the file name down into its stem and staff components.
    event-listener builds file names of the form:
    stem-staff.notes where stem.ly was the input file
                           staff maybe unnamed-staff
    """
    matchoptions = NOTES_FILE.search(name)
    if matchoptions:
        logging.info("parse_file > found %s", matchoptions[1])
        notes_file = matchoptions[1]
        staff_match = NOTES_STAFF.match(notes_file)
        if not staff_match:
            # What's gone wrong, a .notes file must have a file part and a
            # staff part
            logging.error("** parse_file > %s", notes_file)
            raise ValueError
        logging.info(
            "parse_file > stem: %s staff: %s", staff_match[1], staff_match[2]
        )
        return staff_match[1], staff_match[2]

    logging.error("** parse_file > name :%s: doesn't match pattern", name)
    raise ValueError


def build_file_map(file_list):
    """
    decompose the files into a set of stems, staves and their associated files
    """
    file_map = {}
    for file_name in file_list:
        stem, staff = parse_file_name(file_name)
        temp = file_map.get(stem, {})
        temp.update({staff: file_name})
        file_map[stem] = temp  # file_map.get(stem, {}).update({staff: f})
        logging.info("build_map: %s", file_map)
    return file_map


def disambiguate_which_notes(mapping):
    """
    show the files to the person and discuss which one to work on
    """
    if len(mapping) > 1:
        logging.error("too many notes files, qualify which one")
        for i, name in enumerate(mapping):
            print(f">> {i} for: {mapping[name]}\n")
        key_val = -1
        while not 0 <= key_val <= len(mapping) - 1:
            key_val = int(input("enter number..."))
        dict_key = list(mapping.keys())[key_val]
        print(f"continuing with > {key_val} : {dict_key}")
        return dict_key

    return list(mapping.keys())[0]


program_args = read_args()
start_logging(program_args.verbosity + 1)
# print(program_args.force)
logging.info("dir to search: %s", program_args.dir)

pattern = program_args.dir + "/*.notes"
files = glob.glob(pattern)
logging.info("found files: %s", files)
notes_map = build_file_map(files)
index = disambiguate_which_notes(notes_map)
logging.info("working with %s", index)