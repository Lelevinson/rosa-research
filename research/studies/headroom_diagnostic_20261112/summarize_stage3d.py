"""Stage 3d tables and the frozen decision rule (writes STAGE3D_TABLES.md). Offline.
usage: summarize_stage3d.py <a2_run_dir> <a1_run_dir>   (scores_3.json and labels_3.json in both)
"""
import collections, json, statistics, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
a2run, a1run = Path(sys.argv[1]), Path(sys.argv[2])

def load(run):
    sc = [r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"] and r["provider"] == "ollama"]
    lb = {e["episode"]: e for e in json.loads((run / "labels_3.json").read_text())}
    return sc, lb

A2, L2 = load(a2run); A1, L1 = load(a1run)
def stats(rows):
    sup = [r for r in rows if r["supported_complete"]]
    ex, fl = sum(r["excess"] for r in sup), sum(r["floor"] for r in sup)
    return dict(eps=len(rows), sup=len(sup), ex=ex, fl=fl, share=100 * ex / fl if fl else float("nan"))
s1, s2 = stats(A1), stats(A2)
out = ["# Stage 3d tables (arm A2 vs A1; Qwen only; supported-complete episodes; denominators stated)\n"]
if s2["sup"] < 22:
    branch = "rule 1: correctness first (fewer than 22 of 24 supported-complete); excess not interpretable; rule stops here"
elif s2["share"] < 25:
    branch = "rule 2: sentences close it"
elif s2["share"] >= 40:
    branch = "rule 3: a target exists"
else:
    branch = "rule 4: inconclusive"
out += ["## Headline\n",
        f"- A2 Qwen: supported-complete **{s2['sup']}/{s2['eps']}** (A1 {s1['sup']}/{s1['eps']}); excess over the floor on supported episodes **{s2['ex']}/{s2['fl']} = {s2['share']:.1f}%** (A1 {s1['ex']}/{s1['fl']} = {s1['share']:.1f}%).",
        f"- Frozen rule: **{branch}**.",
        "- The A2 share is computed over only the supported episodes and is descriptive here; with rule 1 firing it is not interpretable as a result for the sentences.\n",
        "## Table 1. Per depth\n", "| depth | floor | A1 supported | A1 excess / floor sum | A1 share | A2 supported | A2 excess / floor sum | A2 share |", "|---|---:|---:|---|---:|---:|---|---:|"]
for d in (2, 3, 4, None):
    a = stats([r for r in A1 if d is None or r["depth"] == d]); b = stats([r for r in A2 if d is None or r["depth"] == d])
    out.append(f"| {d if d else '**all**'} | {d + 1 if d else ''} | {a['sup']}/{a['eps']} | {a['ex']} / {a['fl']} | {a['share']:.1f}% | {b['sup']}/{b['eps']} | {b['ex']} / {b['fl']} | {b['share']:.1f}% |")
out += ["\n## Table 2. Per template\n", "| template | A1 supported | A1 excess / floor | A1 share | A2 supported | A2 excess / floor | A2 share |", "|---|---:|---|---:|---:|---|---:|"]
for t in ("upstream", "pointer", "hub", "service"):
    a = stats([r for r in A1 if r["template"] == t]); b = stats([r for r in A2 if r["template"] == t])
    out.append(f"| {t} | {a['sup']}/{a['eps']} | {a['ex']} / {a['fl']} | {a['share']:.1f}% | {b['sup']}/{b['eps']} | {b['ex']} / {b['fl']} | {b['share']:.1f}% |")
idx = lambda rows: {(r["task"], r["repeat"]): r for r in rows}
i1, i2 = idx(A1), idx(A2)
pairs = [(k, i1[k]["requests"], i2[k]["requests"]) for k in sorted(i2) if k in i1 and i1[k]["supported_complete"] and i2[k]["supported_complete"]]
diffs = [a - b for _, a, b in pairs]
out += ["\n## Table 3. A1 versus A2 paired by task and repeat (pairs where both arms are supported-complete)\n",
        f"Pairs: {len(pairs)}. Mean requests A1 - A2: {statistics.mean(diffs):.2f}; median {statistics.median(diffs)}; range {min(diffs)} to {max(diffs)}; A2 fewer in {sum(d > 0 for d in diffs)}, equal in {sum(d == 0 for d in diffs)}, A2 more in {sum(d < 0 for d in diffs)}.\n",
        "| task | repeat | A1 requests | A2 requests | A1 - A2 |", "|---|---:|---:|---:|---:|"]
for (task, rep), a, b in pairs:
    out.append(f"| {task} | {rep} | {a} | {b} | {a - b} |")
def kinds(rows, lab):
    c = collections.Counter(); n = 0
    for r in rows:
        if not r["supported_complete"] or r["excess"] <= 0:
            continue
        for k, l in lab[r["episode"]]["labels"]:
            if l not in (None, "FIN", "NEEDED"):
                c[l] += 1; n += 1
    return c, n
c1, n1 = kinds(A1, L1); c2, n2 = kinds(A2, L2)
same = [i1[k] for k, _, _ in pairs]
ex_same, fl_same = sum(r["excess"] for r in same), sum(r["floor"] for r in same)
ex_a2, fl_a2 = sum(i2[k]["excess"] for k, _, _ in pairs), sum(i2[k]["floor"] for k, _, _ in pairs)
out.append(f"\nSame 20 task-repeat cells (supported in both arms): A1 excess {ex_same}/{fl_same} = {100 * ex_same / fl_same:.1f}%, A2 {ex_a2}/{fl_a2} = {100 * ex_a2 / fl_a2:.1f}%. The four cells lost in A2 are v2 r0, v2 r1, p4 r0, p4 r1; A1 excess on those four cells was {sum(i1[k]['excess'] for k in i1 if k not in {x for x, _, _ in pairs})} over floor {sum(i1[k]['floor'] for k in i1 if k not in {x for x, _, _ in pairs})}.")
out += ["\n## Table 4. Request kinds in supported episodes with excess > 0 (labels per request, not capped; Stage 3 labeller)\n",
        "| arm | excess requests (capped, = excess) | RED | REC | LATE | NOARG | EXPLORE |", "|---|---:|---:|---:|---:|---:|---:|"]
for arm, rows, c in (("A1", A1, c1), ("A2", A2, c2)):
    out.append(f"| {arm} | {stats(rows)['ex']} | " + " | ".join(str(c[k]) for k in ("RED", "REC", "LATE", "NOARG", "EXPLORE")) + " |")
out.append("\n(A2 label total may differ from the capped excess sum because failed episodes are excluded and labels are not capped per episode.)")
# first requests: listing although entity named
out += ["\n## Table 5. Episodes not supported-complete in A2 (read by hand)\n", "| episode | task | requests | exact | issues | support missing | error |", "|---|---|---:|---|---|---|---|"]
for r in A2:
    if not r["supported_complete"]:
        out.append(f"| {r['episode']} | {r['task']} | {r['requests']} | {r['exact']} | {'; '.join(r['issues'])[:80]} | {'; '.join(r['support_missing'])[:80]} | {str(r['error'])[:70].replace(chr(10), ' ')} |")
out += ["\n## Table 6. Every A2 episode\n", "| episode | task | floor | requests | excess | supported-complete | calls per request |", "|---|---|---:|---:|---:|---|---|"]
for r in sorted(A2, key=lambda r: r["episode"]):
    out.append(f"| {r['episode']} | {r['task']} | {r['floor']} | {r['requests']} | {r['excess']} | {r['supported_complete']} | {r['calls_per_request']} |")
(HERE / "STAGE3D_TABLES.md").write_text("\n".join(out) + "\n")
print("\n".join(out[:30]))
