"""Stage 3: first-pass relabel (codebook rules) of every request after the first, for review. Offline."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_requests import extract_episode
import label_requests as L

def main():
    repo_root, run = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    tasks = {t["id"]: t for t in json.loads((HERE / "stage3_tasks.json").read_text())}
    scores = {r["episode"]: r for r in json.loads((run / "scores_3.json").read_text())}
    out = []
    for name, row in sorted(scores.items()):
        if row.get("status") or row["pilot"]:
            continue
        entry = {"copy": str(run / name / "trace.jsonl"), "corpus": "stage3", "episode": name, "task": row["task"]}
        info, requests = extract_episode(entry, repo_root)
        info["arm"], info["model"] = "A0", ("qwen3.5:9b" if row["provider"] == "ollama" else "gpt-6-luna")
        rows = L.analyse_episode(info, requests, tasks[row["task"]]["request"])
        for r in rows:
            r.update(supported_complete=row["supported_complete"], depth=row["depth"], floor=row["floor"], provider=row["provider"], task_id=row["task"])
        out.append(rows)
    json.dump(out, sys.stdout, indent=1)

if __name__ == "__main__":
    main()
