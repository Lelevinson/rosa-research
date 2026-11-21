"""Event capture for the action judge: converts an exam action episode (pilot trace events + the executor's own event stream) into the development trace format that judge v1.2 reads
(`judge_v1_2.dev_events`): one `assistant` row per model response, one `tool` row per tool call (name, arguments, content) and one `executor_events` row. Stock read tools are mapped to the dev
names the judge knows: `ros2_param_get` -> `get_parameter` with content "Integer value is: N" when the result contains that line. Pure Python, no ROS."""
import ast
import json
import re

INTEGER_LINE = re.compile(r"Integer value is: (-?\d+)")


def arguments_of(event):
    value = event.get("input")
    if isinstance(value, dict):
        return value
    try:
        parsed = ast.literal_eval(value) if isinstance(value, str) else {}
    except (ValueError, SyntaxError):
        parsed = {}
    return parsed if isinstance(parsed, dict) else {}


def text_of(output):
    return output if isinstance(output, str) else json.dumps(output, default=str)


def dev_trace(events, executor_events):
    """events: the trace rows (dicts with `kind`). Tool calls are paired by run_id (tool_start / tool_end)."""
    ends = {e.get("run_id"): e for e in events if e["kind"] == "tool_end"}
    trace = []
    for event in events:
        if event["kind"] == "model_end":
            trace.append(dict(kind="assistant", content=(event.get("message") or {}).get("content"), tool_calls=(event.get("message") or {}).get("tool_calls")))
        elif event["kind"] == "tool_start":
            name, arguments = event["name"], arguments_of(event)
            content = text_of(ends[event["run_id"]]["output"]) if event.get("run_id") in ends else ""
            if name == "ros2_param_get":  # stock tool: arguments node_name/param_name, result {param: "Integer value is: N\n"}
                match = INTEGER_LINE.search(content)
                name, content = "get_parameter", (f"Integer value is: {match[1]}" if match else content)
                arguments = {"node_name": arguments.get("node_name"), "parameter_name": arguments.get("parameter_name", arguments.get("param_name"))}
            trace.append(dict(kind="tool", name=name, arguments=arguments, content=content))
    trace.append(dict(kind="executor_events", events=executor_events))
    return trace
