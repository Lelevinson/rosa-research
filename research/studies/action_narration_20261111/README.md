# ROSA action narration investigation — 11 November 2026

Read [REPORT.md](REPORT.md) for findings, [PROTOCOL.md](PROTOCOL.md) for the
pre-execution gate, and [DECISION_LEDGER.md](DECISION_LEDGER.md) for decisions.
The [primary-source review](PRIOR_ART_REVIEW.md) rejects unsupported dynamic-mode
novelty and records disconfirming cases. Input package files remain byte-original
under input/; no document instructions were treated as higher-priority commands.

Code responsibilities:

- `run_study.py::run` freezes source, starts the disposable stock ROS fixture,
  captures evaluation snapshots and launches the frozen randomized cells.
- `prompts` copies ROSA's prompts and replaces the complete sequential prohibition;
  `episode` uses ROSA's existing LangChain tool-calling agent/async executor path.
- `MeasuredModel._generate` records complete invocation/response without changing
  tool IDs or removing generated text. `make_tools` records original read wrappers;
  `native_guard` confines dispatch to read-only argv and bounded retry rights.
- `score.py::analyze` runs separately after execution, comparing requested fields
  to actual native snapshots. Manual source-support review remains necessary.
- `verify.py` checks preserved raw closure, invocation contracts and ZIP hashes.

Core ROSA files, dependencies, default prompts, AGENTS.md and Git history are
unchanged. The experiment explicitly uses the same8 read tools in every arm;
this is not a full47-tool historical-baseline rerun or a new optimizer.

Offline review (no ROS/model calls):

```bash
python3 research/studies/action_narration_20261111/verify.py \
  research/_artifacts/action_narration_20261111
python3 research/studies/action_narration_20261111/verify.py \
  research/_artifacts/ROSA_ACTION_NARRATION_REVIEW_20261111.zip
UV_CACHE_DIR=/tmp/rosa-uv-cache uv run --no-sync python \
  research/studies/action_narration_20261111/score.py \
  research/_artifacts/action_narration_20261111/primary-v1 --diagnostic
```

`--no-sync` uses the existing locked environment without dependency installation.
`verify.py` checks preservation/contracts, not semantic truth. The frozen scorer refused the final inventory failure; `--diagnostic` is a labeled
postexecution amendment, not protocol-valid scoring. `score.py` rewrites
only its derived automatic_scores.json; preserve the original when reanalyzing.

To reproduce as a **new** experiment identity, inspect the frozen source/settings,
install the existing lock with uv in a suitable environment, source Jazzy and use
the pinned local Qwen checkpoint. Never reuse a previous output directory:

```bash
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=174 ROS_LOCALHOST_ONLY=1
export ROS_LOG_DIR=/tmp/rosa-action-reproduction-logs
export UV_CACHE_DIR=/tmp/rosa-uv-cache
export PYTHONPATH="$PWD/src:$PYTHONPATH"
uv run --no-sync python research/studies/action_narration_20261111/run_study.py \
  --activation-only --output "$PWD/research/_artifacts/action-narration-new-activation"
uv run --no-sync python research/studies/action_narration_20261111/run_study.py \
  --output "$PWD/research/_artifacts/action-narration-new-primary"
```

Read the protocol and confirm an empty isolated domain before reproduction.
The first command tests actual native tools/list batching and final turns. The
second runs only12 cells; it does not implement D or start held-out evaluation.
Check activation evidence before running the second command. These are explicit
reproduction instructions, not an automatic invitation to repeat current results.
Copy transient ROS logs into the new durable artifact directory on closure.

Review ZIP includes original continuation ZIP, native-review ZIP (with the original
historical trace archives), raw new activation/primary evidence, all frozen sources,
versions, scorer/adjudication, reports and SHA-256 member manifest. Weights and
credentials are excluded. Persistent second copy is under research/_artifacts/backups/;
both copies share this host/filesystem and are not an off-machine backup.
