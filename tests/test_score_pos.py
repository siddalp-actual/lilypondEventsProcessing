"""
some unit tests to verify the ScorePosition class
"""
import sys
import unittest

sys.path.append("../")

import lilyNotes.score_pos


class TestStuff(unittest.TestCase):
    """
    a wrapping class for the test cases
    """

    def test00_constructor(self):
        """
        construction and representation
        """
        thing = lilyNotes.score_pos.ScorePosition(1, 0.5)
        self.assertEqual(thing.as_array(), [1, 0.5])
        print(thing)
        self.assertEqual(str(thing), "[bar: 1, 0.5]")

    def test01_alternate_constructor(self):
        """
        alternate constructor
        """
        array = [2, 0.25]
        thing = lilyNotes.score_pos.ScorePosition.from_array(array)
        self.assertEqual(thing.as_array(), array)

    def test02_beats_per_bar(self):
        """
        beats per bar
        """
        thing = lilyNotes.score_pos.ScorePosition(1, 1 / 3)
        thing.set_beats_per_bar(3)
        self.assertEqual(lilyNotes.score_pos.ScorePosition.beats_per_bar, 3)
        self.assertEqual(thing.as_beats(), 4)

    def test03_equality(self):
        """
        test the class equality operators
        """
        thing_a = lilyNotes.score_pos.ScorePosition(1, 0.25)
        thing_b = lilyNotes.score_pos.ScorePosition(1, 1 / 4)
        thing_c = lilyNotes.score_pos.ScorePosition(2, 2 / 3)
        self.assertTrue(thing_a == thing_b)
        self.assertFalse(thing_a == thing_c)
        self.assertTrue(thing_a != thing_c)
        self.assertFalse(thing_a != thing_b)

    def test04_subtraction(self):
        """
        test the subtraction operator
        """
        thing_a = lilyNotes.score_pos.ScorePosition(1, 0.5)
        thing_b = lilyNotes.score_pos.ScorePosition(0, 0.5)
        # print((thing_a - thing_b).as_array())
        self.assertEqual(
            thing_a - thing_b, lilyNotes.score_pos.ScorePosition(1, 0)
        )
        # here we check a carry
        thing_c = lilyNotes.score_pos.ScorePosition(0, 0.75)
        self.assertEqual(
            thing_a - thing_c, lilyNotes.score_pos.ScorePosition(0, 0.75)
        )

    def test05_component(self):
        """
        return a component
        """
        thing = lilyNotes.score_pos.ScorePosition(15, 0.125)
        self.assertEqual(15, thing.bar_number())

    def test07_why_is_this_broken(self):
        """
        found this problem in a piece of music, but it doesn't show
        up in unit test.
        I think what went on was that one voice contained very few
        notes, so the start and end of hairpin appeared at the same
        point in that voice's timeline, leading to a as_beats() of
        0 and division by zero in the scaling of velocity.
        """
        hairpin_end = lilyNotes.score_pos.ScorePosition(52, 0.0)
        hairpin_end.set_beats_per_bar(4)
        hairpin_start = lilyNotes.score_pos.ScorePosition(47, 0.75)
        print((hairpin_end - hairpin_start))
        print((hairpin_end - hairpin_start).as_beats())


def do_tests():
    """
    run the tests
    """
    suite = unittest.TestLoader().loadTestsFromTestCase(TestStuff)
    unittest.TextTestRunner(verbosity=2).run(suite)


do_tests()
