"""Part A (static parity, no model calls): build each arm the way the DEV runner builds it and the way the EXAM worker builds it,
then dump everything the model or the executor can see, and compare byte for byte.

Dev path   (run_fair.episode / run_ablation.episode / run_namefix.episode) -> run_pilot.episode -> make_arm(...)  with the full dev task dict as context
Exam path  (queue_bridge.episode)                                            -> factory = {"E1": fair_arms.make_arm}.get(arm, exam_arms.make_arm)  with {"id","request"} as context

For every arm it captures: prompt messages, the wrapped tool list (name, description, JSON schema, class), the schemas bound to the model
(ChatOllama/OpenAI tool format) after the per-request visibility filter, executor class and settings, and the TEXT returned by each tool for
malformed arguments (strict pre-check / errors-as-text path). For the name fix it calls final_answer_tool on the same sample answers.
No model request is made. No ROS command is run (execute_ros_command is replaced by a function that fails the probe if it is reached).

Run:  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/parity_capture.py
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
for sub in ("exam_arms_20261121", "fairness_errors_as_text_20261117", "steady_loop_ablation_20261117", "name_fix_applied_20261117",
            "build_round1_20261115", "small_model_harness_20261115", "residual_failures_20261115"):
    sys.path.insert(0, str(STUDIES / sub))

import ablation_arms  # noqa: E402
import exam_arms  # noqa: E402
import fair_arms  # noqa: E402
import namefix_arm  # noqa: E402
import run_pilot  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from langchain_ollama import ChatOllama  # noqa: E402
from rosa.tools import ros2  # noqa: E402


class StubRecorder:
    def __init__(self):
        self.events = []

    def add(self, kind, **values):
        self.events.append(dict(kind=kind, **values))


def sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def reached_ros(command):
    raise AssertionError(f"a probe reached ROS: {command}")


ros2.execute_ros_command = reached_ros

TASK = json.loads((STUDIES / "name_fix_applied_20261117/namefix_tasks.json").read_text())[0]
DEV_CONTEXT = dict(env="namefix", task=TASK, ns="/nf")                       # run_pilot.episode: the full dev task dict
EXAM_CONTEXT = dict(env="namefix", task={"id": TASK["id"], "request": TASK["request"]}, ns="/nf")  # queue_bridge.episode: id + request only

SAMPLE_OUTPUTS = ["Node name: /nf/alpha_one\nNode namespace: /nf", "Node name: /nf/beta\nNode namespace: /nf"]
SAMPLE_ANSWERS = [
    {"nodes": ["alpha_one", "beta"]},                        # exact names
    {"nodes": ["/nf/alpha_one", "/nf/beta"]},                # full names
    {"nodes": ["alpha_on", "gamma"]},                        # near-miss + never seen
    {},                                                       # empty (finish retry path)
    {"count": 2},                                             # no names
]


def build(factory, name, context):
    """Everything the model/executor can see for one arm object."""
    recorder = StubRecorder()
    arm = factory(name, recorder, context) if name is not None else factory(recorder, context)
    llm = ChatOllama(model="qwen3.5:9b", base_url="http://127.0.0.1:1", temperature=0.7, seed=1, reasoning=False, num_predict=4096, num_ctx=65536,
                     client_kwargs={"timeout": 90})
    agent = run_pilot.PilotROSA(llm, arm)  # builds prompts, wrapped tools, executor exactly like the episode functions
    prompt_messages = [list(m) if isinstance(m, tuple) else m for m in arm.prompt_messages]
    rendered = agent._ROSA__prompts.format_messages(input="SAMPLE REQUEST", chat_history=[], agent_scratchpad=[])
    tools = agent.pilot_tools
    tool_dump = [dict(cls=type(t).__name__, name=t.name, description=t.description, schema=convert_to_openai_tool(t)["function"]["parameters"],
                      handle_validation_error=type(t.handle_validation_error).__name__, handle_tool_error=type(t.handle_tool_error).__name__) for t in tools]
    bound = [convert_to_openai_tool(t) for t in tools]
    visible = arm.visible_schemas(bound, [])
    executor = agent._ROSA__executor
    executor_dump = dict(cls=type(executor).__name__, max_iterations=executor.max_iterations, handle_parsing_errors=executor.handle_parsing_errors,
                         return_intermediate_steps=executor.return_intermediate_steps, early_stopping_method=executor.early_stopping_method)
    # malformed-argument probes: the text the model gets back and the events logged
    probes = {}
    for tool in tools:
        props = list(tool.args_schema.model_json_schema().get("properties", {})) if hasattr(tool.args_schema, "model_json_schema") else []
        for label, tool_input in (("unknown_field", {"__unknown__": 1}), ("object_in_first_field", {props[0]: {"nested": [1]}} if props else {"__unknown__": 2})):
            recorder.events.clear()
            try:
                text = tool.run(tool_input)
            except Exception as failure:  # a hard error (arm NO_ERRORTEXT would end here): record the type and text
                text = f"RAISED {type(failure).__name__}: {failure}"
            events = [{k: v for k, v in e.items() if k != "t"} for e in recorder.events]
            probes[f"{tool.name}/{label}"] = dict(text=text, events=events)
    return dict(prompt_messages=prompt_messages, rendered=[(m.type, m.content) for m in rendered], tools=tool_dump, bound_visible=visible,
                executor=executor_dump, probes=probes), arm


def finish_probe(arm):
    """final_answer_tool on the same samples (name-fix path). Returns result + events, arm name removed."""
    out = []
    for answer in SAMPLE_ANSWERS:
        recorder = arm.recorder
        recorder.events.clear()
        arm.tool_outputs = list(SAMPLE_OUTPUTS)
        arm.final_done, arm.final_answer, arm.final_invalid = False, None, 0
        try:
            result = arm.final_answer_tool({"answer": answer})
        except Exception as failure:
            result = f"RAISED {type(failure).__name__}: {failure}"
        events = []
        for e in recorder.events:
            e = {k: v for k, v in e.items() if k not in ("t", "cpu_seconds")}
            if "handler" in e:
                e["handler"] = "<arm>"
            events.append(e)
        out.append(dict(answer=answer, result=result, final_answer=arm.final_answer, final_done=arm.final_done, events=events))
    return out


def main():
    result = {}
    # dev M = ablation FULL (what the dev evidence measured), dev M+name fix = namefix applied arm; exam M = exam_arms.make_arm("M")
    dev_full, dev_full_arm = build(ablation_arms.make_arm, "FULL", DEV_CONTEXT)
    dev_namefix, dev_namefix_arm = build(lambda recorder, context: namefix_arm.make_arm(recorder, context), None, DEV_CONTEXT)
    exam_m, exam_m_arm = build(exam_arms.make_arm, "M", EXAM_CONTEXT)
    dev_e1, _ = build(fair_arms.make_arm, "E1", DEV_CONTEXT)
    exam_e1, _ = build(fair_arms.make_arm, "E1", EXAM_CONTEXT)  # queue_bridge: factory = fair_arms.make_arm for E1
    result["dev_full"], result["dev_namefix"], result["exam_m"], result["dev_e1"], result["exam_e1"] = dev_full, dev_namefix, exam_m, dev_e1, exam_e1
    result["finish_dev_namefix"] = finish_probe(dev_namefix_arm)
    result["finish_exam_m"] = finish_probe(exam_m_arm)
    result["finish_dev_full"] = finish_probe(dev_full_arm)
    (HERE / "parity_capture.json").write_text(json.dumps(result, indent=1, default=str, sort_keys=True))
    def norm(obj, drop_gate_shadow=False):
        """Arm name in the `handler` field is a log label (FULL / NAMEFIX / M), not behaviour: replace it. Optionally drop the shadow-gate log event."""
        if isinstance(obj, dict):
            return {k: ("<arm>" if k == "handler" and isinstance(v, str) else norm(v, drop_gate_shadow)) for k, v in obj.items()}
        if isinstance(obj, list):
            items = [norm(x, drop_gate_shadow) for x in obj]
            return [x for x in items if not (drop_gate_shadow and isinstance(x, dict) and x.get("event") == "gate_shadow")]
        return obj

    keys = ("prompt_messages", "rendered", "tools", "bound_visible", "executor")
    rows = []
    for label, a, b in (("EX-M vs dev FULL", "dev_full", "exam_m"), ("EX-M vs dev NAMEFIX arm", "dev_namefix", "exam_m"), ("E1 dev vs exam", "dev_e1", "exam_e1")):
        for key in keys:
            rows.append((label, key, sha(result[a][key])[:16], sha(result[b][key])[:16], sha(result[a][key]) == sha(result[b][key])))
        pa, pb = result[a]["probes"], result[b]["probes"]
        rows.append((label, "malformed-argument probes, raw", sha(pa)[:16], sha(pb)[:16], sha(pa) == sha(pb)))
        rows.append((label, "malformed-argument probes, arm label normalised", sha(norm(pa))[:16], sha(norm(pb))[:16], sha(norm(pa)) == sha(norm(pb))))
        # probes of every tool except final_answer (which carries the name-fix events only in EX-M)
        pa2 = {k: v for k, v in norm(pa).items() if not k.startswith("final_answer/")}
        pb2 = {k: v for k, v in norm(pb).items() if not k.startswith("final_answer/")}
        rows.append((label, "malformed-argument probes, label normalised, without final_answer", sha(pa2)[:16], sha(pb2)[:16], sha(pa2) == sha(pb2)))
    for label, a, b in (("EX-M vs dev NAMEFIX arm", "finish_dev_namefix", "finish_exam_m"), ("EX-M vs dev FULL (no name fix)", "finish_dev_full", "finish_exam_m")):
        fa, fb = result[a], result[b]
        rows.append((label, "final_answer_tool samples, label normalised", sha(norm(fa))[:16], sha(norm(fb))[:16], sha(norm(fa)) == sha(norm(fb))))
        fa2, fb2 = norm(fa, True), norm(fb, True)
        rows.append((label, "final_answer_tool samples, label normalised, shadow-gate event dropped", sha(fa2)[:16], sha(fb2)[:16], sha(fa2) == sha(fb2)))
        # what the model and the scorer can see: result text and accepted answer only
        va = [(x["result"], x["final_answer"], x["final_done"]) for x in fa]
        vb = [(x["result"], x["final_answer"], x["final_done"]) for x in fb]
        rows.append((label, "final_answer_tool samples: returned text + accepted answer only", sha(va)[:16], sha(vb)[:16], sha(va) == sha(vb)))
    sources = {}
    for name, path in (("ablation_arms.py", "steady_loop_ablation_20261117/ablation_arms.py"), ("harness.py", "small_model_harness_20261115/harness.py"),
                       ("run_pilot.py", "small_model_harness_20261115/run_pilot.py"), ("fair_arms.py", "fairness_errors_as_text_20261117/fair_arms.py"),
                       ("exam_arms.py", "exam_arms_20261121/exam_arms.py"), ("namefix_arm.py", "name_fix_applied_20261117/namefix_arm.py"),
                       ("round1_harness.py", "build_round1_20261115/round1_harness.py"), ("namefix_rule.py", "name_fix_applied_20261117/namefix_rule.py"),
                       ("answer_gate.py", "build_round1_20261115/answer_gate.py"), ("scorer_v2.py", "residual_failures_20261115/scorer_v2.py"),
                       ("queue_bridge.py", "custodian_stage1_20261121/queue_bridge.py")):
        sources[name] = hashlib.sha256((STUDIES / path).read_bytes()).hexdigest()
    import namefix_rule, answer_gate  # the modules both paths imported in this process
    sources["namefix_rule module path (both paths)"] = namefix_rule.__file__
    sources["answer_gate module path (both paths)"] = answer_gate.__file__
    (HERE / "parity_table.json").write_text(json.dumps(dict(rows=rows, sources=sources), indent=1))
    for row in rows:
        print(" | ".join(map(str, row)))
    print(json.dumps(sources, indent=1))


if __name__ == "__main__":
    main()
