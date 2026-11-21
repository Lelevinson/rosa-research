"""Inspect original and new changing-task triggers without changing scores."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    tasks = {t["id"]: t for t in json.loads((HERE.parent / "small_model_harness_20261115/e1h_tasks.json").read_text())}
    controls = json.loads((HERE / "COMPARATORS_V2.json").read_text())
    matched = [json.loads(line) for line in (HERE / "RESULTS_MATCHED.jsonl").read_text().splitlines()]
    output = []
    for row in controls + matched:
        task = tasks.get(row["task"], {})
        change = task.get("change")
        if not change:
            continue
        trace = ROOT / row["trace_path"]
        events = [dict(json.loads(line), line=i) for i, line in enumerate(trace.read_text().splitlines(), 1)]
        reads = []
        for event in events:
            command = event.get("command", [])
            if event["kind"] == "ros_end" and len(command) == 5 and command[:3] == ["ros2", "param", "get"]:
                if "/" + command[3].lstrip("/") == change["node"] and command[4] == change["param"] and event["returncode"] == 0:
                    reads.append(dict(line=event["line"], command=command, stdout=event["stdout"]))
        fired = [e for e in events if e["kind"] == "scripted_change"]
        relative = [r for r in reads if not r["command"][3].startswith("/")]
        status = "trigger_fired" if fired else "missed_trigger_on_valid_relative_read" if relative else "no_successful_watched_read" if not reads else "missed_trigger_other"
        output.append(dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"],
                           frozen_supported_complete=row["supported_complete"], status=status, reads=reads,
                           change_lines=[e["line"] for e in fired],
                           reset_ok=[e.get("ok") for e in events if e["kind"] == "scripted_reset"], trace_path=row["trace_path"]))
    (HERE / "FIXTURE_EVENT_AUDIT.json").write_text(json.dumps(output, indent=2) + "\n")
    for arm in ["A1", "C1", "Forge"]:
        rows = [r for r in output if r["arm"] == arm]
        counts = {status: sum(r["status"] == status for r in rows) for status in sorted({r["status"] for r in rows})}
        print(arm, len(rows), counts)
    for row in output:
        if row["status"].startswith("missed_trigger"):
            print(json.dumps({k: row[k] for k in ["arm", "model", "task", "seed", "status", "frozen_supported_complete", "trace_path"]}))


if __name__ == "__main__":
    main()
