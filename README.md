# lilypondEventsProcessing
Towards better midi output from LilyPond transcriptions.  

I have extended the sample lilypond event listener and built python code to transform the output lilypond 'events' into midi.

Contents:
lilyNotes        : a python package containing events partser and classes to
                   assist with transforming into a chronological sequence of
                   note-on, note-off midi events.
ly/
  petes-event-listener.ly : an extension of the lilypond provided
                   event-listener.ly

tests/           : unit tests

notebookScript/
  Lilypond Notes to mid.py : Jupyter note book with commentary and sample
                   python code to use the above classes to create a midi file.
                   (I use JupyText to split the notebook into input and output)                      
