"""Independent offline recount. No imports from earlier scorers or model clients.

Run from the repository root with uv run --no-sync python <this file>.
Outputs are exclusive-create: a second run must use a new output directory.
"""
import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
OLD = ROOT / "research/studies/headroom_diagnostic_20261112"
RUNS = ROOT / "research/_artifacts/runs/headroom_diagnostic_20261112"


def first_object(text):
    """Decode the first JSON object in prose or a Markdown fence."""
    if not isinstance(text, str):
        return None
    for pos, char in enumerate(text):
        if char == "{":
            try:
                value, _ = json.JSONDecoder().raw_decode(text[pos:])
                if isinstance(value, dict):
                    return value
            except ValueError:
                continue
    return None


def exact(left, right):
    # Python considers True == 1; the protocol disallows wrong types.
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def successful(output):
    if isinstance(output, dict):
        return "error" not in output and all(successful(v) for v in output.values())
    if isinstance(output, list):
        return all(successful(v) for v in output)
    return True


def param_value(output, name):
    if not isinstance(output, dict) or name not in output:
        return None
    raw = output[name]
    if not isinstance(raw, str):
        return raw
    prefix, marker, value = raw.strip().partition(" value is: ")
    if not marker:
        return None
    if prefix == "Integer":
        return int(value)
    if prefix == "Double":
        return float(value)
    if prefix == "Boolean":
        return {"True": True, "False": False, "true": True, "false": False}[value]
    return value


def recount(path, task, arm):
    events = [(i, json.loads(line)) for i, line in enumerate(path.read_text().splitlines(), 1)]
    starts = [e for _, e in events if e["kind"] == "episode_start"]
    ends = [(i, e) for i, e in events if e["kind"] == "episode_end"]
    assert len(starts) == len(ends) == 1, path
    assert starts[0]["arm"] == arm and starts[0]["task"]["floor"] == task["floor"]
    assert task["floor"] == task["depth"] + 1
    request = 0
    pending = {}
    good = []
    seen = {}
    repeats = set()
    repeat_evidence = []
    issues = []
    for line, event in events:
        kind = event["kind"]
        if kind == "effective_request":
            assert event["request"] == task["request"], path
        elif kind == "model_start":
            request += 1
        elif kind == "tool_start":
            args = event["input"]
            if isinstance(args, str):
                args = ast.literal_eval(args)
            key = (event["name"], json.dumps(args, sort_keys=True, separators=(",", ":")))
            if key in seen and seen[key] < request:
                repeats.add(request)
                repeat_evidence.append({"request": request, "line": line, "name": key[0], "args": args})
            pending[event["run_id"]] = (event["name"], args, request, key)
        elif kind in ("tool_end", "tool_error"):
            name, args, req, key = pending.pop(event["run_id"])
            if kind == "tool_end" and successful(event["output"]):
                # Only successes in earlier requests qualify (not earlier calls
                # emitted together before the model could observe a result).
                good.append((name, args, event["output"], line))
                seen.setdefault(key, req)
        elif kind == "ros_end" and event["returncode"] != 0:
            issues.append({"line": line, "native_failure": event["command"]})
    assert not pending, path
    parsed = first_object(ends[0][1]["answer"])
    evidence = []
    for requirement in task["support"]:
        lines = []
        if requirement[0] == "param":
            _, node, param, value = requirement
            lines = [line for name, args, output, line in good
                     if name == "ros2_param_get" and args == {"node_name": node, "param_name": param}
                     and exact(param_value(output, param), value)]
        elif requirement[0] == "text":
            needle = requirement[1]
            if needle in task["request"]:
                lines.append("task text")
            lines += [line for _, _, output, line in good if needle in json.dumps(output, ensure_ascii=False)]
        else:
            raise ValueError(requirement)
        evidence.append({"requirement": requirement, "lines": lines, "holds": bool(lines)})
    is_exact = exact(parsed, task["answer"])
    return {"episode": path.parent.name, "trace": str(path.relative_to(ROOT)), "arm": arm,
            "model": starts[0]["provider"], "task": task["id"], "depth": task["depth"],
            "requests": request, "floor": task["floor"], "excess": request - task["floor"],
            "exact": is_exact, "support": evidence,
            "supported_complete": is_exact and all(e["holds"] for e in evidence),
            "parsed_answer": parsed, "expected_answer": task["answer"],
            "error": ends[0][1]["error"], "end_line": ends[0][0],
            "duplicate_requests": len(repeats), "duplicate_evidence": repeat_evidence,
            "native_failures": issues}


def main():
    task_path = OLD / "stage3_tasks.json"
    tasks = {t["id"]: t for t in json.loads(task_path.read_text())}
    rows, hashes = [], {}
    for dirname, arm, count in [("stage3b_20261113T155721Z", "A1", 48),
                                 ("stage3d_20261114T005613Z", "A2", 24)]:
        paths = sorted((RUNS / dirname).glob("*/trace.jsonl"))
        assert len(paths) == count
        for path in paths:
            start = json.loads(path.read_text().splitlines()[0])
            rows.append(recount(path, tasks[start["task"]["id"]], arm))
            hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    groups = defaultdict(list)
    for row in rows:
        for depth in ["all", row["depth"]]:
            groups[(row["arm"], row["model"], str(depth))].append(row)
    summary = []
    for (arm, model, depth), group in sorted(groups.items()):
        supported = [r for r in group if r["supported_complete"]]
        floor = sum(r["floor"] for r in supported)
        excess = sum(r["excess"] for r in supported)
        summary.append({"arm": arm, "model": model, "depth": depth, "episodes": len(group),
                        "supported": len(supported), "requests": sum(r["requests"] for r in supported),
                        "floor": floor, "excess": excess, "share": excess / floor if floor else None,
                        "duplicate_requests_supported": sum(r["duplicate_requests"] for r in supported),
                        "duplicate_requests_all": sum(r["duplicate_requests"] for r in group)})
    for p in [task_path, *(OLD / f"PROTOCOL_{s}.md" for s in ["STAGE3", "STAGE3B", "STAGE3D"])]:
        hashes[str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
    for filename, content in [("episode_recount.json", rows), ("aggregate_recount.json", summary),
                               ("INPUT_SHA256.json", hashes)]:
        with (OUT / filename).open("x") as handle:
            json.dump(content, handle, indent=2)
            handle.write("\n")
    print(json.dumps(summary, indent=2))
    for row in rows:
        if not row["supported_complete"]:
            print("FAIL", row["episode"], row["parsed_answer"], row["error"])


if __name__ == "__main__":
    main()
