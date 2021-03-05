from dataclasses import dataclass


@dataclass
class TimedElmt:
    """
    carve out the shape of an element in the TimedList
    """

    event_time: float  # seconds from start
    event: object


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

    def bin_chop_loc(self, time, e_l):
        """
        recursively find the insertion point for given time
        """
        self.bin_chop_depth += 1
        assert self.bin_chop_depth <= TimedList.RECURSION_LIMIT
        # print(bin_chop_depth, len(e_l), e_l)
        # print(f"  searching: {time}")
        if len(e_l) == 0:
            return 0
        pos = max(0, int(len(e_l) / 2) - 1)
        if time < e_l[pos].event_time:  # insert in left hand sub list
            # print("lh search")
            return self.bin_chop_loc(time, e_l[:pos])
        # print("rh search")
        return pos + 1 + self.bin_chop_loc(time, e_l[pos + 1 :])

    def insert(self, mido_note, event_time):
        """
        build data structure to hold timed event and insert
        """
        # el = {'at': event_time,
        #      'event': mido_note}
        el = TimedElmt(event_time=event_time, event=mido_note)
        self.bin_chop_depth = 0
        insert_point = self.bin_chop_loc(event_time, self.event_list)
        self.event_list.insert(insert_point, el)

    def __iter__(self):
        """
        iterate over events
        """
        for event in self.event_list:
            yield event
