"""Two development tasks through released Forge; no full-run mode.

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

PLAN = [dict(task="p3", model="lfm3:1.7b", seed=1),
        dict(task="u3", model="lfm3:1.7b", seed=2)]
OPTIONS = dict(temperature=0.7, num_ctx=65536, num_predict=4096)


class PilotOptionsClient(OllamaClient):
    """The only client override is the Ollama options dictionary."""
    def _build_options(self, sampling=None):
        return dict(OPTIONS, seed=self.pilot_seed)


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
    task = next(t for t in pilot.load_env("stage3").TASKS if t["id"] == cell["task"])
    original, changed = prompts()
    recorder.add("episode_start", arm="Forge", task={"id": task["id"], "floor": task["floor"]},
                 model=cell["model"], seed=cell["seed"], options=dict(OPTIONS, seed=cell["seed"]), prompts=changed, max_iterations=40)
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

    async def request_hook(request):
        body = json.loads(request.content)
        released = dict(body, options=OllamaClient._build_options(client))
        differences = [key for key in body if body[key] != released[key]]
        assert differences == ["options"], differences
        recorder.add("model_start", request=body, released_request=released,
                     changed_fields=differences, messages=body["messages"], schemas=body.get("tools", []))

    async def response_hook(response):
        await response.aread()
        try:
            raw = response.json()
        except ValueError:
            raw = {"body": response.text}
        recorder.add("wire_response", status=response.status_code, response=raw)
        if response.status_code == 200:
            recorder.add("model_end", message=raw.get("message"),
                         usage={"input_tokens": raw.get("prompt_eval_count", 0),
                                "output_tokens": raw.get("eval_count", 0)}, response_metadata=raw)

    client._http.event_hooks = {"request": [request_hook], "response": [response_hook]}
    context = ContextManager(strategy=TieredCompact(keep_recent=2), budget_tokens=65536,
                             on_compact=lambda event: recorder.add("compaction", **asdict(event)))
    runner = WorkflowRunner(client=client, context_manager=context, max_iterations=40,
                            on_message=lambda message: recorder.add("forge_message", message=asdict(message)))
    answer = error = None
    started = time.perf_counter()
    try:
        answer = await runner.run(workflow, task["request"], initial_messages=messages)
    except Exception as failure:
        error = repr(failure)
        recorder.add("model_or_runner_error", error=error)
    finally:
        await client.aclose()
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
    task = next(t for t in pilot.load_env("stage3").TASKS if t["id"] == cell["task"])
    score = scorer.score_events(task, events)
    ends = [e for e in events if e["kind"] == "episode_end"]
    usage = [e["usage"] for e in events if e["kind"] == "model_end"]
    record = dict(run_id=str(directory.relative_to(ROOT)), arm="Forge", **cell, **score,
                  llm_requests=sum(e["kind"] == "model_start" for e in events),
                  input_tokens=sum(u["input_tokens"] for u in usage), output_tokens=sum(u["output_tokens"] for u in usage),
                  native_ops=sum(e["kind"] == "ros_start" for e in events),
                  compactions=sum(e["kind"] == "compaction" for e in events), worker_error=worker_error,
                  error=ends[-1]["error"] if ends else "missing episode_end",
                  trace_path=str(trace.relative_to(ROOT)), trace_hash=hashlib.sha256(trace.read_bytes()).hexdigest() if trace.exists() else None)
    with (HERE / "RESULTS_LOG.jsonl").open("a") as handle:
        handle.write(json.dumps(record) + "\n")
    save(directory / "score.json", record)
    print(json.dumps(record), flush=True)
    return events


def freeze(out):
    original, changed = prompts()
    save(out / "plan.json", PLAN)
    save(out / "prompts.json", dict(c1=original, forge=changed))
    (out / "prompt.diff").write_text("".join(difflib.unified_diff(
        json.dumps(original, indent=2).splitlines(True), json.dumps(changed, indent=2).splitlines(True),
        fromfile="C1", tofile="Forge")))
    paths = [Path(__file__), HERE / "PROTOCOL_SMOKE.md", PILOT / "harness.py", PILOT / "run_pilot.py", STAGE3 / "stage3_tasks.json",
             STAGE3 / "stage3_graph.json", Path(inspect.getfile(WorkflowRunner)), Path(inspect.getfile(OllamaClient))]
    save(out / "freeze.json", dict(frozen_before_inference=True, source_revision=subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        sha256={str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        client_overrides=[name for name in PilotOptionsClient.__dict__ if not name.startswith("__")],
        inherited_send=PilotOptionsClient.send is OllamaClient.send,
        python=sys.executable, options=OPTIONS, plan=PLAN))
    (out / "run_smoke.py").write_bytes(Path(__file__).read_bytes())


def session(out, start_index=0):
    assert os.environ.get("ROS_DOMAIN_ID") == "220"
    assert os.environ.get("ROS_LOCALHOST_ONLY") == "1"
    out.mkdir(parents=True, exist_ok=False)
    freeze(out)
    save(out / "executed-plan.json", PLAN[start_index:])
    recorder = Recorder(out / "setup.jsonl")
    env = pilot.load_env("stage3")
    processes = handles = None

    def oracle(label):
        target = out / f"oracle-{label}"
        target.mkdir()
        bad = env.oracle(target, recorder)
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
        for index, cell in enumerate(PLAN[start_index:], start=start_index):
            if any(process.poll() is not None for process in processes):
                raise RuntimeError("fixture process exited")
            directory = out / f"{index:03d}-{cell['task']}-Forge-s{cell['seed']}"
            command = [sys.executable, str(Path(__file__).resolve()), "episode", str(directory), str(index)]
            worker_error = None
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
                raise RuntimeError("native guard rejection; inspect before continuing")
            if not pilot.check_ollama_context(out, cell["model"], recorder):
                raise RuntimeError("loaded context is not 65536")
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "session", "remaining", "episode"])
    parser.add_argument("output", type=Path)
    parser.add_argument("index", type=int, nargs="?")
    args = parser.parse_args()
    if args.mode == "prepare":
        args.output.mkdir(parents=True, exist_ok=False)
        freeze(args.output)
        save(args.output / "tool-schemas.json", {name: tool.args_schema.model_json_schema() for name, tool in available_tools().items()})
        print(args.output)
    elif args.mode == "episode":
        asyncio.run(episode(args.output, PLAN[args.index]))
    else:
        session(args.output, start_index=1 if args.mode == "remaining" else 0)
