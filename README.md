# ROSA Research

An experiment repository based on [NASA JPL ROSA](https://github.com/nasa-jpl/rosa),
starting from version 1.0.10. Each teammate can clone this repository, set up a
local environment, and develop their own ROSA experiments. Tracing and evaluation
tools live in the separate `rosa-evaluation` project.

## Setup

The local workflow uses Ubuntu 24.04, Python 3.12, ROS 2 Jazzy, uv, and Ollama.
ROS 2 must be sourced in your shell. If Bash already sources it, no additional
step is needed.

```bash
uv sync
```

The default dependency groups include Ollama support and tracing libraries.
`uv.lock` records the package versions. Keep `.venv/` local; uv recreates it.

`.python-version` requests Python 3.12. The `requires-python` field in
`pyproject.toml` declares the allowed Python range; it does not select one exact
interpreter. An existing compatible `.venv` is reused by `uv sync`.
For a first setup with ROS Jazzy, `uv sync --python /usr/bin/python3` explicitly
selects Ubuntu's Python instead of another installed or uv-managed interpreter.
You do not need to repeat that flag for ordinary syncs. `--locked` is optional:
it prevents uv from updating the lockfile if the dependency declarations change.

On a new checkout, copy `.env.example` to `.env` and set your Ollama endpoint and
model. Keep an existing `.env` if you have already configured one. When Ollama
runs on Windows, the endpoint may need the Windows host address visible from WSL.

## Start experimenting

Keep the ROSA implementation in `src/rosa/`. Add your own experiment scripts and
run them with uv, replacing the example path below with your script's path:

```bash
uv run path/to/your_experiment.py
```

For Ollama experiments, start Ollama and make the selected model available.
Your script must read any settings it needs from the environment or `.env`;
uv does not load `.env` automatically. No personal experiment script is included.

For traced runs, obtain the separate `rosa-evaluation` project and keep it next
to this checkout:

```text
project/
  rosa-research/
  rosa-evaluation/
```

From `rosa-evaluation`:

```bash
./tools/phoenix/run.sh start
./run.sh research --mode controlled
```

The controlled run uses scripted model responses and does not require Ollama.
Open http://localhost:6006 and select `rosa-local` to inspect its traces.
Use `./run.sh research --mode live` for a live Ollama run. The evaluation README
describes model configuration, validation cases, and trace inspection.

`rosa-baseline/` is an optional sibling checkout containing the reference ROSA
implementation for comparison with research changes. It is a separate local
checkout and is not included in this repository or required to start experiments.
The evaluation tools default to the research checkout. If you later create a
baseline checkout with the matching uv setup, `./run.sh baseline` selects it.
To validate both, use `./tools/phoenix/run.sh validate --variant research --variant baseline`
from the evaluation repository. The research-only commands above do not need it.

## Tests

```bash
uv run python -m unittest discover -s tests -v
```

The retained upstream tests cover ROSA tools. ROS 1 tests are skipped when the
ROS 2 environment is selected. These tests do not establish live model quality
or robot task success.

## Source and attribution

- `src/rosa/`: ROSA agent, prompts, and tools.
- `tests/`: retained upstream tests, excluding the removed TurtleSim demo tests.

The ROSA package retains its upstream `jpl-rosa` name and version. This repository
is an experiment fork, with no package publishing workflow. The original ROS 1
TurtleSim demo and its Docker setup have been removed.

ROSA originates from NASA JPL. Existing source copyright notices and the
[Apache 2.0 license](LICENSE) are preserved. Upstream documentation and release
history remain available in the [original repository](https://github.com/nasa-jpl/rosa).
