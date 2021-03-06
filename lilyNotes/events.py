"""
Contains classes concerned with handling sequential events in the
score.  For instance, a time signature changes at various points
and a 'performer' needs to be aware of this
"""


class TimedElmt:
    """
    carve out the shape of an element in the TimedList
    """

    def __init__(self, event_time, event, event_type="Note"):
        self.event_time = event_time  # seconds from start
        self.event_type = event_type
        self.event = event

    def __str__(self):
        return f"[{int(self.event_time):06d}-{self.event_type}: {self.event}]"

    def is_note(self):
        """
        identify a note event
        """
        return self.event_type == "Note"


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

    def append(self, event_time, event, event_type="Note"):
        """
        Add (with an element block), to the tail of the list
        """
        t_elmt = TimedElmt(event_time, event, event_type=event_type)
        # must be for a timestamp at or after the last one
        try:
            assert (
                len(self.event_list) == 0
                or event_time >= self.event_list[-1].event_time
            )
        except AssertionError as a_error:
            self.diag_list_error(event.time)
            print("most likely, two lilypond runs in the notes file")
            raise a_error
        if event_type == "Note":
            event.check_valid()

        self.event_list.append(t_elmt)

    def diag_list_error(self, insert_time):
        """
        print out some diagnostics when we see append or insert failure
        """
        print(f"len event_list, {len(self.event_list)}")
        if len(self.event_list) != 0:
            print(f"last element time: {self.event_list[-1].event_time}")
            print(f"last eleemnt: {self.event_list[-1].event}")
        print(f"new event_time: {insert_time}")

    def bin_chop_loc(self, time, e_l):
        """
        recursively find the insertion point for given time
        """
        self.bin_chop_depth += 1
        try:
            assert self.bin_chop_depth <= TimedList.RECURSION_LIMIT
        except AssertionError as a_error:
            self.diag_list_error(time)
            print("most likely, two lilypond runs in the notes file")
            raise a_error

        # print(bin_chop_depth, len(e_l), e_l)
        # print(f"  searching: {time}")
        if len(e_l) == 0:
            return 0
        pos = max(0, int(len(e_l) / 2) - 1)
        if time <= e_l[pos].event_time:  # insert in left hand sub list
            # print("lh search")
            return self.bin_chop_loc(time, e_l[:pos])
        # print("rh search")
        return pos + 1 + self.bin_chop_loc(time, e_l[pos + 1 :])

    def insert(self, event_time, mido_note, event_type):
        """
        build data structure to hold timed event and insert
        """
        # el = {'at': event_time,
        #      'event': mido_note}
        t_elmt = TimedElmt(
            event_time=event_time, event=mido_note, event_type=event_type
        )
        self.bin_chop_depth = 0
        if event_type == "Note":
            mido_note.check_valid()
        insert_point = self.bin_chop_loc(event_time, self.event_list)
        self.event_list.insert(insert_point, t_elmt)

    def __iter__(self):
        """
        iterate over a frozen list of the events, allowing
        new ones to be scheduled into it by downstream processing
        """
        for event in self.event_list.copy():
            yield event
