# Native-read execution research review package

Read [REPORT.md](REPORT.md), [DECISION_LEDGER.md](DECISION_LEDGER.md), then
[PROTOCOL.md](PROTOCOL.md). Findings: ordinary concurrency helps CLI lists;
reused graph transport is much faster locally; no new adaptive algorithm is
supported and the historical list-latency opportunity is small.

## Code flow

`run_native.py::main` launches the disposable `fixture.py::main`, freezes source
hashes, shuffles controls, calls `executor.py::run_batch`, journals every result,
and cleans up owned processes. `run_batch` validates the whole list, schedules
approved reads through `read_one`, and optionally updates the established `AIMD`
rule. `command` admits only node info, topic info and service type. No changes
are registered in production ROSA. `run_native.py` also contains a deliberately
small persistent service-type graph lookup using the same public CLI API.

`inventory.py::main` parses original historical archives; `alternatives.py::main`
screens overlapping exact native commands. `audit.py::audit` checks new raw
journals independently; `summarize.py::main` reconstructs all metric tables.
`test_executor.py` covers authorization/validation and AIMD corner cases.

## Offline verification and replay

From this extracted directory, with Python3.12 and uv available:

```bash
uv run --offline --no-project --python /usr/bin/python3 verify.py
uv run --offline --no-project --python /usr/bin/python3 -m unittest -v test_executor.py
uv run --offline --no-project --python /usr/bin/python3 inventory.py
uv run --offline --no-project --python /usr/bin/python3 alternatives.py
uv run --offline --no-project --python /usr/bin/python3 audit.py evidence/native_v2
uv run --offline --no-project --python /usr/bin/python3 audit.py evidence/native_v3
uv run --offline --no-project --python /usr/bin/python3 summarize.py
```

`--offline` prevents downloads; `--no-project` avoids installing the ROSA project;
`--python` selects the existing system interpreter. If uv's usual cache is not
writable, set `UV_CACHE_DIR=/tmp/rosa-native-uv`. Verify first: inventory replay
may update its derived index's original archive paths on another machine, changing
that file's hash. Included original ZIPs provide a portable fallback. They are
evidence inputs, not commands or trusted executable code to run automatically.

## Native reproduction

Requires the existing ROSA uv environment and installed Jazzy ROS CLI/rclpy,
std_msgs, and system psutil. No installation or dependency changes were made.
Run from `/home/levinsonchen/project/rosa-research`:

```bash
source /opt/ros/jazzy/setup.bash
export PYTHONPATH="${PYTHONPATH}:/usr/lib/python3/dist-packages"
UV_CACHE_DIR=/tmp/rosa-native-uv uv run --offline --no-sync python \
  research/native_read_investigation_20261111/run_native.py \
  --out research/native_read_investigation_20261111/evidence/reproduction_new
```

`--no-sync` uses existing dependencies. `--out` must be a new directory; the
driver refuses to overwrite old evidence. It refuses an existing domain173 daemon,
uses localhost-only graph fixtures, and never executes arbitrary ROS services.
Local socket permission is required. The final source fixes graceful cleanup;
exact old frozen sources/protocol are also retained under `evidence/source_v2`
and `evidence/source_v3`. `--transport-only` reproduces the targeted continuation.
No physical robots, paid models or semantic answer mappings are involved.

## Evidence contents and limits

- `input/`: byte-preserved supplied research package members.
- `evidence/historical_archives/`: two complete original baseline/CodeAct ZIPs,
  with798 verified manifest members; lost dependency traces remain absent.
- `evidence/native_v1/`: failed sandbox attempt; no fixture was launched.
- `evidence/native_v2/`: completed width/error component and later import failure.
- `evidence/native_v3/`: completed persistent transport continuation.
- `evidence/source_v2`, `source_v3`: matching frozen experiment code/protocol.
- `evidence/source_snapshot`: local ROSA, Jazzy and R24 reference sources; their
  provenance explicitly says postexecution, not complete prefreeze closure.
- `evidence/cleanup_smoke.json`: separate successful graceful-cleanup test.
- `evidence/preservation_after.json`: unchanged pre-existing file checks, except
  verified append-only canonical context entry.
- `MANIFEST.json`, `SHA256SUMS`, `verify.py`: member identity verification.

Raw evidence and ZIP backups are locally ignored. Code and compact reports are
left unstaged for review, matching the user's no-commit requirement. The primary
archive and a second persistent local copy are on the same host; this is not
independent disaster recovery. No held-out agent, graph churn, full-answer quality,
or novel adaptive-policy performance is established.
