"""Released Forge on the 80 pilot C1 cells, with matched Ollama transport.

Run with the isolated Forge uv environment. ROSA/LangChain dependencies are
reused read-only from the project environment; nothing is installed there.
"""
import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
import difflib
import hashlib
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PILOT = HERE.parent / "small_model_harness_20261115"
STAGE3 = HERE.parent / "headroom_diagnostic_20261112"
# Keep Forge's own environment first; expose only the installed integration deps.
sys.path.extend([str(ROOT / ".venv/lib/python3.12/site-packages"), str(ROOT / "src")])
sys.path.insert(0, str(PILOT))
import run_pilot as pilot
import harness
from menu_run_study import Recorder, guarded_native, save
from rosa.tools import ros2
from forge import Workflow, WorkflowRunner, ToolDef, ToolSpec, ContextManager, TieredCompact
from forge.clients.ollama import OllamaClient
from forge.core.messages import Message, MessageMeta, MessageRole, MessageType
from forge.tools import respond_tool

FROZEN_PLAN = json.loads((HERE / "FULL_PLAN.json").read_text())
PLAN = [cell for cells in FROZEN_PLAN["sessions"].values() for cell in cells]
PILOT_TRANSPORT = json.loads((HERE / "PILOT_TRANSPORT.json").read_text())
OPTIONS = dict(temperature=0.7, num_ctx=65536, num_predict=4096)


class PilotOptionsClient(OllamaClient):
    """The only client override is the Ollama options dictionary."""
    def _build_options(self, sampling=None):
        return dict(OPTIONS, seed=self.pilot_seed)


class MatchedTransport(httpx.AsyncBaseTransport):
    """Only add the pilot's explicit think field to the outgoing HTTP body."""
    def __init__(self, client, recorder, think, inner=None):
        self.client, self.recorder, self.think = client, recorder, think
        self.inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request):
        body = json.loads(request.content)
        released = dict(body, options=OllamaClient._build_options(self.client))
        body["think"] = self.think
        differences = [key for key in body if body.get(key) != released.get(key) or key not in released]
        assert set(differences) == {"options", "think"}, differences
        assert body["options"] == dict(OPTIONS, seed=self.client.pilot_seed)
        self.recorder.add("model_start", request=body, released_request=released, changed_fields=differences,
                          messages=body["messages"], schemas=body.get("tools", []))
        headers = {k: v for k, v in request.headers.items() if k.lower() != "content-length"}
        forwarded = httpx.Request(request.method, request.url, headers=headers, json=body, extensions=request.extensions)
        return await self.inner.handle_async_request(forwarded)

    async def aclose(self):
        await self.inner.aclose()


def prompts():
    original = pilot.prompt_for("C1") + [harness.FINAL_ANSWER_LINE]
    changed = [(role, text.replace("final_answer", "respond")) for role, text in original]
    assert all(role == "system" for role, _ in changed)
    return original, changed


def available_tools():
    from rosa.tools import ROSATools
    registry = {tool.name: tool for tool in ROSATools(ros_version=2).get_tools()}
    result = {name: registry[name] for name in harness.DOMAIN_TOOLS}
    assert len(result) == 12
    return result


def traced_callable(tool, recorder):
    def execute(**arguments):
        run_id = f"tool-{len(recorder.rows)}"
        recorder.active_tool = run_id
        recorder.add("tool_start", name=tool.name, input=arguments, run_id=run_id)
        try:
            # Same raw callable dispatch as Forge. Do not import C1 validation,
            # repair, caching, tool-error conversion or termination handling.
            output = tool.func(**arguments)
        except Exception as error:
            recorder.add("tool_error", error=repr(error), run_id=run_id)
            raise
        else:
            recorder.add("tool_end", output=output, run_id=run_id)
            return output
        finally:
            recorder.active_tool = None
    return execute


