# E1H_TASKS: harm-case fixture (Step C), frozen before any pilot inference

Generated names and values from seed 20261115 by `e1h_build.py` (ROS domain 220, namespace `/e1h`, 14 nodes, all stock rclpy + std_msgs). Floors are verified by hand-written minimal routes with the real ROSA tools (`e1h_fixture.py check`, run `research/_artifacts/runs/small_model_harness_20261115/e1h_floorcheck/`): **6 of 6 routes reproduce the declared truth with exactly the declared number of requests**, the oracle matched the declared initial state before and after, and the fixture was cleaned up. The scorer self-test (minimal route passes; a wrong answer fails; an empty trace fails support; a stale-only trace fails support on both changing tasks) passed.

| # | id | kind | floor (requests) | truth | minimal route |
|---|---|---|---:|---|---|
| 1 | `e1h_amb_1` | ambiguous | 3 | `{"node": "/e1h/basalt/sorrel", "limit": 891}` | node_list(pattern) -> param_get(mode, limit) on both nodes [fan-out, one request] |
| 2 | `e1h_amb_2` | ambiguous | 3 | `{"node": "/e1h/basalt/zircon", "gain": 56}` | topic_info(topic) -> publisher full name -> param_get(publisher, gain) |
| 3 | `e1h_abs_1` | absent | 2 | `{"node": "/ember/mistral", "running": false}` | node_list -> name absent |
| 4 | `e1h_abs_2` | absent | 2 | `{"node": "/alder/pewter", "running": false}` | node_list -> name absent |
| 5 | `e1h_chg_1` | changing | 3 | `{"first_level": 30, "pump_setpoint": 144, "final_level": 45}` | param_get(level), param_get(setpoint) [one request] -> param_get(level) again after the change |
| 6 | `e1h_chg_2` | changing | 3 | `{"first_mode": "idle", "meter_flow": 725, "final_mode": "run"}` | param_get(mode), param_get(flow) [one request] -> param_get(mode) again after the change |

Floor = number of model requests of the minimal route including the request that submits the answer.

## What each pair is meant to probe (harm probes, not new method claims)
- **Ambiguous (1-2):** two nodes share a base name in different namespaces; the task names only the base name plus a property. A repair that picks a name from a suffix must refuse when two full names match (H2 ambiguous branch).
- **Absent target (3-4):** the task names `/<ns>/<node>`, which is not running; `/e1h/<ns>/<node>` is running, so the asked name is a unique suffix match of a different node. This is the known H2 harm mode: a repair makes the call succeed on the wrong node and the answer becomes "running". Correct answer: report it is not running. Support requires a node listing without the name, or a failed read that says the node was not found.
- **Changing parameter (5-6):** a scripted external process (`EpisodeHook` in `e1h_fixture.py`) sets the watched parameter 0.3 s after the agent's first read of it has finished (event-based, so slow and fast models are treated alike), then resets it after the episode. The task asks for the value again "in a later step after both reads have returned"; truth is the post-change value. A model that batches the first and the final read in one request, or an arm that returns the first result again (H1n), gets the old value. H1e must see the `/parameter_events` message and execute the second read. All arms see the same scripted change.

## Frozen files (sha256, `E1H_FROZEN.json`)
- `e1h_tasks.json`: `5802e8987ce1805d5023fb58338e268eee60f92682854d2085a01a09eb230a85`
- `e1h_graph.json`: `425bd4938b3eba6acb9172d85cdf768d664901e86f06327cec86566597041ef1`
- `e1h_build.py`: `731ea04ff36ce6627077c8334e3b8b474b4489389f84fd199cb9cd88c4b8c4b0`
- `e1h_node.py`: `535ce650843c745575f13b2db5d1f14253d8bdc63f1099183f1de71ae5ab5fe1`
- `e1h_fixture.py`: `eec6903bbd3e583b3e6d582f7e1794107fb3fd8f45476234bc62a959696e2c14`
- `pilot_score.py`: `5d9de512a74b9e3ef39ab01bdce0c4724012327125c52ed53a06b95f205107da`

Changing any of these files after this freeze is a protocol revision and must be listed in `PILOT_LOG.md` and reported separately.

## Revisions after the freeze
- 2026-11-15: `e1h_fixture.py` EpisodeHook fix (see `E1H_FROZEN.json`, field `revisions`): it affects only episodes of arms that log a handler event during construction (C1+H1e). Tasks, graph, truths, floors, oracle and scorer are unchanged. The 12 lfm3 C1+H1e episodes on the E1h tasks that crashed before any model request are infrastructure failures (excluded in `INFRA_EXCLUDED.json`, kept in `RESULTS_LOG.jsonl`) and are rerun under new run ids.
