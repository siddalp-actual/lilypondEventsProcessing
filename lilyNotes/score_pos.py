"""
internal used by lilyNotes classes.
Defines the ScorePosition class
"""

import logging

logger = logging.getLogger(__name__)


class ScorePosition:
    """
    Represented as [bar_number, bar_position]
    plus some arithmetic operations
    """

    beats_per_bar = 4  # time sig numerator
    beats_per_whole_note = 4  # time sig denominator

    def __init__(self, bar_num, bar_pos):
        """
        create a new one
        """
        self.bar_num = int(bar_num)
        self.bar_pos = float(bar_pos)

    @classmethod
    def from_array(cls, array):
        """
        build one from something that looks like [b, p]
        """
        assert len(array) == 2
        return cls(array[0], array[1])

    def as_array(self):
        """
        return an array
        """
        return [self.bar_num, self.bar_pos]

    def as_beats(self):
        """
        return a number of beats
        """
        return (
            self.bar_num * ScorePosition.beats_per_bar
            + self.bar_pos * ScorePosition.beats_per_whole_note
        )

    def bar_number(self):
        """
        extract the bar number
        """
        return self.bar_num

    @classmethod
    def set_beats_per_bar(cls, beats):
        """
        set the class variable
        """
        cls.beats_per_bar = int(beats)
        assert cls.beats_per_bar != 0

    @classmethod
    def set_time_signature(cls, numerator, denominator):
        """
        sets both the beats per bar and type of beat
        """
        cls.beats_per_bar = int(numerator)
        cls.beats_per_whole_note = int(denominator)

    def __str__(self):
        """
        what it looks like
        """
        return f"[bar: {self.bar_num}, {self.bar_pos}]"

    def __sub__(self, other):
        """
        subtract two positions, returning a difference
        """
        new_bar = self.bar_num - other.bar_num
        new_pos = self.bar_pos - other.bar_pos
        # handle a borrow
        logger.debug(
            "time signature %s / %s %s",
            self.beats_per_bar,
            self.beats_per_whole_note,
            self.beats_per_bar / self.beats_per_whole_note,
        )
        if new_pos < 0:
            new_pos += self.beats_per_bar / self.beats_per_whole_note
            new_bar -= 1
        return ScorePosition(new_bar, new_pos)

    def __eq__(self, other):
        """
        return true if two ScorePositions refer to the same location
        """
        return self.bar_pos == other.bar_pos and self.bar_num == other.bar_num

    def __ne__(self, other):
        return not self == other