async def episode(out, cell):
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / "trace.jsonl")
    ros2.execute_ros_command = guarded_native(recorder)
    env = pilot.load_env(cell["env"])
    task = next(t for t in env.TASKS if t["id"] == cell["task"])
    original, changed = prompts()
    recorder.add("episode_start", arm="Forge", task={"id": task["id"], "floor": task["floor"]},
                 model=cell["model"], env=cell["env"], seed=cell["seed"], options=dict(OPTIONS, seed=cell["seed"]),
                 think=PILOT_TRANSPORT[cell["model"]]["think"], prompts=changed, max_iterations=40)
    recorder.add("effective_request", request=task["request"])
    tools = {name: ToolDef(ToolSpec(name=name, description=tool.description, parameters=tool.args_schema),
                           traced_callable(tool, recorder)) for name, tool in available_tools().items()}
    tools["respond"] = respond_tool()
    workflow = Workflow(name="rosa-read-only", description="Pilot read tools", tools=tools,
                        required_steps=[], terminal_tool="respond", system_prompt_template="")
    # Public initial_messages API retains each exact C1 system message separately.
    messages = [Message(MessageRole.SYSTEM, text, MessageMeta(MessageType.SYSTEM_PROMPT)) for _, text in changed]
    messages.append(Message(MessageRole.USER, task["request"], MessageMeta(MessageType.USER_INPUT)))
    client = PilotOptionsClient(model=cell["model"], base_url=pilot.S1.OLLAMA,
                                temperature=0.7, think=False, timeout=90)
    client.pilot_seed = cell["seed"]
    client.set_num_ctx(65536)

    response_count = 0
    async def response_hook(response):
        nonlocal response_count
        await response.aread()
        try:
            raw = response.json()
        except ValueError:
            raw = {"body": response.text}
        recorder.add("wire_response", status=response.status_code, response=raw)
        if response_count == 0:
            check = dict(model=cell["model"], env=cell["env"], task=cell["task"], seed=cell["seed"],
                         wire_think=PILOT_TRANSPORT[cell["model"]]["think"], think_matches_pilot=True,
                         no_thinking_observed=not bool(raw.get("message", {}).get("thinking")),
                         historical_raw_thinking_available=False, http_status=response.status_code,
                         trace_path=str((out / "trace.jsonl").relative_to(ROOT)))
            recorder.add("first_response_transport_check", **check)
            with (HERE / "TRANSPORT_CHECKS_FULL.jsonl").open("a") as handle:
                handle.write(json.dumps(check) + "\n")
        response_count += 1
        if response.status_code == 200:
            recorder.add("model_end", message=raw.get("message"),
                         usage={"input_tokens": raw.get("prompt_eval_count", 0),
                                "output_tokens": raw.get("eval_count", 0)}, response_metadata=raw)

    await client.aclose()
    client._http = httpx.AsyncClient(timeout=90, transport=MatchedTransport(
        client, recorder, PILOT_TRANSPORT[cell["model"]]["think"]), event_hooks={"response": [response_hook]})
    context = ContextManager(strategy=TieredCompact(keep_recent=2), budget_tokens=65536,
                             on_compact=lambda event: recorder.add("compaction", **asdict(event)))
    runner = WorkflowRunner(client=client, context_manager=context, max_iterations=40,
                            on_message=lambda message: recorder.add("forge_message", message=asdict(message)))
    answer = error = None
    started = time.perf_counter()
    hook = env.EpisodeHook(recorder) if hasattr(env, "EpisodeHook") else None
    try:
        if hook:
            hook.start()
        answer = await runner.run(workflow, task["request"], initial_messages=messages)
    except Exception as failure:
        error = repr(failure)
        recorder.add("model_or_runner_error", error=error)
    finally:
        await client.aclose()
        if hook:
            hook.stop()
    recorder.add("episode_end", answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / "answer.json", dict(**cell, answer=answer, error=error))


