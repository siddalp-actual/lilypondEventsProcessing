"""
    This module contains classes to be used to read a LilyPond .notes file
    created using an events listener.  The events are parsed into a set of
    Notes which are held in Voices (think instrument or choral part).  The
    voices are held in a Score, which does the main parsing work.
"""
from dataclasses import dataclass
import logging
import re


class Note:
    """
    represents a music note
    """

    STRESS_INCREMENT = 15

    def __init__(self, midi_pitch, at=0, seconds=0.25, bar=0):
        self.pitch = int(midi_pitch)
        self.duration = seconds
        self.start_time = at
        self.volume = float(71 / 127)
        self.bar = bar
        self.slurred = False

    def __repr__(self):
        return f"{self.pitch} {self.duration} {int(self.volume * 127)}"

    def set_volume(self, new_volume):
        """
        use the dictionary trick to map a dynamic pp thru ff to a
        midi velocity
        same values as scm/midi.scm in lilypond
        """
        self.volume = {
            "sf": 1.00,
            "fffff": 0.95,
            "ffff": 0.92,
            "fff": 0.85,
            "ff": 0.80,
            "f": 0.75,
            "mf": 0.68,
            "mp": 0.61,
            "p": 0.55,
            "pp": 0.49,
            "ppp": 0.42,
            "pppp": 0.34,
            "ppppp": 0.25,
        }[new_volume]

    def extend(self, seconds=0.25):
        """
        when a tie is spotted and we need to extend the previous note
        by the length of the new note
        """
        self.duration += seconds

    def accent(self, stress_type):
        """
        stress this note (add velocity), typically for first beat in bar
        """
        if stress_type == 0:
            self.volume += Note.STRESS_INCREMENT / 127
        else:
            self.volume += Note.STRESS_INCREMENT / 127 * 2 / 3  # less
        self.volume = min(127, self.volume)

    def set_in_slur(self):
        """
        this note is in slur and should not be staccato'd
        """
        self.slurred = True

    def set_not_slurred(self):
        """
        this note is at the end of a slur so may be stacatto'd
        """
        self.slurred = False

    def staccato(self, factor=0):
        """
        shorten this note by a factor
        """
        if factor == 0:
            factor = 0.1  # really short (for staccato dot)
        if not self.slurred:
            self.duration *= factor


class Voice:
    """
    holds information about a voice
    """

    voice_num = 0

    def __init__(self):
        self.voice_num = Voice.voice_num
        Voice.voice_num += 1
        self.volume = 0.5
        self.note_list = []
        self.last_note = None
        self.busy_until = 0
        self.last_note_tied = False
        self.tie_start_bar = 0
        self.slurred = False

    def __repr__(self):
        return f"Voice#{self.voice_num:0d}<{self.last_note.pitch:0d}>"

    def append(self, note_start_time, note):
        """
        appending a note to a voice might extend the last note, if we've had
        a tie

        returns True if a voice was untied
        """
        untied_note = False
        if self.last_note_tied:
            logging.debug(f"tieing {note.pitch}")
            logging.debug(f"append: {self.busy_until} : {note_start_time}")
            assert self.last_note.pitch == note.pitch
            assert abs(self.busy_until - note_start_time) < 1e-6
            self.last_note.extend(seconds=note.duration)
            self.busy_until += note.duration
            self.last_note_tied = False
            untied_note = True
        else:
            self.note_list.append(note)
            self.last_note = note
            self.busy_until = note_start_time + note.duration

        if self.slurred:
            self.last_note.set_in_slur()

        return untied_note

    def is_busy(self, time):
        """
        works out whether a voice would be busy at a particular time
        """
        if time >= self.busy_until - 1e-6:  # allow a microsecond rounding
            return False
        return True

    def prep_tie(self):
        """
        flag this voice as having a pending tie
        """
        self.last_note_tied = True
        self.tie_start_bar = self.last_note.bar

    def prep_slur(self):
        """
        tell a voice that a slur is in progress
        """
        self.slurred = True

    def end_slur(self):
        """
        tell a voice that a slur has ended
        """
        self.last_note.set_not_slurred()
        self.slurred = False


