"""
    This module contains classes to be used to read a LilyPond .notes file
    created using an events listener.  The events are parsed into a set of
    Notes which are held in Voices (think instrument or choral part).  The
    voices are held in a Score, which does the main parsing work.
"""
import logging
import re
from lilyNotes import note as lily_note, voice, performer, score_pos


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
    CLICKS_PER_BEAT = 384  # 2**8 * 3

    def __init__(self, filename):
        self.note_list = []
        self.voices = []
        self.last_voice = None
        self.tied_voices_set = set([])
        self.tempo = Staff.TIME_LAPSE
        self.beat_structure = [0]
        self.beats_per_bar = 0
        with open(filename, "r") as f:
            for line in f:
                self.process(line)

        self.performance = []
        for each_voice in self.voices:
            perf = performer.Performer(each_voice)
            self.performance.append(perf.standard_articulation())

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
        event_time = float(e[0])
        event_type = e[1]
        logging.info(f"Input event: %0.03f : %s", event_time, e[1:])
        {
            "note": self.process_note,
            "tempo": self.process_tempo,
            "tie": self.process_tie,
            "slur": self.process_slur,
            "time-sig": self.process_timesig,
            "dynamic": self.process_dynamic,
            "cresc": self.process_hairpin_start,
            "decresc": self.process_hairpin_start,
        }.get(event_type, self.event_not_recognised)(event_time, e)

    @staticmethod
    def event_not_recognised(time, e):
        """
        flag up an error
        """
        logging.warning(f"event not recognised: {e[1]} at {time}={e[0]}s")

    def broadcast_to_current_voices(self, event_time, event_info):
        click_time = event_time * 4 * Staff.CLICKS_PER_BEAT
        for each_voice in self.voices:
            each_voice.append(click_time, event_info, event_type="Dynamic")

    def create_new_voice(self):
        """
        add a new voice to this staff
        """
        new_voice = voice.Voice(self)
        self.voices.append(new_voice)
        if len(self.voices) >= 7:
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
                if v.tie_start_bar + 2 <= note_info.score_position.bar_number():
                    logging.debug(
                        "find_free: *TIE* at bar %d %s tie started in %d",
                        note_info.score_position.bar_number(),
                        v,
                        v.tie_start_bar,
                    )
                    raise TieException  # can't tie through a whole bar
                if note_info.pitch == v.last_note.pitch:
                    logging.debug("returning tied voice %s", v)
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

    def process_hairpin_start(self, start_time, e):
        """
        start of cresc, decresc etc where we don't know the
        rate of increase and need to wait for it's end to
        work it out.
        """
        e[1] = "start_hairpin"
        self.broadcast_to_current_voices(start_time, e)

    def process_dynamic(self, start_time, e):
        """
        a dynamic event contains the new volume
        """
        new_volume = str(e[2])  # pppp-p,mp,mf,f-ffff
        self.broadcast_to_current_voices(start_time, e)
        for v in self.voices:
            v.set_volume(new_volume)

    def process_timesig(self, start_time, e):
        """
        a time signature has two arguments, number of notes per bar and
        note type.  We only care about the number per bar
        """
        self.broadcast_to_current_voices(start_time, e)
        self.beats_per_bar = int(e[2])
        self.beat_structure = {
            2: [0],
            3: [0],
            4: [0],
            6: [0, 0.5],
            8: [0, 0.5],
        }[self.beats_per_bar]

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
        in one sample with a \tempo of 80
        a quarter note (crotchet) bpm of 80 sends me an event with 320 and I
        see quarter note durations of 0.25s or 240 per minute so I need to
        multiply the event time by 3

        in another sample with no tempo, again, quarter notes arrive at 0.25s
        quantization, but I see no tempo event. This corresponds to lilypond
        default bpm of 100.  If I set \tempo 4 = 60 the tempo event contains
        240, at \tempo 100, the event contains 480.

          bpm:   new_tempo:  quarter duration:
          60       240          1.0s    *4
          80       320          0.75s   *3
          120      480          0.5     *2


        So tempo value is a frequency and 240 / tempo desired seccond per note
        multiplier then is 240*4/tempo

        however, to create a midi file, I need to set a tempo in microseconds
        per quarter note. ie 60/BPM * 1e6 or 240/new_tempo * 1e6
        """
        ## code currently assumes only one tempo event at the start

        new_tempo = float(e[2])
        self.tempo = 240 / new_tempo * 1e6

        # for a piece which changes tempo, would need to create and event
        # to output a midi meta message for tempo change.

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

        # To help with accuracy, at this point we convert the time and duration
        # into clicks.  We choose 384 clicks per quarter note,
        # the input file thinks a quarter note takes .25s, so &4 for beats and
        # * 384 for clicks
        score_position = score_pos.ScorePosition(bar_num, bar_pos)
        note = lily_note.Note(
            midi_note,
            at=note_start * 4 * Staff.CLICKS_PER_BEAT,
            clicks=float(note_duration) * 4 * Staff.CLICKS_PER_BEAT,
            position=score_position,
        )

        self.note_list.append(note)  # all the notes in the score
        use_voice = self.find_free_voice(note.start_time, note)
        if use_voice.last_note_tied:
            logging.info(
                f"using tied voice: {use_voice} {use_voice.last_note.pitch}"
            )
        voice_untied = use_voice.append(note.start_time, note)
        if voice_untied:
            self.tied_voices_set.remove(use_voice)

        self.last_voice = use_voice  # remember voice for tie

    def show_notes(self):
        """
        iterate through the notes in the note_list
        """
        for n in self.note_list:
            print(repr(n))