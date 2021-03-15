"""
A performer 'plays' events in a voice.  It can respond to dynamics
and let them have the desired effect on subsequent notes.

Dynamics include not only crescendo, rallentando, but changes in
time signature (effects the beat pattern)
"""
import copy
import logging

import mido

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
        self.in_hairpin = False
        self.hairpin_event = None
        self.score_position = 0
        # initial time signatures are seen before notes, so voices don't
        # exist.  Get it from the staff
        self.beat_structure = note_stream.parent_staff.beat_structure
        self.beats_per_bar = note_stream.parent_staff.beats_per_bar

    def standard_articulation(self):
        """
        a set of articulation functions for normal use
        """
        return self.articulate(
            [
                Performer.set_volume_for_stream,
                Performer.more_staccato,
                Performer.stress_beats,
                #    Performer.bar_counter,
                #    Performer.show_event,
            ]
        )

    def articulate(self, effects):
        """
        articulate the music according to the requested effects if any
        """
        new_stream = events.TimedList()

        # First pass, get the notes and tee up some dynamics
        for event in self.event_list:
            event_added = False
            new_event = copy.deepcopy(event.event)
            if event.is_note():
                self.score_position = new_event.score_position
                new_event.volume = self.volume
            else:
                if new_event[1] == "start_hairpin":
                    self.start_hairpin(new_event)
                # need to track volume changes
                if event.event[1] == "dynamic":  # volume
                    self.volume = self.note_stream.set_volume(
                        str(event.event[2])
                    )
                    self.end_hairpin(self.volume)
                    # insert the dynamic so it precedes notes at the same
                    # point in the score
                    new_stream.insert(
                        event.event_time, new_event, event.event_type
                    )
                    event_added = True
            if not event_added:
                new_stream.append(event.event_time, new_event, event.event_type)

        logging.info("Performer.articulate finished first pass")

        # Second pass, add the performance effects
        for event in new_stream:
            if event.is_note():
                # Now the performer tracks the bar number so where necesary,
                # rates per beat can be used.
                self.score_position = event.event.score_position
                for effect in effects:
                    effect(self, event.event)  # apply the effect to the note
            else:
                if event.event[1] == "dynamic":  # volume
                    self.volume = self.note_stream.set_volume(
                        str(event.event[2])
                    )
                    self.end_hairpin(self.volume)

                if event.event[1] == "time-sig":
                    self.beats_per_bar = int(event.event[2])
                    self.score_position.set_beats_per_bar(event.event[2])
                    self.beat_structure = {
                        2: [0],
                        3: [0],
                        4: [0],
                        6: [0, 0.5],
                        8: [0, 0.5],
                    }[self.beats_per_bar]
                    logging.info(
                        "performer sees time-sig %s %s",
                        self.beats_per_bar,
                        self.beat_structure,
                    )
                if event.event[1] == "start_hairpin":
                    self.start_hairpin(event.event)
                    # print(event.event)

        return new_stream

    def start_hairpin(self, origin_event):
        """
        a stake in the ground from which we need to calculate the
        volume increase rate
        """
        if self.in_hairpin:
            print(self.in_hairpin, self.hairpin_event)
            raise ValueError
        assert not self.in_hairpin
        self.in_hairpin = self.score_position
        origin_event[3] = self.volume
        self.hairpin_event = origin_event

    def end_hairpin(self, new_volume):
        """
        the end of a crescendo or decrescendo may have been reached
        we can now calculate the volume increase or decrease per beat and
        apply it to any intervening notes
        """
        # if no hairpin has been started, there's nothing to do
        if not self.in_hairpin:
            return
        hairpin_start = self.in_hairpin
        hairpin_start_volume = self.hairpin_event[3]
        hairpin_end = self.score_position
        hairpin_end_volume = new_volume
        hairpin_beats = (hairpin_end - hairpin_start).as_beats()
        volume_rate = (hairpin_end_volume - hairpin_start_volume) / (
            hairpin_beats
        )
        logging.info(
            "end_hairpin sees: start %s:%s end %s,%s",
            hairpin_start,
            hairpin_start_volume,
            hairpin_end,
            hairpin_end_volume,
        )
        self.in_hairpin = False
        ## sub-script 4 item
        self.hairpin_event.append(volume_rate)

    ###
    ### The following methods are all note process for articulate
    ###

    def set_volume_for_stream(self, note):
        """
        extract the stream's current volume and push into a note
        """
        volume_increment = 0  # extra because in hairpin, may be negative
        if self.in_hairpin:
            # work out number of beats into hairpin
            hairpin_start = self.in_hairpin
            current_pos = self.score_position
            beats_into_hairpin = (current_pos - hairpin_start).as_beats()
            volume_increment = beats_into_hairpin * self.hairpin_event[4]
        note.set_velocity(self.volume + volume_increment)

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
            if abs(float(note.score_position.bar_pos) - stress_pos) < 1e-6:
                note.accent(stress_pos)  # stress first beat of bar

    def bar_counter(self, unused_note):
        """
        checking the effects are driven
        """
        print(self.score_position, self.in_hairpin)

    @staticmethod
    def show_event(unused_self, note):
        """
        what's in the note
        """
        print(note)


class MidiPerformer(Performer):
    """
    not only performs the notes, but has specific midi
    characteristics, eg we must send a `midi_off` at the
    end of the note
    """

    def standard_articulation(self):
        """
        a set of articulation functions for normal use
        """
        return self.articulate(
            [
                Performer.set_volume_for_stream,
                Performer.more_staccato,
                Performer.stress_beats,
                MidiPerformer.schedule_midi_events
                #    Performer.bar_counter,
                #    Performer.show_event,
            ]
        )

    def schedule_midi_events(self, note):
        """
        for each note we need a midi on and midi off event
        """
        note_on = mido.Message(**note.as_mido_on_attrs())
        self.event_list.insert(note.start_time, note_on, event_type="mido-note")

        note_off = mido.Message(**note.as_mido_off_attrs())
        self.event_list.insert(
            (note.start_time + note.duration), note_off, event_type="mido-note"
        )