class TieException(Exception):
    """
    Tie must tie notes of same pitch and cannot last more than a bar
    """


class Staff:
    """
    Holding pattern for notes read from a single .notes file
    """

    WHITESPACE = re.compile(r"\s+")
    TIME_LAPSE = 1.0

    def __init__(self, filename):
        self.note_list = []
        self.voices = []
        self.last_voice = None
        self.tied_voices_set = set([])
        self.tempo = Staff.TIME_LAPSE
        self.beat_structure = [0]
        self.staccato_er = 0.875  # fraction of note length to play
        with open(filename, "r") as f:
            for line in f:
                self.process(line)

    def process(self, l):
        """
        handle a line from the notes file
        split it into a bunch of fields representing the event
        """
        fields = Staff.WHITESPACE.split(l)
        self.process_event(fields)

    def process_event(self, e):
        """
        decide which type of event we're dealing with and hand-off
        to the relevant sub-process via a
        dictionary pretending to be a switch statemetn
        """
        event_time = float(e[0]) * self.tempo
        event_type = e[1]
        {
            "note": self.process_note,
            "tempo": self.process_tempo,
            "tie": self.process_tie,
            "slur": self.process_slur,
            "time-sig": self.process_timesig,
        }.get(event_type, self.event_not_recognised)(event_time, e)

    def event_not_recognised(self, time, e):
        """
        flag up an error
        """
        logging.warning(f"event not recognised: {e[1]} at {time}={e[0]}s")

    def create_new_voice(self):
        """
        add a new voice to this staff
        """
        new_voice = Voice()
        self.voices.append(new_voice)
        if len(self.voices) >= 6:
            raise ValueError
        return new_voice

    def find_free_voice(self, start_time, note_info):
        """
        try to find an existing voice that this note should belong to
        initially, we test for voices with pending ties
        """
        # does this note match a tied voice?
        logging.debug(f"find_free_voice at {start_time}")
        if self.tied_voices_set:
            logging.debug(f"find_free: tied {self.tied_voices_set}")
            logging.debug("find_free: all {self.voices}")
            for v in self.tied_voices_set:
                if v.tie_start_bar + 2 <= note_info.bar:
                    logging.debug(
                        f"find_free: *TIE* at bar {note_info.bar} {v} tie "
                        "started in {v.tie_start_bar}"
                    )
                    raise TieException  # can't tie through a whole bar
                if note_info.pitch == v.last_note.pitch:
                    logging.debug(f"returning tied voice {v}")
                    return v

        for v in self.voices:
            if v.is_busy(start_time):
                logging.debug(f"voice {v.voice_num} busy until {v.busy_until}")
                continue

            if v.last_note_tied:
                if note_info.pitch != v.last_note.pitch:
                    continue
            break  # I want to come out with the FIRST voice available

        try:
            v
            logging.debug(
                f"find_free: loop returned {v.voice_num} {v.busy_until} "
                "{v.last_note.pitch if v.last_note_tied else 0}"
            )
        except NameError:
            return self.create_new_voice()
        logging.debug(f"find free: thinking about {v.voice_num}")
        if (
            v.is_busy(start_time)
            or v.last_note_tied
            and v.last_note.pitch != note_info.pitch
        ):
            return self.create_new_voice()

        return v

    def process_timesig(self, unused_note_start, e):
        """
        a time signature has two arguments, number of notes per bar and
        note type.  We only care about the number per bar
        """
        beats_per_bar = int(e[2])
        self.beat_structure = {
            2: [0],
            3: [0],
            4: [0],
            6: [0, 0.5],
            8: [0, 0.5],
        }[beats_per_bar]

    def process_slur(self, unused_note_start, e):
        """
        a slur applies to the previously seen note
        slur start has -1
        slur end indicated by +1
        """
        if int(e[2]) == -1:
            self.last_voice.prep_slur()
        elif int(e[2]) == 1:
            self.last_voice.end_slur()
        else:
            logging.error(f"slur: unexpected arg {e[2]}")

    def process_tie(self, unused_note_start, unused_e):
        """
        there is no further information in a tie event
        it applies to the immediately prior note, which is going to be extended
        by an amound given by the next note of the same pitch
        """
        self.last_voice.prep_tie()
        logging.debug(
            f"tie for {self.last_voice} {self.last_voice.last_note.pitch}"
        )
        self.tied_voices_set.add(self.last_voice)

    def process_tempo(self, unused_note_start, e):
        """
        events are always received at a rate of 60 quarter notes per min
        eighth = 80 gives a tempo number of 640 = 40 per min = 3/2 * time
        """
        new_tempo = float(e[2])
        self.tempo = new_tempo / 425

    def process_note(self, note_start, e):
        """
        we've got a note event
        find a voice for it, and append to it
        """
        (
            unused_time,
            unused_type,
            midi_note,
            unused_note_length,
            note_duration,
            bar_num,
            bar_pos,
            *unused_origin,
        ) = e
        logging.info(f"found note: {midi_note}")
        note = Note(
            midi_note,
            at=note_start,
            seconds=float(note_duration) * self.tempo,
            bar=int(bar_num),
        )

        # only Score knows about bar position, but the way to stress a beat
        # should be an attribute of the voice and we certainly shouldn't be
        # stressing the second part of a tie
        for stress_pos in self.beat_structure:
            if abs(float(bar_pos) - stress_pos) < 1e-6:
                note.accent(stress_pos)  # stress first beat of bar

        self.note_list.append(note)  # all the notes in the score
        use_voice = self.find_free_voice(note_start, note)
        if use_voice.last_note_tied:
            logging.info(
                f"using tied voice: {use_voice} {use_voice.last_note.pitch}"
            )
        untied = use_voice.append(note_start, note)
        if untied:
            self.tied_voices_set.remove(use_voice)
        self.last_voice = use_voice  # remember voice for tie

    def show_notes(self):
        """
        iterate through the notes in the note_list
        """
        for n in self.note_list:
            print(repr(n))

    def articulate(self, effects):
        """
        articulate the music according to the requested effects if any
        """
        for v in self.voices:
            for n in v.note_list:
                for e in effects:
                    e(n)  # apply the effect to the note

    def more_staccato(self, note):
        """
        a helper function for use with articulate, makes playing less legato
        """
        note.staccato(factor=self.staccato_er)


