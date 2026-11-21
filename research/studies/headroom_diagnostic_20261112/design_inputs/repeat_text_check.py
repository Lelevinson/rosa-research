"""Read-only check of the 18 'claimed done' Qwen repeats (A1 Stage 3b and A2 Stage 3d): does the repeating request's text hold the full final answer as valid JSON,
and does it equal the answer given later? Reads saved traces and repeats_rows.json only. Writes REPEAT_TEXT_CHECK.md."""
import json, re
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
STUDY = HERE.parent
RUNS = STUDY.parents[1] / "_artifacts/runs/headroom_diagnostic_20261112"
RUN = {"A1": RUNS / "stage3b_20261113T155721Z", "A2": RUNS / "stage3d_20261114T005613Z"}
TASKS = {t["id"]: t for t in json.loads((STUDY / "stage3_tasks.json").read_text())}
rows = [r for r in json.loads((HERE / "repeats_rows.json").read_text()) if r["ok_src"] and r["has_text"] and r["said_done"]]
assert len(rows) == 18, len(rows)

def parse_json(text):
    """First valid JSON object in the text (fenced or bare); None if there is none."""
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try: return json.loads(m.group(1))
        except Exception: pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            depth += text[i] == "{"; depth -= text[i] == "}"
            if depth == 0:
                try: return json.loads(text[start:i + 1])
                except Exception: break
        start = text.find("{", start + 1)
    return None

def leaves(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if str(k).startswith("/"): yield k
            yield from leaves(v)
    elif isinstance(x, list):
        for v in x: yield from leaves(v)
    else: yield x

def holds(text, v):
    s = str(v)
    if re.fullmatch(r"-?\d+", s): return re.search(r"(?<![\w/])" + re.escape(s) + r"(?![\w])", text) is not None
    return s in text

def request_text(run, ep, k):
    n = 0
    for line in (run / ep / "trace.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "model_end":
            n += 1
            if n == k: return e["message"].get("content") or ""

def final_answer(run, ep):
    for line in (run / ep / "trace.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "episode_end": return e.get("answer")

out = []
for r in rows:
    run = RUN[r["arm"]]
    text = request_text(run, r["ep"], r["k"])
    task_id = r["ep"].split("-")[1]
    keys = list(TASKS[task_id]["answer"].keys()); values = [v for v in leaves(TASKS[task_id]["answer"]) if str(v).strip()]
    final = final_answer(run, r["ep"]); final_obj = parse_json(final or "")
    obj = parse_json(text)
    has_all_keys = isinstance(obj, dict) and all(k in obj for k in keys)
    stated = [v for v in values if holds(text, v)]
    if has_all_keys:
        cat = "full"
    elif obj is not None or stated:
        cat = "partial"
    else:
        cat = "none"
    if cat == "full":
        same = obj == final_obj
        detail = "identical JSON object to the final answer" if same else "valid JSON with all keys but differs from the final answer"
    elif cat == "partial":
        in_final = all(holds(final or "", v) for v in stated)
        detail = f"{len(stated)}/{len(values)} answer values stated in " + ("a JSON object missing keys" if obj is not None else "prose or bullets (no JSON object)") + "; every stated value " + ("appears" if in_final else "does NOT all appear") + " in the final answer"
    else:
        detail = "no answer value in the text"
    out.append(dict(arm=r["arm"], ep=r["ep"], k=r["k"], line=r["line"], dist=r["dist"], cat=cat, detail=detail, n_values=len(values), n_stated=len(stated),
                    is_json=obj is not None, quote=re.sub(r"\s+", " ", text.strip())[:110]))

def n(cat): return sum(o["cat"] == cat for o in out)
d1 = [o for o in out if o["dist"] == 1]
lines = ["# REPEAT_TEXT_CHECK: do the 18 'claimed done' repeats already contain the final answer? (design input; read-only; saved traces only)\n",
 "Population: the 18 Qwen repeats from `REPEATS_READING.md` whose repeating request carried model text that states the answer or says it is compiling it (6 in A1, 12 in A2; same regex as there, `claimed done`). Nothing was run; sources: the saved traces and `repeats_rows.json`. Script: `repeat_text_check.py`.\n",
 "Definitions (fixed before looking at the result): **full valid answer** = the text contains a JSON object (fenced or bare) that parses and has every key of the task's required answer; **partial** = the text states some or all of the answer values but not as such a complete JSON object (prose or bullets, or a JSON object with keys missing); **no answer** = no expected answer value in the text. 'Equals the later answer' is checked against the episode's final answer: identical parsed JSON for full answers, and, for partial ones, whether every stated value also appears in the final answer. The text is the model text in the same request that issued the repeated call.\n",
 "## Counts (18)\n", "| category | count |", "|---|---:|",
 f"| full valid answer (complete JSON) | {n('full')} |", f"| partial | {n('partial')} |", f"| no answer | {n('none')} |",
 f"\n**At distance 1:** {len(d1)} of 18. By category at distance 1: full {sum(o['cat'] == 'full' for o in d1)}, partial {sum(o['cat'] == 'partial' for o in d1)}, none {sum(o['cat'] == 'none' for o in d1)}.",
 f"\nWithin partial: all answer values stated {sum(o['cat'] == 'partial' and o['n_stated'] == o['n_values'] for o in out)}, some values stated {sum(o['cat'] == 'partial' and 0 < o['n_stated'] < o['n_values'] for o in out)}; of the partial ones, {sum(o['cat'] == 'partial' and o['is_json'] for o in out)} contain a JSON object (missing keys) and {sum(o['cat'] == 'partial' and not o['is_json'] for o in out)} are prose or bullets. Full answers identical to the final answer: {sum(o['cat'] == 'full' and o['detail'].startswith('identical') for o in out)} of {n('full')}.\n",
 "## Every item\n", "| arm | episode | req / line | dist | category | detail | start of the text |", "|---|---|---|---:|---|---|---|"]
for o in out:
    lines.append(f"| {o['arm']} | {o['ep']} | R{o['k']} / {o['line']} | {o['dist']} | {o['cat']} | {o['detail']} | {o['quote'].replace('|', '/')} |")
lines.append("\nLimits: the 18 are selected by a regex on the model text (my choice in `REPEATS_READING.md`); the repeats come from 24 episodes in near-duplicate pairs (temperature 0); string matching of answer values; this describes the saved text, not why the model issued the call.")
(HERE / "REPEAT_TEXT_CHECK.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines[4:14]))
