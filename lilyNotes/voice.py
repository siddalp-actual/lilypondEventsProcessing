"""
A voice represents a sequence of related notes, eg an instrument or
vocal part.
There is a bunch of state it holds,such as volume, whether a tie
or slur is in progress, which need to be considered when adding notes
or articulation events.
"""
import logging

from lilyNotes import events


class Voice:
    """
    holds information about a voice
    """

    voice_num = 0
    # microsecond sacaled by clicks per beat
    BUSY_BUFFER = 1e-6 * 4 * 384

    def __init__(self, parent_staff):
        self.voice_num = Voice.voice_num
        self.parent_staff = parent_staff
        Voice.voice_num += 1
        self.volume = 0.65  # between mp and mf
        self.note_list = events.TimedList()
        self.last_note = None
        self.busy_until = 0
        self.last_note_tied = False
        self.tie_start_bar = 0
        self.slurred = False

    def __repr__(self):
        return f"Voice#{self.voice_num:0d}<{self.last_note.pitch:0d}>"

    def append(self, note_start_time, note, event_type="Note"):
        """
        appending a note to a voice might extend the last note, if we've had
        a tie

        returns True if a voice was untied
        """
        if event_type == "Dynamic":
            self.note_list.append(note_start_time, note, event_type)
            return False  # no note has been untied

        untied_note = False
        if self.last_note_tied:
            logging.debug("tieing %s", note.pitch)
            logging.debug("append: %s : %s", self.busy_until, note_start_time)
            assert self.last_note.pitch == note.pitch
            assert abs(self.busy_until - note_start_time) < Voice.BUSY_BUFFER
            self.last_note.extend(clicks=note.duration)
            self.busy_until += note.duration
            self.last_note_tied = False
            untied_note = True
        else:
            self.note_list.append(note_start_time, note, event_type=event_type)
            self.last_note = note
            self.busy_until = note_start_time + note.duration
            note.set_velocity(self.volume)  # current voice volume

        if self.slurred:
            self.last_note.set_in_slur()

        return untied_note

    def is_busy(self, time):
        """
        works out whether a voice would be busy at a particular time
        """
        if (
            time >= self.busy_until - Voice.BUSY_BUFFER
        ):  # allow a microsecond rounding
            return False
        return True

    def prep_tie(self):
        """
        flag this voice as having a pending tie
        """
        self.last_note_tied = True
        self.tie_start_bar = self.last_note.score_position.bar_num

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
        return self.volume