@dataclass
class TimedElmt:
    """
    carve out the shape of an element in the TimedList
    """

    event_time: float  # seconds from start
    event: object


class TimedList:
    """
    a data structure and methods to let us insert events at a particular
    time, and retrieve them chronologically
    """

    RECURSION_LIMIT = 14

    def __init__(self):
        """
        Create a new, empty, list
        """
        self.event_list = []
        self.bin_chop_depth = 0

    def bin_chop_loc(self, time, e_l):
        """
        recursively find the insertion point for given time
        """
        self.bin_chop_depth += 1
        assert self.bin_chop_depth <= TimedList.RECURSION_LIMIT
        # print(bin_chop_depth, len(e_l), e_l)
        # print(f"  searching: {time}")
        if len(e_l) == 0:
            return 0
        pos = max(0, int(len(e_l) / 2) - 1)
        if time < e_l[pos].event_time:  # insert in left hand sub list
            # print("lh search")
            return self.bin_chop_loc(time, e_l[:pos])
        # print("rh search")
        return pos + 1 + self.bin_chop_loc(time, e_l[pos + 1 :])

    def insert(self, mido_note, event_time):
        """
        build data structure to hold timed event and insert
        """
        # el = {'at': event_time,
        #      'event': mido_note}
        el = TimedElmt(event_time=event_time, event=mido_note)
        self.bin_chop_depth = 0
        insert_point = self.bin_chop_loc(event_time, self.event_list)
        self.event_list.insert(insert_point, el)

    def __iter__(self):
        """
        iterate over events
        """
        for event in self.event_list:
            yield event
