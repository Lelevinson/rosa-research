"""Offline check (exam draft section 4b): do the scripted changes of the e1h_chg_* tasks trigger on equivalent calls in every arm? CPU only, saved dev traces only.
  nice uv run python research/studies/final_exam_draft_20261118/scripted_change_check.py
Trigger rule (e1h_fixture.EpisodeHook): the first `ros_end` event whose command equals ["ros2","param","get",<node>,<param>] exactly; then the parameter is set 0.3 s later.
For each saved e1h_chg_1 / e1h_chg_2 episode (all arms and studies of the candidate-count population): did the hook fire (`scripted_change` event)? did the model call a parameter read
for the watched node and parameter in any form (tool_start with name ros2_param_get and the watched parameter among its arguments)? Classes: fired; read_but_not_fired
(the model asked for the watched parameter but the exact command never ran: the missed-trigger defect, e.g. node written without the leading slash); never_read."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "research/studies/candidate_counts_20261118"))
import count_candidates as C  # noqa: E402
import ast  # noqa: E402

TASKS = {t["id"]: t for t in json.loads((ROOT / "research/studies/small_model_harness_20261115/e1h_tasks.json").read_text()) if t["id"].startswith("e1h_chg")}
rows, detail = [], []
for study, row in C.load_population():
    if row["task"] not in TASKS:
        continue
    change = TASKS[row["task"]]["change"]
    events = [json.loads(line) for line in (ROOT / row["trace_path"]).read_text().splitlines()]
    fired = any(e["kind"] == "scripted_change" or (e["kind"] == "handler" and e.get("event") == "scripted_change") for e in events)
    exact = [e for e in events if e["kind"] == "ros_end" and e.get("command") == ["ros2", "param", "get", change["node"], change["param"]]]
    reads = []
    for e in events:
        if e["kind"] == "tool_start" and e.get("name") == "ros2_param_get":
            try:
                args = ast.literal_eval(e["input"]) if isinstance(e["input"], str) else e["input"]
            except (ValueError, SyntaxError):
                continue
            text = json.dumps(args)
            if change["param"] in text and change["node"].lstrip("/").split("/")[-1] in text:
                reads.append(args)
    klass = "fired" if fired else ("read_but_not_fired" if reads else "never_read")
    system = f"{study}/{row['arm']}"
    rows.append(dict(system=system, task=row["task"], model=row["model"], seed=row["seed"], klass=klass, exact_command_seen=bool(exact), watched_param_in_tool_call=bool(reads), trace=row["trace_path"]))
    if klass == "read_but_not_fired":
        detail.append(dict(system=system, task=row["task"], model=row["model"], seed=row["seed"], first_read_args=reads[0], trace=row["trace_path"]))
by_system = defaultdict(Counter)
for r in rows:
    by_system[r["system"]][r["klass"]] += 1
exact_without_fire = sum(1 for r in rows if r["exact_command_seen"] and r["klass"] != "fired")
out = dict(episodes=len(rows), by_system={k: dict(v) for k, v in sorted(by_system.items())}, overall=dict(Counter(r["klass"] for r in rows)),
           exact_command_seen_but_hook_not_fired=exact_without_fire, read_but_not_fired_by_model=dict(Counter(r["model"] for r in rows if r["klass"] == "read_but_not_fired")),
           read_but_not_fired_first_args_sample=detail[:12],
           note="Systems whose runner has no EpisodeHook (for example Forge, if present) cannot show `scripted_change` events; they are listed as logged and must be checked separately.")
(HERE / "scripted_change_check.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("episodes", "by_system", "overall", "exact_command_seen_but_hook_not_fired", "read_but_not_fired_by_model")}, indent=1))
for d in detail[:8]:
    print(d["system"], d["task"], d["model"], d["seed"], d["first_read_args"], d["trace"].split("runs/")[-1])
