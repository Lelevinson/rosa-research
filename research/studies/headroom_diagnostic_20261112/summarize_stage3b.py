"""Stage 3b tables and frozen decision rules (writes STAGE3B_TABLES.md). Offline.
usage: summarize_stage3b.py <study_dir> <a1_run_dir> <a0_run_dir>   (scores_3.json and labels_3.json in both)
"""
import collections, json, statistics, sys
from pathlib import Path
study, a1run, a0run = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
def load(run):
    sc = [r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"]]
    lb = {e["episode"]: e for e in json.loads((run / "labels_3.json").read_text())}
    return sc, lb
A1, L1 = load(a1run); A0, L0 = load(a0run)
AVOID = {"RED", "REC", "LATE", "NOARG"}
name = {"ollama": "Qwen", "openai": "Luna"}
def stats(rows, prov, depth=None):
    eps = [r for r in rows if r["provider"] == prov and (depth is None or r["depth"] == depth)]
    sup = [r for r in eps if r["supported_complete"]]
    ex, fl = sum(r["excess"] for r in sup), sum(r["floor"] for r in sup)
    return dict(eps=len(eps), sup=len(sup), ex=ex, fl=fl, share=(100 * ex / fl if fl else float("nan")), reqs=sorted(r["requests"] for r in sup))
out = ["# Stage 3b tables (arm A1 vs the Stage 3 arm A0; supported-complete episodes; denominators stated)\n",
       "## Table 1. Per depth and model\n", "| model | depth | floor | A0 supported | A0 excess / floor sum | A0 share | A1 supported | A1 requests per supported episode | A1 excess / floor sum | A1 share |", "|---|---:|---:|---:|---|---:|---:|---|---|---:|"]
for prov in ("ollama", "openai"):
    for d in (2, 3, 4, None):
        a, b = stats(A0, prov, d), stats(A1, prov, d)
        lab = str(d) if d else "**all**"
        out.append(f"| {name[prov]} | {lab} | {d + 1 if d else ''} | {a['sup']}/{a['eps']} | {a['ex']} / {a['fl']} | {a['share']:.1f}% | {b['sup']}/{b['eps']} | {b['reqs'] if d else ''} | {b['ex']} / {b['fl']} | {b['share']:.1f}% |")
out += ["\n## Table 2. Per template (A1; A0 beside)\n", "| model | template | A0 excess / floor | A0 share | A1 supported | A1 excess / floor | A1 share |", "|---|---|---|---:|---:|---|---:|"]
for prov in ("ollama", "openai"):
    for tpl in ("upstream", "pointer", "hub", "service"):
        def t(rows):
            sup = [r for r in rows if r["provider"] == prov and r["template"] == tpl and r["supported_complete"]]
            ex, fl = sum(r["excess"] for r in sup), sum(r["floor"] for r in sup)
            return len(sup), ex, fl
        sa, ea, fa = t(A0); sb, eb, fb = t(A1)
        out.append(f"| {name[prov]} | {tpl} | {ea} / {fa} | {100 * ea / fa:.1f}% | {sb} | {eb} / {fb} | {100 * eb / fb:.1f}% |")
# paired
idx = lambda rows: {(r["task"], r["repeat"], r["provider"]): r for r in rows}
i0, i1 = idx(A0), idx(A1)
out += ["\n## Table 3. A0 versus A1 paired by task, repeat and model (pairs where both are supported-complete)\n", "| model | pairs | mean requests A0 - A1 | range | A1 fewer / equal / A1 more | supported-complete A0 -> A1 |", "|---|---:|---:|---|---|---|"]
for prov in ("ollama", "openai"):
    diffs = []
    for key, r0 in i0.items():
        if key[2] == prov and key in i1 and r0["supported_complete"] and i1[key]["supported_complete"]:
            diffs.append(r0["requests"] - i1[key]["requests"])
    s0 = sum(r["supported_complete"] for r in A0 if r["provider"] == prov); s1 = sum(r["supported_complete"] for r in A1 if r["provider"] == prov)
    out.append(f"| {name[prov]} | {len(diffs)} | {statistics.mean(diffs):.2f} | {min(diffs)} to {max(diffs)} | {sum(d > 0 for d in diffs)} / {sum(d == 0 for d in diffs)} / {sum(d < 0 for d in diffs)} | {s0} -> {s1} |")
# remaining excess by kind
def kinds(rows, lab):
    c = collections.Counter(); ex = 0
    for r in rows:
        if not r["supported_complete"] or r["excess"] <= 0: continue
        ex += r["excess"]
        ls = [l for k, l in lab[r["episode"]]["labels"] if l not in (None, "FIN")]
        for l in ls:
            if l not in ("NEEDED",): c[l] += 1
    return ex, c
out += ["\n## Table 4. Remaining excess by kind (supported episodes with excess > 0; label counts per request, not capped)\n", "| model | arm | excess requests | RED (repeats) | REC (recovery after short names) | LATE (late stage calls) | NOARG (extra calls, args in task) | EXPLORE | avoidable share (capped per episode) |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
avshare = {}
for prov in ("ollama", "openai"):
    for arm, rows, lab in (("A0", A0, L0), ("A1", A1, L1)):
        rr = [r for r in rows if r["provider"] == prov]
        ex, c = kinds(rr, lab)
        capped = 0
        for r in rr:
            if r["supported_complete"] and r["excess"] > 0:
                ls = [l for k, l in lab[r["episode"]]["labels"] if l not in (None, "FIN")]
                capped += min(sum(l in AVOID for l in ls), r["excess"])
        avshare[(prov, arm)] = 100 * capped / ex if ex else float("nan")
        out.append(f"| {name[prov]} | {arm} | {ex} | {c['RED']} | {c['REC']} | {c['LATE']} | {c['NOARG']} | {c['EXPLORE']} | {avshare[(prov, arm)]:.0f}% |")
# opening listing although entity named (non-service tasks)
def opening_listing(rows, lab, prov):
    n = hit = 0
    for r in rows:
        if r["provider"] != prov or not r["supported_complete"] or r["template"] == "service": continue
        n += 1
        first = lab[r["episode"]]["calls"][0]
        if any(t in first for t in ("node_list", "topic_list", "service_list")): hit += 1
    return hit, n
out += ["\n## Table 5. First request is a listing although the entity is named (non-service tasks, supported episodes)\n", "| model | A0 | A1 |", "|---|---|---|"]
for prov in ("ollama", "openai"):
    a, b = opening_listing(A0, L0, prov), opening_listing(A1, L1, prov)
    out.append(f"| {name[prov]} | {a[0]} / {a[1]} | {b[0]} / {b[1]} |")
# largest remaining excess
out += ["\n## Table 6. Largest excess episodes under A1 (trace lines are `model_end` lines)\n", "| model | episode | task | requests / floor | label sequence | trace |", "|---|---|---|---|---|---|"]
for prov in ("ollama", "openai"):
    for r in sorted([r for r in A1 if r["provider"] == prov and r["supported_complete"]], key=lambda r: -r["excess"])[:4]:
        e = L1[r["episode"]]
        out.append(f"| {name[prov]} | {r['episode']} | {r['task']} | {r['requests']} / {r['floor']} | " + " ".join(f"R{k}:{l}" for k, l in e["labels"] if l) + f" | {a1run.name}/{r['episode']}/trace.jsonl (lines {e['lines'][1]}..{e['lines'][-1]}) |")
out += ["\n## Failures read by hand (A1)\n"] + [f"- {r['episode']}: exact={r['exact']}, issues {r['issues'][:2]}, missing {r['support_missing'][:2]}, requests {r['requests']} / floor {r['floor']}." for r in A1 if not r["supported_complete"]]
out += ["\n## Costs and behaviour (all 48 episodes per arm)\n", "| model | arm | requests | input tokens | native ops | native failures | seconds | multi-call requests |", "|---|---|---:|---:|---:|---:|---:|---:|"]
for prov in ("ollama", "openai"):
    for arm, rows in (("A0", A0), ("A1", A1)):
        rr = [r for r in rows if r["provider"] == prov]
        out.append(f"| {name[prov]} | {arm} | {sum(r['requests'] for r in rr)} | {sum(r['input_tokens'] for r in rr):,} | {sum(r['native_ops'] for r in rr)} | {sum(r['native_failures'] for r in rr)} | {sum(r['episode_seconds'] or 0 for r in rr):.0f} | {sum(r['multi_call_requests'] for r in rr)} |")
# frozen rules
q, l = stats(A1, "ollama"), stats(A1, "openai")
interp = lambda s: s["sup"] / s["eps"] >= 0.5 and s["sup"] >= 8
ok = interp(q) and interp(l)
if not ok: branch = "INCONCLUSIVE (a model is not interpretable)"
elif l["share"] < 15 and q["share"] < 25: branch = "ORDINARY CONTROL CLOSES IT"
elif l["share"] >= 25: branch = "ROOM REMAINS FOR LUNA"
elif l["share"] < 25 and q["share"] >= 40: branch = "WEAK-MODEL ROOM REMAINS"
else: branch = "INCONCLUSIVE"
loops = [r for r in A1 if r["provider"] == "ollama" and r["supported_complete"] and sum(1 for k, x in L1[r["episode"]]["labels"] if x == "RED") >= 10]
qs = [r for r in A1 if r["provider"] == "ollama" and r["supported_complete"] and r not in loops]
qsens = 100 * sum(r["excess"] for r in qs) / sum(r["floor"] for r in qs)
out += ["\n## Sensitivity (not part of the frozen rule)\n",
        f"- Qwen A1 with every episode that has 10 or more RED requests removed ({len(loops)} episode(s): {[r['episode'] for r in loops]}): {qsens:.1f}% ({sum(r['excess'] for r in qs)} / {sum(r['floor'] for r in qs)}).",
        f"- Luna A1 excess is {l['ex']} over a floor sum of {l['fl']}: one request more would give {100 * (l['ex'] + 1) / l['fl']:.1f}% (threshold for the closing rule 15%, for room 25%).",
        "\n## Frozen decision rules applied\n",
        f"- A0 (Stage 3): Luna {stats(A0, 'openai')['share']:.1f}% ({stats(A0, 'openai')['ex']}/{stats(A0, 'openai')['fl']}), Qwen {stats(A0, 'ollama')['share']:.1f}% ({stats(A0, 'ollama')['ex']}/{stats(A0, 'ollama')['fl']}).",
        f"- A1: supported-complete Qwen {q['sup']}/{q['eps']}, Luna {l['sup']}/{l['eps']}; both interpretable: {ok}. Mean excess share: Qwen {q['share']:.1f}% ({q['ex']}/{q['fl']}), Luna {l['share']:.1f}% ({l['ex']}/{l['fl']}).",
        f"- 1. closes (Luna < 15% and Qwen < 25%): {'yes' if (ok and l['share'] < 15 and q['share'] < 25) else 'no'}. 2. Luna >= 25%: {'yes' if l['share'] >= 25 else 'no'}. 3. Luna < 25% and Qwen >= 40%: {'yes' if (l['share'] < 25 and q['share'] >= 40) else 'no'}.",
        f"- **Branch: {branch}.**"]
(study / "STAGE3B_TABLES.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
