"""
hold the top level structures
"""
import logging
import re

import mido

import lilyNotes

logger = logging.getLogger(__name__)


class Score:
    """
    score is the top level class in lilyNotes. It contains methods for finding
    the .notes files related to a piece of music

    Hopefully the staff related .notes files for a single score have the same
    time-signature, tempo etc and so these attributes are held at this level.

    Finally, when producing a midi file, track0 contains some of this meta
    information
    """

    NOTES_FILE = re.compile(r"\/([^/.]+\.notes)")
    NOTES_STAFF = re.compile(r"([^.-]+)-(.+).notes")

    @classmethod
    def find_files(cls, directory):
        """
        placeholder
        not sure whether I want all the file search and disambiguation
        stuff in here
        """

    def __init__(self, file_map):
        """
        build the top level object
        """
        self.lily_staff = {}
        self.file_map = file_map  # stem: {staff: filepath/stemp-staff.notes}
        stem = next(iter(file_map))  # the first key, stem of .ly file
        self.meta = {
            "text": {"text": "built by lilyNotes from lilypond source"},
            "track_name": {"name": next(iter(file_map))},
            "set_tempo": {"tempo": 500000},
        }
        self.title = next(iter(file_map))  # return first key
        self.performance = []
        for staff in self.file_map[stem]:
            self.lily_staff[staff] = lilyNotes.staff.Staff(
                self.file_map[stem][staff], parent=self  # the .notes file
            )

    def perform(self):
        """
        actually perform the music
        """
        self.performance = []
        for each_voice in self.get_all_voices():
            perf = lilyNotes.performer.Performer(each_voice)
            self.performance.append(perf.standard_articulation())

    def to_midi(self):
        """
        create a midi file
        """
        track_zero = self.build_track_zero()
        midi_file = mido.MidiFile(type=1)
        midi_file.ticks_per_beat = lilyNotes.staff.Staff.CLICKS_PER_BEAT
        midi_file.tracks.append(track_zero)

        for i, each_voice in enumerate(self.get_all_voices()):
            m_p = lilyNotes.performer.MidiPerformer(each_voice)
            functions = (
                lilyNotes.performer.MidiPerformer.MIDI_ARTICULATION_FUNCTIONS
            )
            # functions.insert(0, lilyNotes.performer.Performer.show_event)
            track = m_p.to_midi_track(functions)
            midi_file.tracks.append(track)
            logger.debug("to_midi > added %d tracks", i)

        return midi_file

    def build_track_zero(self):
        """
        return a mido track containing the meta information
        """
        return_var = mido.MidiTrack()
        for key in self.meta:
            meta_msg = mido.MetaMessage(key, **self.meta[key])
            logger.debug("build_track_zero: %s", **self.meta[key])
            return_var.append(meta_msg)
        return return_var

    def set_tempo(self, new_tempo):
        """
        hold the tempo in the track's meta information
        """
        tempo = int(new_tempo)
        logger.debug("set_tempo, new value: %s", tempo)
        self.meta["set_tempo"]["tempo"] = tempo

    def get_all_voices(self):
        """
        construct a list containing all the voices in all the staves
        """
        all_voices = [
            v
            for staff in self.lily_staff
            for v in self.lily_staff[staff].voices
        ]
        return all_voices

    def get_stem(self):
        """
        return the start of the original .ly file
        """
        return self.meta["track_name"]["name"]

    @staticmethod
    def build_file_map(file_list):
        """
        decompose the files into a set of stems, staves and their associated
        files
        """
        file_map = {}
        for file_name in file_list:
            stem, staff = Score.parse_file_name(file_name)
            file_map.setdefault(stem, {})[staff] = file_name
            logger.info("build_map: %s", file_map)
        return file_map

    @staticmethod
    def parse_file_name(name):
        """
        break the file name down into its stem and staff components.
        event-listener builds file names of the form:
        stem-staff.notes where stem.ly was the input file
                               staff maybe unnamed-staff
        """
        matchoptions = Score.NOTES_FILE.search(name)
        if matchoptions:
            logger.info("parse_file > found %s", matchoptions[1])
            notes_file = matchoptions[1]
            staff_match = Score.NOTES_STAFF.match(notes_file)
            if not staff_match:
                # What's gone wrong, a .notes file must have a file part and a
                # staff part
                logger.error("** parse_file > %s", notes_file)
                raise ValueError
            logger.info(
                "parse_file > stem: %s staff: %s",
                staff_match[1],
                staff_match[2],
            )
            return staff_match[1], staff_match[2]

        logger.error("** parse_file > name :%s: doesn't match pattern", name)
        raise ValueError
