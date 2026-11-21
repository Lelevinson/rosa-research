# Collision preflight of the exact round-2 rewrite (2026-11-17)

Code under test: `round2_harness.rewrite` (source SHA-256 `70459977409d94bb...`, file `build_round2_20261116/round2_harness.py`). The frozen design says: if two nested keys would become the same key the exact rule must not silently overwrite; if it can, the exact rule fails the preflight and applied use is blocked until a separate dated rule revision is authorized.

**Preflight verdict: FAIL.**

| case | answer | rewritten | events | values lost | silent overwrite |
|---|---|---|---|---|---|
| a model writes both the short and the full form of one entity as nested keys | `{"gains": {"quill": 1, "/plant32/quill": 2}}` | `{"gains": {"/plant32/quill": 2}}` | ['rewrite'] | ['1'] | True |
| the same, full form first | `{"gains": {"/plant32/quill": 2, "quill": 1}}` | `{"gains": {"/plant32/quill": 1}}` | ['rewrite'] | ['2'] | True |
| two different short forms of one entity | `{"gains": {"anvil": 5, "/anvil": 6}}` | `{"gains": {"/plant32/anvil": 6}}` | ['rewrite', 'rewrite'] | ['5'] | True |
| control: one short key, no collision | `{"gains": {"quill": 1, "/plant32/anvil": 2}}` | `{"gains": {"/plant32/quill": 1, "/plant32/anvil": 2}}` | ['rewrite'] | [] | False |
| control: values only | `{"node": "quill", "others": ["anvil"]}` | `{"node": "/plant32/quill", "others": ["/plant32/anvil"]}` | ['rewrite', 'rewrite'] | [] | False |

Reading: `rewrite` builds the new object with `out[new_key] = rewrite(v, ...)` for every key, and it logs only `rewrite` events, so two keys that map to the same full name keep only the last value and the loss is not logged. This is the exact rule of round 2; it was never exposed to the case in round 2 (2 rewritten answers, none with nested-key collisions).

## Revised rule (name-rewrite v2, `namefix_rule.py`) on the same cases

| case | rewritten | events | values lost |
|---|---|---|---|
| a model writes both the short and the full form of one entity as nested keys | `{"gains": {"quill": 1, "/plant32/quill": 2}}` | ['collision'] | 0 |
| the same, full form first | `{"gains": {"/plant32/quill": 2, "quill": 1}}` | ['collision'] | 0 |
| two different short forms of one entity | `{"gains": {"anvil": 5, "/anvil": 6}}` | ['collision', 'collision'] | 0 |
| control: one short key, no collision | `{"gains": {"/plant32/quill": 1, "/plant32/anvil": 2}}` | ['rewrite'] | 0 |
| control: values only | `{"node": "/plant32/quill", "others": ["/plant32/anvil"]}` | ['rewrite', 'rewrite'] | 0 |
| list items: short and full form of one entity | `{"nodes": ["quill", "/plant32/quill"]}` | ['collision'] | 0 |
| list items: two identical short forms | `{"nodes": ["quill", "quill"]}` | ['collision', 'collision'] | 0 |

**Revised rule preflight verdict: PASS** (no value lost in any case; collisions leave every colliding key or item unchanged and are logged as `collision`). The rule has 11 frozen unit tests (`tests/test_namefix.py`), including 500 random answers (no value dropped, idempotent) and equality with the round-2 rewrite on every collision-free case.
