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

## Prepared Windows/WSL services

From Windows PowerShell, start the local inference and tracing services with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-research.ps1
```

Add `-SmokeTest` to also run the live native-tool and custom-only ROSA readiness
checks through the evaluation project.

The sibling `rosa-evaluation` checkout is required. Ollama binds only to the
Windows WSL virtual adapter; its endpoint is refreshed in the evaluation
checkout's ignored `.env`. The helper uses a project-local Ollama 0.40.6 binary
under the parent workspace's `.local/ollama-0.40.6` when present. The older
installed 0.24.0 server cannot download the current Qwen3.5 manifests.
Phoenix remains loopback-only at http://localhost:6006.

Stop both project services with `scripts/stop-research.ps1`. Models and stored
traces are retained. Each teammate needs their own local setup; these scripts
do not manage ChatGPT credentials.

On Martin's prepared machine, `.venv` links to a Linux-hosted environment under
`~/.local/share/rosa-envs/` to avoid slow package imports through `/mnt/c`.
Phoenix state uses `~/.local/share/rosa-state/` through ignored local config.
Neither the environment links nor machine-specific config belongs in Git.

### Custom-only tools for model smoke tests

This branch adds `ROSA(..., load_default_tools=False)`, which constructs the
registry from only explicitly supplied tools/packages and avoids importing the
built-in ROS tool modules. Default behavior remains compatible with upstream.
Check the immutable `agent.tool_names` against your expected allowlist before
invocation. Custom tools themselves must be trusted; this option is not an OS
sandbox. Results from this branch must be labeled as a modified ROSA fork.

The isolation regression uses an offline scripted model and blocks network and
subprocess access while executing a mock read. Run it with:

```bash
uv run --locked python -m unittest discover -s tests -p test_mock_isolation.py -v
```

The prepared evaluation `.env` sets `OLLAMA_USE_MMAP=true` for memory-mapped
loading on this Windows host. Both readiness probes honor that setting; it
avoids the observed warm-up crash with Ollama's default non-mapped loading.
The model factory accepts `use_mmap=True` explicitly for equivalent settings
outside those probes. Model weights and the inference server are unchanged.

## Shared ROSA model interface

`rosa_backends.create_model` selects either the existing `ChatOllama` model or
the new `ChatSiwc` LangChain model. Both use the real ROSA executor and ordinary
LangChain tools; the adapter does not implement a second planning loop.

```python
from rosa_backends import create_model, create_mock_agent

# Local model, with the prepared machine's Ollama endpoint:
llm = create_model("ollama", model="qwen3.5:9b", base_url=ollama_url)
agent = create_mock_agent(llm, tools=allowed_tools, max_iterations=4)
answer = agent.invoke(query)

# For OAuth, use a validated memory-only session's SiwcBackend transport:
llm = create_model("siwc", model=selected_catalog_slug, siwc_transport=transport)
agent = create_mock_agent(llm, tools=allowed_tools, max_iterations=4)
answer = agent.invoke(query)
```

`create_mock_agent` requires a nonempty, unique tool allowlist, disables built-in
tool imports, checks the registered names, and disables accumulated chat history.
Its tools still need to be trusted. `ChatSiwc` maps system instructions to the
supported developer role, wraps the same function schemas in `rosa_tools`, and
maps native calls/results to LangChain tool messages with matching call IDs.
It rejects unknown tool names/namespaces and malformed arguments before dispatch.

The OAuth wire stream is buffered until completion; this first adapter does not
emit UI token deltas. Encrypted continuation items stay in a private, bounded
64-message in-memory store, outside traced messages and serialized model fields.
Missing native tool history fails closed. Call `llm.close()` when finished and
revoke the owning OAuth session. Sessions are short and request-budgeted; automatic
refresh is available in memory for bounded benchmark batches; persistent login
is not implemented. The shared probe handles cleanup.

For one-sign-in overnight batches, renewal preflight, checkpoint boundaries and
failure handling, see [the OAuth inspection and usage guide](OAUTH_OVERNIGHT.md).

Run the identical single/dependent mock cases from `rosa-evaluation`:

```bash
./run.sh research --probe-backends --backend ollama
./run.sh research --probe-backends --backend siwc
```

OAuth requires browser consent and uses a current account-catalog model; pass
`--model EXACT_SLUG` to choose explicitly. Each probe reports exact tool calls,
schemas, source hashes, configuration and Phoenix trace ID. These checks establish
integration, not stateful task success or model equivalence. Local Qwen uses its
recorded deterministic settings; OAuth sampling overrides are unsupported.

```bash
uv run --locked python -m unittest discover -s tests -p test_shared_backends.py -v
```

## Retained upstream tests

The `rosa_auth` package also provides a bounded, memory-only ChatGPT OAuth
readiness transport. From the sibling evaluation checkout, run
`./run.sh research --probe-siwc` and complete browser consent at the printed
loopback link. This checks the native transport directly; use the shared probe
above to exercise the new LangChain/ROSA adapter. Each run revokes its token session.
The default uv groups include the locked JWT verification dependencies.

Run its offline regressions without a browser or model request:

```bash
uv run --locked python -m unittest discover -s tests -p test_siwc.py -v
```

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
