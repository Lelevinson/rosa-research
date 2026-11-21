"""Standalone mathematical illustrations; NEVER performs ROS/LLM calls.

The parameters are deliberately synthetic, not estimates of ROSA latency.
This code is for checking action contrasts and counterexamples only.
"""
from __future__ import annotations
import json
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Transport:
    cli_per_read: float
    persistent_setup: float
    persistent_per_read: float

    def validate(self) -> None:
        assert self.cli_per_read > self.persistent_per_read >= 0
        assert self.persistent_setup > 0


def costs_per_episode(n: int, c: Transport) -> dict:
    """Rent CLI until the excess rent pays for the persistent setup.

    Decision uses completed previous calls, not future N.
    Each episode has a cold persistent backend by assumption.
    """
    c.validate()
    assert n >= 0
    delta = c.cli_per_read - c.persistent_per_read
    threshold = math.ceil(c.persistent_setup / delta)
    rented = min(n, threshold)
    online = rented * c.cli_per_read
    if n > threshold:
        online += c.persistent_setup + (n - threshold) * c.persistent_per_read
    cli = n * c.cli_per_read
    persistent = (c.persistent_setup + n * c.persistent_per_read) if n else 0
    return {
        'eligible_reads': n,
        'switch_after_rented_reads': threshold,
        'always_cli': round(cli, 5),
        'always_persistent_cold': round(persistent, 5),
        'online_rent_then_buy': round(online, 5),
        'offline_oracle': round(min(cli, persistent), 5),
    }


def batch_runtime_ms(n: int, k: int, base_ms: float, safe_capacity: int, penalty: float) -> float:
    """Toy fixed-width batch; changing concurrency can cause contention.

    This is not a ROS concurrency or service-time model. Service times are
    deterministic and identical within each wave. Each wave waits for all reads.
    """
    assert n >= 0 and k >= 1 and safe_capacity >= 1 and base_ms > 0 and penalty >= 0
    if n == 0:
        return 0
    wave_ms = base_ms * (1 + penalty * max(k - safe_capacity, 0))
    return math.ceil(n / k) * wave_ms


def run() -> dict:
    t = Transport(cli_per_read=100, persistent_setup=450, persistent_per_read=25)
    lengths = [2] * 10 + [20] * 3
    rows = [costs_per_episode(n, t) for n in [2, 6, 7, 20]]
    totals = {key: round(sum(costs_per_episode(n, t)[key] for n in lengths), 5)
              for key in ('always_cli', 'always_persistent_cold', 'online_rent_then_buy', 'offline_oracle')}
    # A shared persistently initialized client changes the denominator. It is
    # not a sum of cold per-episode costs.
    pooled = t.persistent_setup + sum(lengths) * t.persistent_per_read
    concurrency = [
        {'regime': 'no_contention', 'width': k, 'makespan_ms': batch_runtime_ms(8,k,80,4,0.8)}
        for k in (1,2,4,8)
    ] + [
        {'regime': 'contention_after_2', 'width': k, 'makespan_ms': batch_runtime_ms(8,k,80,2,0.8)}
        for k in (1,2,4,8)
    ]
    return {
        'warning':'SYNTHETIC illustrative units. No ROS/LLM calls or measured speeds.',
        'transport': {'assumed_cli_per_read':100,'assumed_persistent_setup':450,'assumed_persistent_per_read':25},
        'episode_examples':rows,
        'mixed_episode_lengths': {'10 episodes':2,'3 episodes':20},
        'cold_per_episode_totals':totals,
        'always_persistent_if_shared_across_all_episodes':round(pooled,5),
        'concurrency_examples': concurrency,
    }

if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
