"""One ordered event log per episode. Every event gets a global sequence number plus monotonic and wall times (the L4 requirement)."""
import datetime
import time


class EventLog:
    def __init__(self):
        self.events = []
        self._seq = 0

    def add(self, kind, **fields):
        self._seq += 1
        event = {'seq': self._seq, 'kind': kind, 't_monotonic': round(time.monotonic(), 6),
                 't_wall': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds'), **fields}
        self.events.append(event)
        return self._seq

    def of(self, *kinds):
        return [e for e in self.events if e['kind'] in kinds]
