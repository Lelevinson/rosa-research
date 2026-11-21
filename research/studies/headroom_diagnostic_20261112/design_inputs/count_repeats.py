"""Repeat-rate counting script (addendum ROSA_repeat_rate_three_models_addendum.md). Offline; reads scored run folders only.

usage: python3 count_repeats.py <run_dir> [<run_dir> ...]   (each needs scores_3.json and labels_3.json; for the Qwen reference pass the Stage 3b run)
Prints a JSON list of per-run metrics; REPEAT_RATE_MODELS.md is built from it.

Definitions (fixed before any run):
- identical successful repeat: a request that contains an executed tool call whose name and parsed arguments equal an executed call from an EARLIER request of the
  same episode whose result succeeded (success = no 'error', 'Unable to find', 'Node not found' or 'not found' in the result text, as in the other design inputs).
  Same definition as REPEATS_READING.md without its `param_list` RED variant and without its fallback for subset repeats of a batch.
  Two equal calls inside the same request are not counted.
- R = share of supported-complete episodes with at least one identical successful repeat request.
- identical repeat requests / floor sum: repeat requests in supported-complete episodes over the floor sum of those episodes.
- excess share = sum(requests - floor) / sum(floor) over supported-complete episodes; codebook labels per request (not capped) from stage3_labels.py via labels_3.json,
  counted over supported-complete episodes with excess > 0.
- harness aborts: episodes whose episode_end has an error (schema validation, exception, timeout) or no answer.
- multi-call share: requests with more than one executed tool call over all requests of all episodes (final-answer requests included in the denominator).
"""
import ast, json, re, sys
from pathlib import Path

def sig(call):
    return json.dumps([call["name"], call["args"]], sort_keys=True)

def episode_requests(trace):
    reqs, cur, by_id, end = [], None, {}, {}
    for line in Path(trace).read_text().splitlines():
        e = json.loads(line); k = e["kind"]; tid = e.get("tool_run_id") or e.get("run_id")
        if k == "model_end":
            cur = dict(index=len(reqs) + 1, calls=[]); reqs.append(cur)
        elif k == "tool_start" and cur is not None:
            raw = e.get("input")
            try: args = ast.literal_eval(raw) if isinstance(raw, str) else raw
            except Exception: args = raw
            c = dict(name=e["name"], args=args, ok=None); cur["calls"].append(c); by_id[tid] = c
        elif k == "tool_end" and tid in by_id:
            by_id[tid]["ok"] = not re.search(r"error|Unable to find|Node not found|not found", str(e.get("output")), re.I)
        elif k == "episode_end":
            end = e
    return reqs, end

def metrics(run, provider="ollama"):
    run = Path(run)
    scores = [r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"] and r["provider"] == provider]
    labels = {e["episode"]: dict(e["labels"]) for e in json.loads((run / "labels_3.json").read_text())}
    sup = [r for r in scores if r["supported_complete"]]
    rep_eps, rep_tasks, rep_requests, all_requests, multi, aborts, kinds = 0, set(), 0, 0, 0, [], {}
    for r in scores:
        reqs, end = episode_requests(run / r["episode"] / "trace.jsonl")
        all_requests += len(reqs); multi += sum(len(q["calls"]) > 1 for q in reqs)
        if end.get("error") or not end.get("answer"):
            aborts.append((r["episode"], str(end.get("error"))[:90].replace("\n", " ")))
        if not r["supported_complete"]:
            continue
        seen, n_rep = set(), 0
        for q in reqs:
            if any(sig(c) in seen for c in q["calls"]):
                n_rep += 1
            seen |= {sig(c) for c in q["calls"] if c["ok"]}
        if n_rep:
            rep_eps += 1; rep_tasks.add(r["task"])
        rep_requests += n_rep
        if r["excess"] > 0:
            for k, l in labels[r["episode"]].items():
                if l in ("RED", "REC", "LATE", "NOARG", "EXPLORE"):
                    kinds[l] = kinds.get(l, 0) + 1
    floor_sum = sum(r["floor"] for r in sup); excess = sum(r["excess"] for r in sup)
    return dict(run=run.name, episodes=len(scores), supported=len(sup), R=(rep_eps / len(sup) if sup else None), repeat_episodes=rep_eps, repeat_tasks=len(rep_tasks),
                repeat_task_ids=sorted(rep_tasks), repeat_requests=rep_requests, floor_sum=floor_sum, excess=excess, excess_share=(excess / floor_sum if floor_sum else None),
                labels={k: kinds.get(k, 0) for k in ("RED", "REC", "LATE", "NOARG", "EXPLORE")}, aborts=aborts, requests=all_requests, multi_call_requests=multi,
                multi_share=(multi / all_requests if all_requests else None))

if __name__ == "__main__":
    print(json.dumps([metrics(p) for p in sys.argv[1:]], indent=1))
