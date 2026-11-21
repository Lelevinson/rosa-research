"""Extract one row per model request from preserved ROSA primary traces.

Offline only: reads frozen trace copies listed in INPUTS_FROZEN.json, performs
no inference and no ROS operation. Output feeds the Stage 0 labeling.

Trace schemas differ slightly between corpora (baseline uses `tool_run_id`,
narration/coverage use `tool_id`); this reader only relies on `kind`,
`message.tool_calls`, `usage`, `tool_start/tool_end` and `episode_end`.
"""
import hashlib
import json
import sys
from pathlib import Path

FROZEN = Path("research/_artifacts/autotool_iteration_20261112")


def read_trace(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def model_name(events):
    for event in events:
        if event["kind"] == "model_end":
            meta = event.get("response_metadata") or event["message"].get("response_metadata", {})
            configuration = meta.get("request", {}).get("configuration", {})
            return configuration.get("model") or meta.get("model_name") or meta.get("model") or "unknown"
    return "unknown"


def extract_episode(trace_entry, repo_root):
    """Return (episode_info, request_rows) for one preserved trace."""
    # Stage 1c reuses this reader for run folders: an absolute `copy` path overrides the frozen-inputs prefix.
    path = Path(trace_entry["copy"]) if Path(trace_entry["copy"]).is_absolute() else repo_root / FROZEN / trace_entry["copy"]
    raw = path.read_bytes()
    if trace_entry.get("sha256") and hashlib.sha256(raw).hexdigest() != trace_entry["sha256"]:
        raise SystemExit(f"hash mismatch for {path}")
    events = [json.loads(line) for line in raw.decode().splitlines()]
    start = events[0]
    arm = start.get("arm") or start.get("task", {}).get("arm")
    # Walk events in order. Tool starts after model_end k belong to request k;
    # each start is paired with its own tool_end by tool id (ends can arrive
    # out of order for parallel calls). Output is normalised to text because
    # baseline traces store dicts and later traces store Python repr strings.
    requests = []
    current = None
    by_id = {}
    for line_number, event in enumerate(events, start=1):
        kind = event["kind"]
        tool_id = event.get("tool_run_id") or event.get("tool_id") or event.get("run_id")
        if kind == "model_end":
            tool_calls = event["message"].get("tool_calls", [])
            current = {
                "request_index": len(requests) + 1,
                "trace_line": line_number,
                "content": event["message"].get("content") or "",
                "proposed": [{"name": c["name"], "args": c["args"]} for c in tool_calls],
                "calls": [],
                "invalid_tool_calls": len(event["message"].get("invalid_tool_calls", [])),
                "input_tokens": (event.get("usage") or {}).get("input_tokens"),
                "output_tokens": (event.get("usage") or {}).get("output_tokens"),
                "seconds": event.get("seconds"),
            }
            requests.append(current)
        elif kind == "tool_start" and current is not None:
            call = {"name": event["name"], "tool_id": tool_id, "start_line": line_number,
                    "args": event.get("input", event.get("arguments")), "result": None, "end_line": None}
            current["calls"].append(call)
            by_id[tool_id] = call
        elif kind == "tool_end" and tool_id in by_id:
            by_id[tool_id]["result"] = str(event.get("output"))
            by_id[tool_id]["end_line"] = line_number
        elif kind == "ros_end" and tool_id in by_id:
            by_id[tool_id].setdefault("ros_returncodes", []).append(event.get("returncode"))
    info = {
        "corpus": trace_entry["corpus"],
        "episode": trace_entry["episode"],
        "task": trace_entry["task"],
        "arm": arm,
        "model": model_name(events),
        "trace": str(FROZEN / trace_entry["copy"]),
        "sha256": trace_entry.get("sha256") or hashlib.sha256(raw).hexdigest(),
        "events": len(events),
        "error": events[-1].get("error"),
    }
    return info, requests


def main():
    repo_root = Path(sys.argv[1])
    frozen = json.loads((repo_root / FROZEN / "INPUTS_FROZEN.json").read_text())
    episodes = []
    for entry in frozen["traces"]:
        info, requests = extract_episode(entry, repo_root)
        info["requests"] = requests
        episodes.append(info)
    json.dump(episodes, sys.stdout, indent=1)


if __name__ == "__main__":
    main()
