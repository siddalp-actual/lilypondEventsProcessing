# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.9.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Midi from Notes file
#
# ## Background
# I have been using Lilypond to transcribe music we've been preparing for online church. It helps where parts need to be shared, fingering added, different harmonies used etc.  
#
# Optionally, Lilypond is able to output a midi file, which I can then play through a soft-synthesizer `timidity++` transforming into a `.wav` file, which can be used with `audacity` to create accurate backing tracks.
#
# Lilypond includes a sample script, `ly/articulate.ly` which enhances the performance of the music created from these midi files.  It has better support for dynamics, multiple instruments, and embellishments such as trills, ralls etc.  In a different project, I have looked at one way of enhancing midi performance through a mechanism to increase volume on each iteration (think verse) of a piece.
#
# ## Objective
# I wanted to achieve a simple thing, stress on a particular beat of the bar, eg beats 1 and 4 in 6/8 time.  
#
# ## Alternatives considered
#  1. munging the midi file - by this point in the pipeline, music representation is lost, there are just notes and times to play them
#  1. automatic markup of the `.ly` input to Lilypond - this pollutes the printed output with '<' accents
#  1. altering the sample `articulate.ly` function - I might come back to this, but after a lifetime of procedural programming, my brain really doesn't like the back-to-front thinking needed for functional programming in `Scheme`.
#
# ## Introduction
# Then I found the Lilypond `.notes` file.
#
# The `.notes` file is created by running an event listener against the creation of the lilypond output from the `.ly` file.
#
# A sample event listener is provided in `ly/event-listener.ly`. The recommendation is to copy this to somewhere else, modify it, and use with an
# ```
# /include "../petes-event-listener.ly"
# ```
# There is a problem with the output filename generator when the input filename contains spaces which results in the output filename using the string which starts after the last space in the filename.  Hence, where my input filename is 'music representation.ly', the output file uses the name from the space, and is then further thrown off by the backslash escape character, so only 'epresentation' makes it through into the notes file name.
#
# > I have tidied this problem up a bit in the ly/petes-event.listener.ly sample.
#
# One line of output is written to the `.notes` file for each event processed by the event listener.  I can add additional information by augmenting an existing event (eg I needed to be aware of bar positions, and after a fruitless search for 'newbar' events, ended up adding the bar number and bar position for each note seen by the note-event listener), or, by adding a new event listener.  For example, I have added a time-signature event listener.
#
# A trivial input and output is shown below:

# %%
# !cat ../music\ representation.ly

# %%
# !head ../music\ representation-unnamed-staff.notes

# %% [markdown]
# Which I can read and parse with the following python

# %%
'''
process the output from lilypond event-listener.ly
into a midi file
'''
import importlib
import logging
import sys

sys.path.append("/home/siddalp/github/lilypondEventsProcessing/")
import lilyNotes

FILE = "../ody-unnamed-staff.notes"
FILE = "../music representation-unnamed-staff.notes"
FILE = "/home/siddalp/audio/P256 St Theodulph/heodulph-unnamed-staff.notes"
FILE = "/home/siddalp/audio/Let nothing trouble you/Let nothing trouble you-unnamed-staff.notes"
FILE = "/home/siddalp/audio/Love Is/love is-unnamed-staff.notes"
FILE = "/home/siddalp/audio/Builders stone/Builders stone-unnamed-staff.notes"

logging.basicConfig(#filename='example.log', 
                    encoding='utf-8',
                    force=True,
#                    level=logging.WARNING
#                    level=logging.INFO
#                    level=logging.DEBUG
)



#
# Main starts here
#
importlib.reload(lilyNotes)
#import lilyNotes.Staff  ## not needed because module's __init__.ly does it for you

staff = lilyNotes.staff.Staff(FILE)


# %%
#dir(lilyNotes.Note.Note)
#globals()
for n in staff.voices[0].note_list:
    print(n)
print(staff.voices)

# %%
#staff.articulate([staff.more_staccato])
#staff.show_notes()
print(staff.performance)
for n in staff.performance[0]:
    print(n)


# %%
import mido

midi_file = mido.MidiFile(type=1)
midi_file.ticks_per_beat = 384
print(midi_file.ticks_per_beat)



def schedule(note, voice, event_list):

    on = mido.Message('note_on', channel=voice, note=note.pitch, velocity=int(note.volume * 127)
                     )
    event_list.insert(note.start_time, on, event_type="mido-note")
    
    off = mido.Message('note_off', channel=voice, note=note.pitch, velocity=0)
    
    event_list.insert((note.start_time + note.duration), off, event_type="mido-note")

track_zero = mido.MidiTrack()
print(f"tempo: {staff.tempo}")
tempo_msg = mido.MetaMessage('set_tempo', tempo=int(staff.tempo))
track_zero.append(tempo_msg)
midi_file.tracks.append(track_zero)
for i, v in enumerate(staff.performance):
    
    track_events = lilyNotes.events.TimedList()
    track = mido.MidiTrack()
    for n in v:
        if n.is_note() and not n.event.is_rest():
            schedule(n.event, i, track_events)
        
    last_time = 0
    for ev in track_events:
        time_delta = ev.event_time - last_time
        #new_time = int(mido.second2tick(time_delta, ticks_per_beat= midi_file.ticks_per_beat, tempo=staff.tempo))
        new_note = ev.event.copy(time=int(time_delta))
        #print(new_note)
        track.append(new_note)
        last_time = ev.event_time
        
    midi_file.tracks.append(track)

midi_file.save("../try.midi")

# %%
midi_file = mido.MidiFile(type=1)
midi_file.ticks_per_beat = 384
midi_file.tracks.append(track_zero)
for i, each_voice in enumerate(staff.voices):
    m_p = lilyNotes.performer.MidiPerformer(each_voice)
#    e_l = m_p.standard_articulation()
    functions = lilyNotes.performer.MidiPerformer.MIDI_ARTICULATION_FUNCTIONS
    functions.insert(0, lilyNotes.performer.Performer.show_event)
    track = m_p.to_midi_track(functions)
    midi_file.tracks.append(track)
    if i == 0:
        break
    
midi_file.save("../try2.midi")

# %%
print(staff.tempo)

# %%
[1, 2, 3][-1]

# %%
list = [1,2,3]
del list[1] #del list[1] #list.pop(1)
list

# %%
logging.error("%s", [])

# %%
"%s" % list

# %%
lilyNotes.performer.MidiPerformer.MIDI_ARTICULATION_FUNCTIONS

# %%
10.4166667*384*4


# %%
10.25*4*384

# %%
10.25*4*384 + 256

# %%
.16666667 *4*384

# %%
10.5833333 * 4 * 384

# %%
1e-6*4*384

# %%
