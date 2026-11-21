"""Stage 1c step 1 (offline): relabel the 12 Stage 1a Qwen A0 episodes. First pass only; manual labels are in manual_labels_1c.json."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_requests import extract_episode
import label_requests as L

def a0_episodes(repo_root):
    base = repo_root / "research/_artifacts/runs/headroom_diagnostic_20261112"
    runs = [Path(sys.argv[2]).resolve()] if len(sys.argv) > 2 else sorted(p for p in base.glob("stage1a_*") if p.is_dir() and "combined" not in p.name)
    for run in runs:
        if not run.is_dir():
            continue
        for scores in [json.loads((run / "scores_1a.json").read_text())]:
            for row in scores["episodes"]:
                if row["arm"] == "A0":
                    yield run, row

def main():
    repo_root = Path(sys.argv[1]).resolve()
    tasks = {t["id"]: t["request"] for t in json.loads((HERE / "vendor/baseline_protocol.json").read_text())["tasks"]}
    out = []
    for run, row in a0_episodes(repo_root):
        entry = {"copy": str(run / row["episode"] / "trace.jsonl"), "corpus": "stage1a", "episode": row["episode"], "task": row["task"]}
        info, requests = extract_episode(entry, repo_root)
        info["arm"], info["model"] = "A0", ("gpt-6-luna" if len(sys.argv) > 2 else "qwen3.5:9b")
        rows = L.analyse_episode(info, requests, tasks[row["task"]])
        for r in rows:
            r.update(supported_complete=row["supported_complete"], trace_file=info["trace"], floor_strict=L.FLOORS[row["task"]]["strict"], n_requests_episode=len(requests))
        out.append(rows)
    json.dump(out, sys.stdout, indent=1)

if __name__ == "__main__":
    main()
