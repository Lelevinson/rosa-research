"""Opt-in bounded dependency scheduling; native adapters own tool execution.

Critical-path priority is an established list-scheduling heuristic. It uses only
declared durations, never measured future durations or evaluator expectations.
The coordinator alone ingests evidence and releases dependencies.
"""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from time import monotonic, perf_counter


@dataclass(frozen=True)
class Operation:
    name: str
    needs: frozenset = frozenset()
    nominal_seconds: float = 0.05

    def __post_init__(self):
        if not self.name or not isfinite(self.nominal_seconds) or self.nominal_seconds <= 0:
            raise ValueError('Operations require a name and positive finite duration.')


def critical_ranks(operations):
    """Own nominal duration plus the longest downstream nominal duration."""
    by_name = {op.name: op for op in operations}
    if len(by_name) != len(operations) or any(op.needs - by_name.keys() for op in operations):
        raise ValueError('Operation names must be unique and dependencies declared.')
    ranks, visiting = {}, set()
    def rank(name):
        if name in visiting:
            raise ValueError('Cyclic operation dependencies.')
        if name not in ranks:
            visiting.add(name)
            children = [op.name for op in operations if name in op.needs]
            ranks[name] = by_name[name].nominal_seconds + max((rank(c) for c in children), default=0.0)
            visiting.remove(name)
        return ranks[name]
    for name in by_name:
        rank(name)
    return ranks


def run_concurrent(task, invoke, *, workers=2, priority='ready', retries=1, deadline=12.0):
    """Run a fresh task's DAG with immediate dependency release after ingest.

    task.action(name) constructs grounded arguments from its accepted ledger.
    task.ingest(name, request, output) returns True only for an accepted complete
    operation. Workers return outputs; they never mutate task evidence or await
    another worker. Running native calls must have their own finite deadlines.
    """
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError('workers must be an integer from 1 to 8.')
    if priority not in ('ready', 'critical') or retries not in (0, 1):
        raise ValueError('Unknown scheduling priority or retry budget.')
    if not isfinite(deadline) or deadline <= 0:
        raise ValueError('A positive finite deadline is required.')
    if getattr(task, '_concurrent_used', False) or task.completed:
        raise ValueError('Every query requires a fresh evidence task.')
    task._concurrent_used = True
    operations = list(task.operations)
    ranks = critical_ranks(operations)
    positions = {op.name: index for index, op in enumerate(operations)}
    attempts = dict.fromkeys(positions, 0)
    active, events = {}, []
    overhead = 0.0
    started = monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while True:
            tick = perf_counter()
            active_names = {item['operation'] for item in active.values()}
            ready = [op for op in operations if op.name not in task.completed | active_names
                     and op.needs <= task.completed and attempts[op.name] < 1 + retries]
            # Fresh independent work is never displaced by a repeated failure.
            ready.sort(key=lambda op: (attempts[op.name],
                       -ranks[op.name] if priority == 'critical' else positions[op.name],
                       positions[op.name]))
            if monotonic() - started < deadline:
                for op in ready[:workers - len(active)]:
                    request = deepcopy(task.action(op.name))
                    attempts[op.name] += 1
                    event = dict(operation=op.name, attempt=attempts[op.name], request=request,
                                 submitted=monotonic(), ready_with=[r.name for r in ready],
                                 rank=ranks[op.name], output=None, accepted=False)
                    events.append(event)
                    active[pool.submit(invoke, deepcopy(request))] = event
            overhead += perf_counter() - tick
            if not active:
                break
            finished, _ = wait(active, return_when=FIRST_COMPLETED)
            # Simultaneously delivered futures are processed in submission order.
            for future in sorted(finished, key=lambda f: active[f]['submitted']):
                tick = perf_counter()
                event = active.pop(future)
                try:
                    output = future.result()
                except Exception as error:
                    output = {'error': type(error).__name__ + ': ' + str(error)}
                accepted = bool(task.ingest(event['operation'], event['request'], output))
                if accepted:
                    task.completed.add(event['operation'])
                event.update(output=deepcopy(output), accepted=accepted, ingested=monotonic())
                overhead += perf_counter() - tick
    report = task.report()
    return dict(events=events, report=report, complete=not report['unresolved'],
                attempts=attempts, scheduler_seconds=overhead,
                seconds=monotonic() - started, deadline_exceeded=monotonic() - started > deadline,
                workers=workers, priority=priority, ranks=ranks)
