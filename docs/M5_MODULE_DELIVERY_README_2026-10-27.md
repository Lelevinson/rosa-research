# Bounded ROSA macros: installation and delivery guide

Date: **2026-10-27**. Component0.2.0 inside the existing modified `jpl-rosa`1.0.10
distribution; this is not a separately published package or a new LLM.

## What is delivered

One state-changing capability selects among named, bounded six-joint UR5e poses.
A second, genuinely read-only capability checks controller activation and fresh
joint-state availability. Python performs predictable acquisition/execution/check
steps; the LLM still selects a skill and classifies its evidence. Use a fresh
invocation per task. This is a small fixed catalogue, not autonomous task planning.

The module reuses shared ROSA execution, feedback and report guards. Both primitive
and macro modes commit to one selected skill. Selecting the macro also starts the
routine immediately. Wrong initial selection can therefore remain a task failure;
do not assume that a correct readiness report fulfills a movement request.

## Existing Windows/WSL environment

Do not rerun the system setup script to enter the environment. In WSL:

```bash
source /opt/ros/jazzy/setup.bash
cd /mnt/c/Proj/robotics/introtorobotics/rosa-research
source /home/martin/.local/share/rosa-envs/research/bin/activate
python -m rosa_reliability.capability_demo --help
```

Those environment paths are specific to the current laptop. For another checkout
with ROS2 Jazzy/Gazebo Harmonic and the UR simulation/controller packages already
installed, clone `member/martin` and use its frozen Python dependencies:

```bash
git clone --branch member/martin https://github.com/Lelevinson/rosa-research.git
cd rosa-research
source /opt/ros/jazzy/setup.bash
uv sync --frozen
source .venv/bin/activate
python -m rosa_reliability.capability_demo --help
```

Python3.12 is the validated research runtime. Python dependency locking does not
install ROS, Gazebo, the UR robot description/simulation packages or controllers.
No fresh Windows/WSL/ROS installation is certified by the delivery acceptance.
Do not uv-sync/change model/dependency configuration during a frozen experiment.

## Wheel installation acceptance

M5 builds the wheel offline from the unchanged runtime source, installs it into
an empty target with `uv pip install --no-deps --no-index --target ...`, then uses
an isolated interpreter to import from that target and exercise both capabilities.
The interpreter retains the existing pinned dependencies. This validates the
installable artifact and public API; it is not a dependency-free/fresh-OS test.
The supplied wheel is the modified ROSA distribution, so do not confuse it with
an unmodified PyPI release sharing upstream version1.0.10.

## Deterministic Gazebo demonstration

Run only in simulation, one simulator at a time, with a new output directory:

```bash
python -m rosa_reliability.capability_demo --mode deterministic \
  --skill ur5e.inspect_readiness --output /tmp/rosa-m5-inspect-new
python -m rosa_reliability.capability_demo --mode deterministic \
  --skill ur5e.offset --output /tmp/rosa-m5-move-new
```

HOME=(0,-1.57,1.57,-1.57,-1.57,0); offset changes pan to0.18 and final wrist to0.16.
Targets remain in the existing0.4-rad HOME neighborhood. The trajectory is three
seconds; final joint tolerance is0.025 rad. Joint agreement is not collision/path
safety, torque safety, grasping or authorization for physical hardware.

## Model-backed demonstration

Use identical explicit movement requests with each backend, separately:

```bash
python -m rosa_reliability.capability_demo --mode ollama \
  --ollama-url YOUR_OLLAMA_ENDPOINT \
  --request "Move the arm to the registered ur5e.offset pose and report the verified outcome." \
  --output /tmp/rosa-m5-qwen-new
python -m rosa_reliability.capability_demo --mode siwc \
  --request "Move the arm to the registered ur5e.offset pose and report the verified outcome." \
  --output /tmp/rosa-m5-sol-new
```

The existing remembered authorization is opt-in and encrypted. New consent stays
manual. Never paste credentials into commands/reports. Explicit sign-out is
`python -m rosa_auth.remembered logout`; do not sign out during an active hosted
run. Tokens/scopes/cleanup remain governed by the existing adapter.

The public demo has eight inference calls,2,048 observed generated tokens,1,024
local tokens/call,10 native operations,16 tool attempts,3 corrections and at most
one movement dispatch. Its invocation defaults to180 seconds, with a300-second
external lifecycle deadline. It never retries a dispatched robot command.
The demo's `pass` field means accepted selected-skill report, not independently
proven user-intent correctness. Check selected skill, final joints and the request.
Do not treat demo runs as additional M4 observations.

## Evidence and limitations

M4 Sol:20/20 in each condition; calls68→38, mean task time16.42→9.73 seconds,
native operations38→40. Qwen:15/20→14/20, calls91→53, time133.49→85.18 seconds,
native50→48. Sol passed the preset retention screen; Qwen failed it. These are
short, fixed-catalogue simulation tasks against a shared repaired ROSA reference,
not superiority to untouched upstream ROSA or a general reliability guarantee.

Both-pass and all-attempt costs must accompany correctness. Five accepted grounded
Qwen reports answered the wrong/unresolved goal. Independent human clarification
review is deferred; existing ratings are Codex operator review. The forensic review
also shows rejected pre-selection readiness reads in primitive mode and unsuccessful
attempts to change an already selected inspection skill in macro mode.

Use the sibling evaluation repository's living project README, M5 research report,
claim ledger and frozen M4 artifacts for provenance. Memory, full JTVR, a general
planner, backend migration and physical robot deployment remain outside this delivery.
