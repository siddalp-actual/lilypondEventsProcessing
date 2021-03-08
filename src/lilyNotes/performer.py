"""
A performer 'plays' events in a voice.  It can respond to dynamics
and let them have the desired effect on subsequent notes.

Dynamics include not only crescendo, rallentando, but changes in
time signature (effects the beat pattern)
"""
import copy
import logging

from lilyNotes import voice, events


class Performer:
    """
    encapsulates what a performer does
    """

    STACCATO_ER = 0.875  # fraction of note length to play

    def __init__(self, note_stream: voice):
        """
        set up the initial state of the performer
        """
        self.event_list = note_stream.note_list
        self.note_stream = note_stream
        self.volume = 0.65
        # initial time signatures are seen before notes, so voices don't
        # exist.  Get it from the staff
        self.beat_structure = note_stream.parent_staff.beat_structure

    def articulate(self, effects):
        """
        articulate the music according to the requested effects if any
        """
        new_stream = events.TimedList()
        for event in self.event_list:
            if event.is_note():
                new_event = copy.deepcopy(event.event)
                for effect in effects:
                    effect(self, new_event)  # apply the effect to the note
                new_stream.append(event.event_time, new_event, event.event_type)
            else:
                if event.event[1] == "dynamic":  # volume
                    self.volume = self.note_stream.set_volume(
                        str(event.event[2])
                    )
                if event.event[1] == "time-sig":
                    beats_per_bar = int(event.event[2])
                    self.beat_structure = {
                        2: [0],
                        3: [0],
                        4: [0],
                        6: [0, 0.5],
                        8: [0, 0.5],
                    }[beats_per_bar]
                    logging.info(
                        "performer sees time-sig %s %s",
                        beats_per_bar,
                        self.beat_structure,
                    )

        return new_stream

    @staticmethod
    def more_staccato(unused_self, note):
        """
        a helper function for use with articulate, makes playing less legato
        """
        note.staccato(factor=Performer.STACCATO_ER)

    def stress_beats(self, note):
        """
        only Score knows about bar position, but the way to stress a beat
        should be an attribute of the voice and we certainly shouldn't be
        stressing the second part of a tie
        """
        for stress_pos in self.beat_structure:
            if abs(float(note.bar_pos) - stress_pos) < 1e-6:
                note.accent(stress_pos)  # stress first beat of bar


class MidiPerformer(Performer):
    """
    not only performs the notes, but has specific midi
    characteristics, eg we must send a `midi_off` at the
    end of the note
    """
