# Automatic capability discovery prototype

Start with [the standalone research report](REPORT.md). The result is negative for
automatic tool replacement: matching runtime values do not establish semantic
equivalence. The working prototype emits diagnostic overlap evidence and always
preserves the ordinary-call fallback.

This directory is opt-in. Nothing is registered with ROSA by importing the engine.
No dependency changes, model calls, paid APIs, native ROS operations, or robot
operations are required for tests/replay. The full study imports the real ROS 2
registry, then executes only explicitly selected pure local calculation functions
and synthetic fixtures.

From `/home/levinsonchen/project/rosa-research`:

```bash
.venv/bin/python -m unittest discover -s research/capability_discovery -p 'test_*.py' -v
.venv/bin/python research/studies/capability_discovery_20261110/audit_results.py research/studies/capability_discovery_20261110/results_corrected
```

To rerun all experiments and timing measurements into a **fresh** directory:

```bash
source /opt/ros/jazzy/setup.bash
.venv/bin/python research/studies/capability_discovery_20261110/run_study.py --output /tmp/rosa-capability-reproduction
.venv/bin/python research/studies/capability_discovery_20261110/audit_results.py /tmp/rosa-capability-reproduction
```

Existing results are never overwritten. Timings and process-local fingerprints
vary by run. Pair decisions and confusion counts are deterministic here.

The original implementation/results are preserved separately. To reproduce the
original run from the repository root after sourcing ROS, set its archived
runner's repository root explicitly (its directory has changed):

```bash
.venv/bin/python - <<'PY'
from pathlib import Path
import sys
root = Path.cwd()
sys.path.insert(0, str(root / 'research/studies/capability_discovery_20261110/initial_source'))
import run_study
run_study.ROOT = root
sys.argv = ['run_study', '--output', '/tmp/rosa-capability-original']
run_study.main()
PY
```

Its default freeze points to `initial_source/FREEZE.json`. It uses the original
text/schema behavior; it is not the recommended implementation.

Main files:

- `discovery.py`: metadata inventory, proposals, passive validation, registration
  invalidation and ordinary-call fallback seam.
- `ARCHITECTURE.md`: inspection of ROSA and installed LangChain source.
- `PROTOCOL.md`, `FREEZE*.json`, `CHANGELOG.md`: evaluation boundaries and history.
- `fixtures_*.py`, `test_discovery.py`, `run_study.py`: fixtures, behavioral checks,
  actual invocation and measurement harness. Semantic labels exist only in the
  harness and audit output, never in the mechanism.
- `results/`, `results_corrected/`: initial and corrected raw observations,
  inventory, pair witnesses/counterexamples, costs and preservation manifests.
- `audit_results.py`: reconstructs decisions from raw observations without
  dispatching tools. `regression_failures.txt` preserves the two found defects.

The experiment branch is `research/capability-discovery-20261110`. Files remain
uncommitted. The teammate's remote `origin/member/martin` ref and all pre-existing
tracked/research files checked by the run are unchanged.
