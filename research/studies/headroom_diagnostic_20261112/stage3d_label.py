"""Stage 3d: show and first-pass label the A2 excess requests with the Stage 3c definitions (PROTOCOL_STAGE3D.md). Offline.
  stage3d_label.py <repo_root> <a2_run_dir> firstpass|show
Reuses stage3c_label.first_pass/show_request unchanged; only the population differs (no 47/13 assertion)."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage3c_label as C
from stage3_review import requests_of

def load(repo_root, run):
    scores = {r["episode"]: r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"]}
    labels = {e["episode"]: e for e in json.loads((run / "labels_3.json").read_text())}
    items, episodes = [], {}
    for name, s in sorted(scores.items()):
        if not s["supported_complete"] or s["excess"] <= 0:
            continue
        reqs = requests_of(repo_root, run, name, s["task"])
        episodes[name] = dict(task=s["task"], provider=s["provider"], depth=s["depth"], excess=s["excess"], requests=reqs, template=s["template"])
        stage3 = dict(labels[name]["labels"])
        for r in reqs:
            if stage3.get(r["index"]) in C.EXCESS_LABELS:
                items.append(dict(episode=name, task=s["task"], provider=s["provider"], template=s["template"], request=r["index"], line=r["line"], stage3_label=stage3[r["index"]]))
    return items, episodes

if __name__ == "__main__":
    repo_root, run, cmd = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]
    items, episodes = load(repo_root, run)
    print(len(items), "excess requests in", len(episodes), "episodes; expected from scores:", sum(e["excess"] for e in episodes.values()))
    if cmd == "firstpass":
        for it in items:
            it["first_pass"], it["first_pass_of"], it["first_pass_note"] = C.first_pass(it, episodes[it["episode"]])
        (HERE / "stage3d_firstpass.json").write_text(json.dumps(items, indent=1))
    else:
        cur = None
        fp = {(i["episode"], i["request"]): i for i in json.loads((HERE / "stage3d_firstpass.json").read_text())} if (HERE / "stage3d_firstpass.json").exists() else {}
        for it in items:
            if it["episode"] != cur:
                cur = it["episode"]; ep = episodes[cur]
                print(f"\n## {cur} {ep['task']} excess={ep['excess']}\n  task: {C.TASKS[ep['task']]['request'][:200]}")
                for r in ep["requests"]:
                    hit = [i for i in items if i["episode"] == cur and i["request"] == r["index"]]
                    tag = f"  <<ITEM stage3={hit[0]['stage3_label']} first={fp[(cur, r['index'])]['first_pass']}" if hit and fp else ""
                    print(C.show_request(ep, r["index"], 100) + tag)
