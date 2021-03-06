"""
    This module contains classes to be used to read a LilyPond .notes file
    created using an events listener.  The events are parsed into a set of
    Notes which are held in Voices (think instrument or choral part).  The
    voices are held in a Score, which does the main parsing work.
"""


class Note:
    """
    represents a music note
    """

    STRESS_INCREMENT = 9

    def __init__(self, midi_pitch, at=0, clicks=0.25, position=None):
        self.pitch = int(midi_pitch)
        self.duration = clicks
        self.start_time = at
        self.volume = float(71 / 127)
        self.score_position = position
        self.slurred = False

    def __repr__(self):
        return f"{self.pitch} {self.duration} {int(self.volume * 127)}"

    def check_valid(self):
        """
        add in some validation checking
        """
        try:
            # assert type(self.duration) is int
            assert self.duration > 1
        except AssertionError as a_error:
            print(self)
            raise a_error

    def extend(self, clicks=0.25):
        """
        when a tie is spotted and we need to extend the previous note
        by the length of the new note
        """
        if self.is_rest():
            # should not be extending a rest, implies a tie
            raise ValueError
        self.duration += clicks

    def accent(self, stress_type):
        """
        stress this note (add velocity), typically for first beat in bar
        """
        if self.is_rest():
            return
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

    def set_velocity(self, velocity):
        """
        update the note's volume with an explicit midi velocity
        """
        self.volume = min(127, velocity)

    def staccato(self, factor=0):
        """
        shorten this note by a factor
        """
        if self.is_rest():
            return
        if factor == 0:
            factor = 0.1  # really short (for staccato dot)
        if not self.slurred:
            self.duration *= factor

    def is_rest(self):
        """
        rests use a dummy pitch of -1
        """
        return self.pitch == -1

    def as_mido_on_attrs(self):
        """
        return the note's midi attributes in a format suitable for
        generating a mido message
        """
        if self.is_rest():
            return None

        attribs = {
            "type": "note_on",
            "time": 0,
            "channel": 1,
            "note": self.pitch,
            "velocity": int(self.volume * 127),
        }
        return attribs

    def as_mido_off_attrs(self):
        """
        return the note's midi attributes in a format suitable for
        generating a mido message
        """
        if self.is_rest():
            return None

        attribs = {
            "type": "note_off",
            "time": self.duration,
            "channel": 1,
            "note": self.pitch,
            "velocity": 0,
        }
        return attribs
