"""Stage 3 tables and frozen decision rules (writes STAGE3_TABLES.md). Offline.
usage: summarize_stage3.py <study_dir> <run_dir>   (needs scores_3.json and labels_3.json in run_dir)
"""
import collections, json, sys
from pathlib import Path
study, run = Path(sys.argv[1]), Path(sys.argv[2])
scores = [r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status")]
labels = {e["episode"]: e for e in json.loads((run / "labels_3.json").read_text())}
main = [r for r in scores if not r["pilot"]]
pilot = [r for r in scores if r["pilot"]]
AVOID = {"RED", "REC", "LATE", "NOARG"}
out = ["# Stage 3 tables (arm A0; 48 main episodes; pilot reported separately)\n"]
name = {"ollama": "Qwen (qwen3.5:9b)", "openai": "Luna (gpt-6-luna)"}
summary = {}
for prov in ("ollama", "openai"):
    eps = [r for r in main if r["provider"] == prov]
    sup = [r for r in eps if r["supported_complete"]]
    sf = sum(r["floor"] for r in sup); se = sum(r["excess"] for r in sup)
    share = 100 * se / sf if sf else float("nan")
    # relabel split over supported episodes with excess > 0
    tot_ex = tot_av = tot_explore = 0
    for r in sup:
        if r["excess"] <= 0: continue
        labs = [l for k, l in labels[r["episode"]]["labels"] if l not in (None, "FIN")]
        av = sum(l in AVOID for l in labs); ex = sum(l == "EXPLORE" for l in labs)
        tot_ex += r["excess"]; tot_av += min(av, r["excess"]); tot_explore += min(ex, max(r["excess"] - min(av, r["excess"]), 0))
    summary[prov] = dict(eps=len(eps), sup=len(sup), rate=len(sup) / len(eps), floor=sf, excess=se, share=share, tot_ex=tot_ex, av=tot_av, explore=tot_explore)
out += ["## Table 1. Per depth and model (supported-complete episodes only; denominators stated)\n",
        "| model | depth | floor | episodes | supported-complete | requests per supported episode | excess (sum / floor sum) | excess share |", "|---|---:|---:|---:|---:|---|---|---:|"]
for prov in ("ollama", "openai"):
    for d in (2, 3, 4):
        eps = [r for r in main if r["provider"] == prov and r["depth"] == d]
        sup = [r for r in eps if r["supported_complete"]]
        ex = sum(r["excess"] for r in sup); fl = sum(r["floor"] for r in sup)
        out.append(f"| {name[prov]} | {d} | {d + 1} | {len(eps)} | {len(sup)} | {sorted(r['requests'] for r in sup)} | {ex} / {fl} | {100 * ex / fl:.1f}% |")
    s = summary[prov]
    out.append(f"| **{name[prov]} all** | | | {s['eps']} | {s['sup']} | | {s['excess']} / {s['floor']} | **{s['share']:.1f}%** |")
out += ["\n## Table 2. Per template and model (supported-complete)\n", "| model | template | episodes | supported | excess / floor sum | share |", "|---|---|---:|---:|---|---:|"]
for prov in ("ollama", "openai"):
    for tpl in ("upstream", "pointer", "hub", "service"):
        eps = [r for r in main if r["provider"] == prov and r["template"] == tpl]
        sup = [r for r in eps if r["supported_complete"]]
        ex = sum(r["excess"] for r in sup); fl = sum(r["floor"] for r in sup)
        out.append(f"| {name[prov]} | {tpl} | {len(eps)} | {len(sup)} | {ex} / {fl} | {100 * ex / fl:.1f}% |")
out += ["\n## Table 3. Relabelled excess (supported-complete episodes with excess > 0)\n",
        "Avoidable = RED + REC + LATE (stage already started, or stage-1 call issued after the first request) + NOARG (call outside the plan whose arguments are in the task text or absent). Per episode min(avoidable, excess) is used. Exploration = unneeded calls outside the plan whose arguments needed an earlier result (codebook JUDG); needed = the first request of each next dependency stage.\n",
        "| model | excess requests | avoidable (frozen definition) | share | exploration (extra) | share avoidable + exploration | mostly avoidable (>50%)? |", "|---|---:|---:|---:|---:|---:|---|"]
for prov in ("ollama", "openai"):
    s = summary[prov]
    a = 100 * s["av"] / s["tot_ex"] if s["tot_ex"] else float("nan"); b = 100 * (s["av"] + s["explore"]) / s["tot_ex"] if s["tot_ex"] else float("nan")
    out.append(f"| {name[prov]} | {s['tot_ex']} | {s['av']} | {a:.0f}% | {s['explore']} | {b:.0f}% | {'yes' if a > 50 else 'no'} |")
out += ["\n## Table 4. Largest excess episodes (trace lines are `model_end` lines)\n", "| model | episode | task | requests / floor | label sequence (requests 2..n) | trace file |", "|---|---|---|---|---|---|"]
for prov in ("ollama", "openai"):
    top = sorted([r for r in main if r["provider"] == prov and r["supported_complete"]], key=lambda r: -r["excess"])[:5]
    for r in top:
        e = labels[r["episode"]]
        seq = " ".join(f"R{k}:{l}" for k, l in e["labels"] if l)
        out.append(f"| {name[prov]} | {r['episode']} | {r['task']} | {r['requests']} / {r['floor']} | {seq} | {run.name}/{r['episode']}/trace.jsonl (lines {e['lines'][1]}..{e['lines'][-1]}) |")
out += ["\n## Table 5. Costs and behaviour (all main episodes)\n", "| model | requests | input tokens | output tokens | native ops | native failures | seconds | multi-call requests | capacity events |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
for prov in ("ollama", "openai"):
    eps = [r for r in main if r["provider"] == prov]
    cap = sum(len(r["length_events"]) + r["iteration_cap"] + r["timeout"] + r["model_errors"] for r in eps)
    out.append(f"| {name[prov]} | {sum(r['requests'] for r in eps)} | {sum(r['input_tokens'] for r in eps):,} | {sum(r['output_tokens'] for r in eps):,} | {sum(r['native_ops'] for r in eps)} | {sum(r['native_failures'] for r in eps)} | {sum(r['episode_seconds'] or 0 for r in eps):.0f} | {sum(r['multi_call_requests'] for r in eps)} | {cap} |")
out += ["\n## Failures read by hand\n"]
for r in main:
    if not r["supported_complete"]:
        out.append(f"- {r['episode']}: exact={r['exact']}, issues {r['issues'][:2]}, missing {r['support_missing'][:2]}, requests {r['requests']} / floor {r['floor']}.")
out += ["\n## Pilot (4 Qwen episodes, reported separately, not in the 48)\n"] + [f"- {r['episode']}: requests {r['requests']} / floor {r['floor']}, supported-complete {r['supported_complete']}" for r in pilot]
# sensitivity
q, l = summary["ollama"], summary["openai"]
v2 = [r for r in main if r["provider"] == "ollama" and r["task"] == "v2" and r["supported_complete"]]
q_wo = (q["excess"] - sum(r["excess"] for r in v2)) / (q["floor"] - sum(r["floor"] for r in v2)) * 100
unsup = [r for r in main if r["provider"] == "openai" and not r["supported_complete"]]
l_all = 100 * (l["excess"] + sum(r["excess"] for r in unsup)) / (l["floor"] + sum(r["floor"] for r in unsup))
out += ["\n## Sensitivity (not part of the frozen rule)\n",
        f"- Qwen without the two 15-repeat `v2` loop episodes (excess 16 each): {q_wo:.1f}% ({q['excess'] - sum(r['excess'] for r in v2)} / {q['floor'] - sum(r['floor'] for r in v2)}).",
        f"- Luna including its one failed episode (excess counted): {l_all:.1f}%.",
        f"- Luna excess is {l['excess']} over a floor sum of {l['floor']}: one request fewer would give {100 * (l['excess'] - 1) / l['floor']:.1f}% (threshold 25%); one more {100 * (l['excess'] + 1) / l['floor']:.1f}%."]
# frozen decision rules
def interpretable(s): return s["rate"] >= 0.5
def enough(s): return s["sup"] >= 8
avoid = {p: summary[p]["tot_ex"] and summary[p]["av"] / summary[p]["tot_ex"] > 0.5 for p in summary}
luna_ok, qwen_ok = interpretable(l) and enough(l), interpretable(q) and enough(q)
clause1 = luna_ok and l["share"] >= 25
clause2 = qwen_ok and luna_ok and q["share"] >= 40 and l["share"] < 25
threshold_models = [p for p, ok in (("openai", clause1), ("ollama", (q["share"] >= 25 and qwen_ok) if clause1 else clause2)) if ok]
room = (clause1 or clause2) and all(avoid[p] for p in (["openai"] if clause1 else ["ollama"]))
noroom = luna_ok and qwen_ok and q["share"] < 15 and l["share"] < 15
branch = "ROOM FOR A METHOD" if room else ("NO ROOM" if noroom else "INCONCLUSIVE")
out += ["\n## Frozen decision rules applied\n",
        f"- Supported-complete rates: Qwen {q['sup']}/{q['eps']} ({100 * q['rate']:.0f}%), Luna {l['sup']}/{l['eps']} ({100 * l['rate']:.0f}%); both interpretable (>= 50%) and >= 8 supported episodes: {luna_ok and qwen_ok}.",
        f"- Mean excess share: Qwen {q['share']:.1f}%, Luna {l['share']:.1f}%.",
        f"- Clause 1 (Luna >= 25%): {'met' if clause1 else 'not met'}; clause 2 (Qwen >= 40% while Luna < 25%): {'met' if clause2 else 'not met'}.",
        f"- Relabelled excess mostly avoidable (> 50%): Luna {'yes' if avoid['openai'] else 'no'} ({l['av']}/{l['tot_ex']}), Qwen {'yes' if avoid['ollama'] else 'no'} ({q['av']}/{q['tot_ex']}).",
        f"- No room (both < 15%): {'yes' if noroom else 'no'}.",
        f"- **Branch: {branch}.**"]
(study / "STAGE3_TABLES.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
