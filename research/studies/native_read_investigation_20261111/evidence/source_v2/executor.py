"""Isolated read-only executor controls; no production ROSA registration changes."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import math
import re
import subprocess
import time

COMMANDS = {'node': ['ros2', 'node', 'info'],
            'topic': ['ros2', 'topic', 'info'],
            'service': ['ros2', 'service', 'type']}

def command(family, name):
    if family not in COMMANDS or not isinstance(name, str) or not re.fullmatch(
            r'/(?:[A-Za-z_][A-Za-z0-9_]*/)*[A-Za-z_][A-Za-z0-9_]*', name):
        raise ValueError('Only approved read family and absolute ROS entity names are allowed')
    return COMMANDS[family] + [name] + (['--verbose'] if family == 'topic' else [])

class AIMD:
    """Netflix AIMD rule, with disclosed small-pool initial/min/max adaptation."""
    def __init__(self):
        self.limit = 2

    def update(self, seconds, failed, inflight):
        if failed or seconds > 5:
            self.limit = max(1, math.floor(self.limit * .9))
        elif inflight * 2 >= self.limit:
            self.limit = min(4, self.limit + 1)

def read_one(family, name, position, queued):
    start = time.perf_counter()
    argv = command(family, name)
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=8, check=False)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        code, stdout, stderr = 124, str(exc.stdout or ''), str(exc.stderr or '')
    return {'position': position, 'name': name, 'command': argv, 'start': start,
            'end': time.perf_counter(), 'queue_seconds': start-queued,
            'returncode': code, 'stdout': stdout, 'stderr': stderr}

def run_batch(family, names, policy):
    if policy not in ('serial', 'fixed2', 'fixed4', 'aimd') or not names or len(names)>32:
        raise ValueError('Invalid policy or batch cardinality')
    for name in names:
        command(family, name)  # Validate the entire batch before any process starts.
    start = time.perf_counter()
    limiter = AIMD()
    width = {'serial':1, 'fixed2':2, 'fixed4':4, 'aimd':2}[policy]
    pending, results, decisions = {}, [], []
    next_position, policy_seconds = 0, 0.
    with ThreadPoolExecutor(max_workers=4) as pool:
        while next_position < len(names) or pending:
            while next_position < len(names) and len(pending) < width:
                pos = next_position
                decisions.append({'position':pos, 'width':width, 'inflight_before':len(pending),
                                  'time':time.perf_counter()})
                future = pool.submit(read_one, family, names[pos], pos, start)
                pending[future] = len(pending)+1
                next_position += 1
            done, _ = wait(pending, return_when=FIRST_COMPLETED)
            # Stable order resolves simultaneous completions reproducibly.
            for future in sorted(done, key=lambda f:f.result()['end']):
                inflight = pending.pop(future)
                result = future.result()
                results.append(result)
                if policy == 'aimd':
                    before = time.perf_counter()
                    limiter.update(result['end']-result['start'], result['returncode']!=0, inflight)
                    width = limiter.limit
                    policy_seconds += time.perf_counter()-before
    return {'family':family, 'policy':policy, 'wall_seconds':time.perf_counter()-start,
            'policy_seconds':policy_seconds, 'decisions':decisions,
            'results':sorted(results,key=lambda r:r['position'])}

def normalize(text):
    """Full line multiset comparison tolerates ROS graph enumeration order only."""
    return sorted(line.strip() for line in text.splitlines() if line.strip())
