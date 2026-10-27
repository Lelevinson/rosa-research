"""Non-privileged observation cache. Actions and verification are never cached."""
from copy import deepcopy
import json
import time

READS = {'observe_robot', 'locate_object'}
ACTIONS = {'pick_object', 'place_object'}


class ObservationCache:
    def __init__(self, policy='none', ttl=5):
        if policy not in ('none', 'ttl', 'conservative'):
            raise ValueError('Unknown cache policy')
        self.policy, self.ttl = policy, ttl
        self.entries = {}
        self.metrics = {'sensor_backend_reads': 0, 'cache_hits': 0, 'cache_validation_calls': 0,
                        'sensor_backend_ms': 0.0, 'cache_policy_ms': 0.0, 'bytes_read': 0,
                        'action_invalidations': 0}

    def invalidate(self, events):
        if self.policy != 'conservative':
            return
        names = {name for event in events for name in event.get('invalidates', [])}
        for key in list(self.entries):
            if key[0] in names:
                del self.entries[key]

    def call(self, name, args, *, tick, invoke, on_cached, events=(), notifications_reliable=True):
        started = time.perf_counter()
        self.invalidate(events)
        key = (name, json.dumps(args, sort_keys=True))
        eligible = name in READS and self.policy != 'none'
        if self.policy == 'conservative' and name == 'locate_object' and not notifications_reliable:
            eligible = False
        if eligible:
            self.metrics['cache_validation_calls'] += 1
        cached = self.entries.get(key) if eligible else None
        if cached and 0 <= tick - cached[0] < self.ttl:
            self.metrics['cache_hits'] += 1
            self.metrics['cache_policy_ms'] += (time.perf_counter() - started) * 1000
            value = deepcopy(cached[1])
            on_cached(name, args, value)
            return value
        self.metrics['cache_policy_ms'] += (time.perf_counter() - started) * 1000
        before = time.perf_counter()
        response = invoke(name, args)
        value = response['output']
        if name in READS:
            self.metrics['sensor_backend_reads'] += 1
            self.metrics['sensor_backend_ms'] += (time.perf_counter() - before) * 1000
            self.metrics['bytes_read'] += len(json.dumps(value).encode())
        if eligible and 'error' not in value and value.get('status') != 'UNKNOWN':
            self.entries[key] = (tick, deepcopy(value))
        self.invalidate(response.get('events', []))
        if self.policy == 'conservative' and name in ACTIONS:
            self.entries.clear()
            self.metrics['action_invalidations'] += 1
        return value
