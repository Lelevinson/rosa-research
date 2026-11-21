"""One ordered event log per episode. Every event gets a global sequence number plus monotonic and wall times (the L4 requirement)."""
import datetime
import time


class EventLog:
    """sink: optional object with .add(kind, **values) and .rows (his Recorder). Every event is also written there as `macro_<kind>` with `trace_row` = the number of
    rows already in his trace, so the macro's internal reads have a sequence position inside his own trace."""
    def __init__(self, sink=None):
        self.events = []
        self._seq = 0
        self.sink = sink

    def add(self, kind, **fields):
        self._seq += 1
        if self.sink is not None:
            fields = {**fields, 'trace_row': len(self.sink.rows)}
        event = {'seq': self._seq, 'kind': kind, 't_monotonic': round(time.monotonic(), 6),
                 't_wall': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds'), **fields}
        self.events.append(event)
        if self.sink is not None:
            self.sink.add('macro_' + kind, **{k: v for k, v in event.items() if k != 'kind'})
        return self._seq

    def of(self, *kinds):
        return [e for e in self.events if e['kind'] in kinds]