def append_result(directory, cell, worker_error):
    directory = directory.resolve()
    from importlib.util import spec_from_file_location, module_from_spec
    scorer_path = HERE.parent / "residual_failures_20261115/scorer_v2.py"
    expected = "c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9"
    assert hashlib.sha256(scorer_path.read_bytes()).hexdigest() == expected
    spec = spec_from_file_location("forge_frozen_scorer", scorer_path)
    scorer = module_from_spec(spec)
    spec.loader.exec_module(scorer)
    trace = directory / "trace.jsonl"
    events = [dict(json.loads(line), line=index) for index, line in enumerate(trace.read_text().splitlines(), 1)] if trace.exists() else []
    task = next(t for t in pilot.load_env(cell["env"]).TASKS if t["id"] == cell["task"])
    score = scorer.score_events(task, events)
    ends = [e for e in events if e["kind"] == "episode_end"]
    usage = [e["usage"] for e in events if e["kind"] == "model_end"]
    record = dict(run_id=str(directory.relative_to(ROOT)), dataset="matched_full", arm="Forge", **cell, **score,
                  llm_requests=sum(e["kind"] == "model_start" for e in events),
                  input_tokens=sum(u["input_tokens"] for u in usage), output_tokens=sum(u["output_tokens"] for u in usage),
                  native_ops=sum(e["kind"] == "ros_start" for e in events),
                  compactions=sum(e["kind"] == "compaction" for e in events), worker_error=worker_error,
                  thinking_responses=sum(bool(e["message"].get("thinking")) for e in events if e["kind"] == "model_end"),
                  error=ends[-1]["error"] if ends else "missing episode_end",
                  trace_path=str(trace.relative_to(ROOT)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest() if trace.exists() else None)
    with (HERE / "RESULTS_MATCHED.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    save(directory / "score.json", record)
    print(json.dumps(record), flush=True)
    return events


def freeze(out, cells):
    original, changed = prompts()
    save(out / "plan.json", cells)
    save(out / "prompts.json", dict(c1=original, forge=changed))
    (out / "prompt.diff").write_text("".join(difflib.unified_diff(
        json.dumps(original, indent=2).splitlines(True), json.dumps(changed, indent=2).splitlines(True),
        fromfile="C1", tofile="Forge")))
    paths = [Path(__file__), HERE / "PROTOCOL_FULL.md", HERE / "FULL_PLAN.json", HERE / "PILOT_TRANSPORT.json",
             PILOT / "harness.py", PILOT / "run_pilot.py", PILOT / "e1h_fixture.py", PILOT / "e1h_tasks.json",
             PILOT / "e1h_graph.json", PILOT / "e1h_node.py", STAGE3 / "stage3_fixture.py", STAGE3 / "stage3_node.py",
             HERE.parent / "residual_failures_20261115/scorer_v2.py", STAGE3 / "stage3_tasks.json",
             STAGE3 / "stage3_graph.json", Path(inspect.getfile(WorkflowRunner)), Path(inspect.getfile(OllamaClient))]
    save(out / "freeze.json", dict(frozen_before_inference=True, source_revision=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        client_overrides=[name for name in PilotOptionsClient.__dict__ if not name.startswith("__")],
        inherited_send=PilotOptionsClient.send is OllamaClient.send,
        python=sys.executable, options=OPTIONS, plan=cells))
    (out / "run_full.py").write_bytes(Path(__file__).read_bytes())


def session(out, cells, deadline):
    assert os.environ.get("ROS_DOMAIN_ID") == "220"
    assert os.environ.get("ROS_LOCALHOST_ONLY") == "1"
    out.mkdir(parents=True, exist_ok=False)
    freeze(out, cells)
    recorder = Recorder(out / "setup.jsonl")
    env = pilot.load_env(cells[0]["env"])
    processes = handles = None

    def oracle(label):
        target = out / f"oracle-{label}"
        target.mkdir()
        for attempt in range(3):
            try:
                bad = env.oracle(target, recorder)
                break
            except subprocess.TimeoutExpired as failure:
                recorder.add("oracle_cli_timeout", attempt=attempt, command=failure.cmd)
        else:
            raise RuntimeError("oracle CLI timed out three times")
        if bad:
            raise RuntimeError(f"oracle mismatch {label}: {bad}")

    try:
        pilot.S1.assert_domain_empty((env.NS,), recorder)
        # Fixture processes use the pilot's interpreter, not Forge's deliberately
        # minimal environment. The commands and fixture source stay unchanged.
        fixture_commands = [[str(ROOT / ".venv/bin/python"), *command[1:]] for command in env.commands()]
        processes, handles = pilot.S1.start_processes(fixture_commands, out, "fx", recorder)
        if not pilot.S1.wait_for([n["fqn"] for n in env.GRAPH["nodes"]], recorder, attempts=10):
            raise RuntimeError("fixture readiness failed")
        oracle("before")
        for cell in cells:
            index = PLAN.index(cell)
            if time.time() > deadline:
                raise RuntimeError("10-hour full-run wall cap reached")
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("fixture process exited")
            directory = out / f"{index:03d}-{cell['task']}-Forge-s{cell['seed']}"
            command = [sys.executable, str(Path(__file__).resolve()), "episode", str(directory), str(index)]
            worker_error = None
            with (HERE / "ATTEMPTS_FULL.jsonl").open("a") as handle:
                handle.write(json.dumps(dict(event="attempt_start", cell=cell, directory=str(directory))) + "\n")
            with (out / f"{directory.name}.worker.log").open("w") as log:
                worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = worker.wait(timeout=900)
                    if code:
                        worker_error = f"worker exit {code}"
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid, signal.SIGTERM)
                    try:
                        worker.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        os.killpg(worker.pid, signal.SIGKILL)
                        worker.wait()
                    worker_error = "900-second episode timeout"
            events = append_result(directory, cell, worker_error)
            if pilot.write_reached_ros(directory):
                raise RuntimeError("write reached ROS")
            if any(e["kind"] == "guard_rejection" for e in events):
                # A rejected command never reached ROS. Keep the shared guard
                # and Forge's completed recovery unchanged; do not abort later
                # independent cells merely because a malformed read was blocked.
                recorder.add("guard_rejection_recorded", directory=directory.name)
            if not pilot.check_ollama_context(out, cell["model"], recorder):
                raise RuntimeError("loaded context is not 65536")
            if any(e["kind"] in ("scripted_change_failed", "scripted_reset") and
                   (e["kind"] == "scripted_change_failed" or e.get("ok") is False) for e in events):
                raise RuntimeError("scripted fixture change/reset failed")
        oracle("after")
    except Exception as error:
        recorder.add("session_error", error=repr(error))
        raise
    finally:
        if processes is not None:
            pilot.S1.stop_processes(processes, handles, recorder)
            if not pilot.S1.verify_empty((env.NS,), recorder):
                recorder.add("cleanup_failed")
                raise RuntimeError("fixture cleanup failed")
            recorder.add("cleanup_ok", ok=True)
        pilot.S1.stop_daemon(recorder)


def full_run(out, resume=False):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    freeze(out, PLAN)
    done = set()
    if (HERE / "RESULTS_MATCHED.jsonl").exists():
        rows = [json.loads(line) for line in (HERE / "RESULTS_MATCHED.jsonl").read_text().splitlines()]
        done = {(r["model"], r["env"], r["task"], r["seed"]) for r in rows}
    if done and not resume:
        raise RuntimeError("Matched cells already recorded; use resume to avoid reruns")
    origin = ROOT / json.loads((HERE / "RUN_STATE.json").read_text())["run_root"]
    started = (origin / "freeze.json").stat().st_mtime if resume else time.time()
    deadline = started + 10 * 3600
    for name, cells in FROZEN_PLAN["sessions"].items():
        cells = [c for c in cells if (c["model"], c["env"], c["task"], c["seed"]) not in done]
        if not cells:
            continue
        print(json.dumps(dict(event="session_start", name=name, cells=len(cells))), flush=True)
        session(out / name.replace(":", "_"), cells, deadline)
    print(json.dumps(dict(event="full_run_complete", cells=len(PLAN))), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "full", "resume", "episode"])
    parser.add_argument("output", type=Path)
    parser.add_argument("index", type=int, nargs="?")
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.mode == "prepare":
        args.output.mkdir(parents=True, exist_ok=False)
        freeze(args.output, PLAN)
        save(args.output / "tool-schemas.json", {name: tool.args_schema.model_json_schema() for name, tool in available_tools().items()})
        print(args.output)
    elif args.mode == "episode":
        asyncio.run(episode(args.output, PLAN[args.index]))
    else:
        full_run(args.output, resume=args.mode == "resume")
