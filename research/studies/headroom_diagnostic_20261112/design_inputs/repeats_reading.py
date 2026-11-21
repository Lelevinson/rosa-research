"""Design input, Part A: read every RED (repeat) request in the Qwen A1 (Stage 3b) and A2 (Stage 3d) traces. Offline, saved traces only.
usage: python3 repeats_reading.py   -> writes REPEATS_READING.md next to this file. Not a diagnostic stage; no decision rule."""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
RUNS = STUDY.parents[1] / "_artifacts/runs/headroom_diagnostic_20261112"
RUN = {"A1": RUNS / "stage3b_20261113T155721Z", "A2": RUNS / "stage3d_20261114T005613Z"}
TASKS = {t["id"]: t for t in json.loads((STUDY / "stage3_tasks.json").read_text())}

def leaves(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if str(k).startswith("/"):  # mapping keys that are ROS names are answer values; field names like 'first' are not
                yield k
            yield from leaves(v)
    elif isinstance(x, (list, tuple)):
        for v in x: yield from leaves(v)
    else:
        yield x

def holds(text, value):
    s = str(value)
    if re.fullmatch(r"-?\d+", s):
        return re.search(r"(?<![\w/])" + re.escape(s) + r"(?![\w])", text) is not None
    if s in text:
        return True
    if s.startswith("/plant32/") and s.count("/") == 2:  # topic_info reports a node as 'Node name: x' plus 'Node namespace: /plant32'
        return re.search(r"Node name: " + re.escape(s.split("/")[-1]) + r"\b", text) is not None
    return False

def sig(c):
    return json.dumps([c["name"], c["args"]], sort_keys=True)

def events_of(run, ep):
    return [json.loads(l) for l in (run / ep / "trace.jsonl").read_text().splitlines()]

def episode_requests(run, ep):
    """Requests with proposed calls (model's own tool_calls), executed calls with results, content, done_reason."""
    reqs, cur, by_id = [], None, {}
    for n, e in enumerate(events_of(run, ep), 1):
        k = e["kind"]; tid = e.get("tool_run_id") or e.get("run_id")
        if k == "model_end":
            m = e["message"]
            cur = dict(index=len(reqs) + 1, line=n, content=m.get("content") or "", done=(m.get("response_metadata") or {}).get("done_reason"),
                       proposed=[dict(name=c["name"], args=c["args"]) for c in m.get("tool_calls", [])], calls=[])
            reqs.append(cur)
        elif k == "tool_start" and cur is not None:
            c = dict(name=e["name"], args=eval(e["input"]) if isinstance(e.get("input"), str) else e.get("input"), text=None, ok=None)
            cur["calls"].append(c); by_id[tid] = c
        elif k == "tool_end" and tid in by_id:
            t = str(e.get("output")); by_id[tid]["text"] = t
            by_id[tid]["ok"] = not re.search(r"error|Unable to find|Node not found|not found", t, re.I)
    return reqs

TRUNC = re.compile(r"truncat|\[\d+ more|\.\.\.\s*$", re.I)
rows = []
for arm, run in RUN.items():
    scores = {r["episode"]: r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"] and r["provider"] == "ollama"}
    labels = {e["episode"]: dict(e["labels"]) for e in json.loads((run / "labels_3.json").read_text())}
    for ep, s in sorted(scores.items()):
        if not s["supported_complete"] or s["excess"] <= 0:
            continue
        reqs = episode_requests(run, ep)
        answer_values = [v for v in leaves(TASKS[s["task"]]["answer"]) if str(v).strip()]
        for r in reqs:
            if labels[ep].get(r["index"]) != "RED":
                continue
            k = r["index"]
            dist, src_text, src_idx = [], "", []
            for c in r["calls"]:
                prior = [q for q in reqs[:k - 1] if any(sig(x) == sig(c) and x["ok"] for x in q["calls"])]
                if not prior:  # element-level repeat (e.g. a subset of an earlier batch): nearest request that read the same node/param
                    prior = [q for q in reqs[:k - 1] if any(x["name"] == c["name"] and x["ok"] and json.dumps(c["args"]) in json.dumps(x["args"]) for x in q["calls"])]
                if prior:
                    dist.append(k - prior[-1]["index"]); src_idx.append(prior[-1]["index"])
            if not dist:
                dist, src_idx = [None], [None]
            srcs = [q for q in reqs[:k - 1] if q["index"] in set(i for i in src_idx if i)]
            src_calls = [x for q in srcs for x in q["calls"] if x["ok"] and any(json.dumps(c["args"]) == json.dumps(x["args"]) and c["name"] == x["name"] for c in r["calls"])]
            src_text = " ".join(x["text"] or "" for x in src_calls)
            held_before = " ".join(x["text"] or "" for q in reqs[:k - 1] for x in q["calls"] if x["ok"])
            leaf_in_src = sum(holds(src_text, v) for v in answer_values)
            leaf_in_hist = sum(holds(held_before, v) for v in answer_values)
            first = min(i for i in src_idx if i) if any(src_idx) else None
            between = reqs[first:k - 1] if first else []
            if not between:
                what = "nothing"
            elif any(not x["ok"] for q in between for x in q["calls"]):
                what = "a failed call"
            else:
                what = "other tool calls"
            prev_prop = json.dumps(reqs[k - 2]["proposed"]) if k >= 2 else None
            same_string = json.dumps(r["proposed"]) == prev_prop
            nxt = reqs[k] if k < len(reqs) else None
            if nxt is None:
                nxt_kind = "end of episode"
            elif not nxt["calls"]:
                nxt_kind = "final answer"
            elif labels[ep].get(nxt["index"]) == "RED":
                nxt_kind = "another repeat"
            else:
                nxt_kind = "a new call"
            text = re.sub(r"\s+", " ", r["content"].strip().split("\n")[0])[:95] if r["content"].strip() else "none"
            said_done = bool(re.search(r"all the information|have all|final answer|complete (information|answer)|here'?s the complete|compile|summary|based on my investigation", r["content"], re.I))
            rows.append(dict(arm=arm, ep=ep, k=k, line=r["line"], tool=" ; ".join(f"{c['name'].replace('ros2_', '')}({', '.join(str(v).replace('/plant32/', '/') for v in c['args'].values())})" for c in r["calls"])[:90],
                             dist=max(d for d in dist if d) if any(dist) else None, n_calls=len(r["calls"]), ok_src=bool(src_calls), length=len(src_text), trunc=bool(TRUNC.search(src_text)),
                             leaf_src=leaf_in_src, leaf_hist=leaf_in_hist, n_leaf=len(answer_values), between=what, same=same_string, text=text, said_done=said_done,
                             has_text=bool(r["content"].strip()), done=r["done"], nxt=nxt_kind))
assert sum(r["arm"] == "A1" for r in rows) == 22 and sum(r["arm"] == "A2" for r in rows) == 22, [sum(r["arm"] == a for r in rows) for a in ("A1", "A2")]
out = ["# REPEATS_READING: why does Qwen repeat successful reads? (design input, not a stage; saved traces only)\n",
       "Population: every RED (repeat) request in the Qwen A1 traces (Stage 3b, 22) and Qwen A2 traces (Stage 3d, 22), supported-complete episodes with excess > 0, as labelled by `stage3_labels.py`. Nothing was run. Definitions:\n",
       "- **Not every RED is an identical repeat.** The Stage 3 labeller also gives RED to a `param_list` on a node when the parameter name is already in the task text (4 per arm). These have no identical earlier call; they are listed in the table (`dist` = n/a) and excluded from the counts, which use the identical repeats only (18 per arm).",
       "- **dist**: requests back to the nearest earlier request containing the identical call (for a batch, the largest over its calls); 1 = the request just before.",
       "- **src result**: the earlier result(s) of that identical call: all successful in this population; length in characters; `trunc` = a truncation marker in the text (none is expected; param/node results are short).",
       "- **ans in src / ans in history**: how many of the task's expected-answer values (leaves of `stage3_tasks.json` answer, keys included) appear in that earlier result / in all successful results before the repeat, out of the total. `yes` = the earlier result held an answer value; the history column says how much of the answer was already held.",
       "- **same string**: the proposed tool call(s) (name and arguments as stored in `model_end.tool_calls`) equal the immediately preceding request's. The trace stores parsed calls, not raw tokens, so this is the best available proxy for 'exact token string'.",
       "- **text**: first line of the model's text in the repeating request (`none` if empty); **claimed done** = that text matches a done phrase ('all the information', 'final answer', 'compile', 'summary', ...), a regex on my part.\n",
       "| arm | episode | req / line | call | dist | src len | trunc | ans in src | ans in history | between | same string | text before the repeat | claimed done | next |",
       "|---|---|---|---|---:|---:|---|---|---|---|---|---|---|---|"]
for r in rows:
    yn = "yes" if r["leaf_src"] else "no"
    if not r["ok_src"]:
        r.update(dist="n/a", between="n/a", length="n/a", same=False)
        yn = "n/a"
    out.append(f"| {r['arm']} | {r['ep']} | R{r['k']} / {r['line']} | {r['tool']} | {r['dist']} | {r['length']} | {'yes' if r['trunc'] else 'no'} | {yn} ({r['leaf_src']}/{r['n_leaf']}) | {r['leaf_hist']}/{r['n_leaf']} | {r['between']} | {'yes' if r['same'] else 'no'} | {r['text'].replace('|', '/')} | {'yes' if r['said_done'] else 'no'} | {r['nxt']} |")
def pct(n, d): return f"{n}/{d} ({100 * n / d:.0f}%)"
def counts(sub, label):
    sub = [r for r in sub if r["ok_src"]]
    n = len(sub)
    held_all = sum(r["leaf_hist"] == r["n_leaf"] for r in sub)
    return [f"| {label} | {n} | {pct(sum(r['dist'] == 1 for r in sub), n)} | {pct(sum(r['dist'] != 1 for r in sub), n)} | {pct(sum(r['ok_src'] for r in sub), n)} | 0/{n} | {pct(sum(bool(r['leaf_src']) for r in sub), n)} | {pct(held_all, n)} | {pct(sum(r['trunc'] for r in sub), n)} | {pct(sum(r['same'] for r in sub), n)} | {pct(sum(r['has_text'] for r in sub), n)} | {pct(sum(r['said_done'] for r in sub), n)} | {pct(sum(r['between'] == 'nothing' for r in sub), n)} | {pct(sum(r['nxt'] == 'another repeat' for r in sub), n)} / {pct(sum(r['nxt'] == 'final answer' for r in sub), n)} |"]
out += ["\n## Counts\n", "| group | repeats | distance 1 | distance > 1 | earlier result success | earlier result error | earlier result held an answer value | whole answer already in history | truncated | same string as preceding call | had model text | claimed done in the text | nothing in between | next: another repeat / final answer |", "|---|---:|---|---|---|---|---|---|---|---|---|---|---|---|"]
for label, sub in (("A1", [r for r in rows if r["arm"] == "A1"]), ("A2", [r for r in rows if r["arm"] == "A2"]), ("both", rows)):
    out += counts(sub, label)
(HERE / "REPEATS_READING.md").write_text("\n".join(out) + "\n")
n = len(rows)
print("\n".join(out[-6:]))
json.dump(rows, open(HERE / "repeats_rows.json", "w"), indent=1)
