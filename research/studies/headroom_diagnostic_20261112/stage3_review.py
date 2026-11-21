"""Print / compute Stage 3 labels per episode (offline). usage: stage3_review.py <repo_root> <run_dir> [show]"""
import json, re, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from extract_requests import extract_episode
from label_requests import parse_args
import stage3_labels as L

def requests_of(root, run, name, task):
    info, requests = extract_episode({"copy": str(run / name / "trace.jsonl"), "corpus": "s", "episode": name, "task": task}, root)
    out = []
    for r in requests:
        calls = [dict(name=c["name"], args={k: v for k, v in parse_args(c["args"]).items() if v is not None}, text=c["result"] or "",
                      ok=not re.search(r"error|Unable to find|Node not found|not found", c["result"] or "", re.I)) for c in r["calls"]]
        out.append(dict(index=r["request_index"], calls=calls, line=r["trace_line"]))
    return out

def main():
    root, run = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    scores = json.loads((run / "scores_3.json").read_text())
    result = []
    for s in scores:
        if s.get("status") or s["pilot"]:
            continue
        rq = requests_of(root, run, s["episode"], s["task"])
        labs = L.label_episode(s["task"], rq)
        result.append(dict(episode=s["episode"], task=s["task"], provider=s["provider"], depth=s["depth"], floor=s["floor"], requests=s["requests"],
                           excess=s["excess"], supported=s["supported_complete"], labels=[(k, l) for k, l in labs],
                           lines=[r["line"] for r in rq], calls=[" ; ".join(re.sub(r"/plant32/", "/", c["name"].replace("ros2_", "") + json.dumps(c["args"])[:60]) for c in r["calls"]) for r in rq]))
    (run / "labels_3.json").write_text(json.dumps(result, indent=1))
    if len(sys.argv) > 3:
        seen = set()
        for e in result:
            if not e["supported"] or e["excess"] <= 0:
                continue
            sig = (e["task"], e["provider"], tuple(l for _, l in e["labels"]))
            if sig in seen:
                continue
            seen.add(sig)
            print(f"\n## {e['episode']} {e['task']} {e['provider']} floor={e['floor']} n={e['requests']} excess={e['excess']}")
            for (k, l), c in zip(e["labels"], e["calls"]):
                print(f"  R{k:<2} {str(l):8} {c[:96]}")

if __name__ == "__main__":
    main()
