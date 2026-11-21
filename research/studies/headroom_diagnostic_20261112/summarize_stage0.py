"""Stage 0 tables from labeled_requests.csv (offline). Writes STAGE0_TABLES.md.

Usage: python3 summarize_stage0.py <study_dir>

Definitions (see PROTOCOL_STAGE0.md):
  floor_strict  lower bound on model requests under perfect batching and no guessed names
                (observation stages + 1 final answer).
  excess        actual requests - floor_strict, summed over episodes.
  headroom      (DEP + RED) / all labeled requests; first requests are unlabeled and excluded.
  adoption      share of requests with at least one tool call that emitted 2+ calls.
"""
import collections
import csv
import sys
from pathlib import Path

LABELS = ["JUDG", "DEP", "REC", "ORD", "RED", "FIN", "UNCLEAR"]


def group_key(row):
    return (row["corpus"], row["model"], row["arm"])


def truthy(value):
    return value == "True"


def episode_table(rows):
    """One record per episode: actual requests, floor, support."""
    episodes = {}
    for row in rows:
        episode = episodes.setdefault(row["episode"], {
            "group": group_key(row), "task": row["task"], "actual": 0,
            "floor": int(row["floor_strict"]), "floor_alt": int(row["floor_alt"]),
            "supported": truthy(row["supported_complete"]), "prompt": row["batching_prompt"],
            "in": 0, "out": 0, "seconds": 0.0})
        episode["actual"] += 1
        episode["in"] += int(float(row["input_tokens"] or 0))
        episode["out"] += int(float(row["output_tokens"] or 0))
        episode["seconds"] += float(row["seconds"] or 0)
    return episodes


def main():
    study = Path(sys.argv[1])
    rows = list(csv.DictReader(open(study / "labeled_requests.csv")))
    episodes = episode_table(rows)
    groups = sorted({e["group"] for e in episodes.values()})
    out = []

    out.append("## Table 1. Requests, floor and excess (per corpus / model / arm)\n")
    out.append("`sup.` = episodes judged supported-complete by the earlier studies (reported, not re-scored here). "
               "Excess is shown for all episodes and for supported-complete episodes only; "
               "episodes below their floor are counted separately because the floor then does not describe a complete answer.\n")
    out.append("| corpus | model | arm | prompt | eps | sup. | requests | floor | excess | excess % | sup. requests | sup. floor | sup. excess | sup. excess % | alt-floor excess (sup.) | eps below floor |")
    out.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    totals = collections.Counter()
    for g in groups:
        eps = [e for e in episodes.values() if e["group"] == g]
        sup = [e for e in eps if e["supported"]]
        a, f = sum(e["actual"] for e in eps), sum(e["floor"] for e in eps)
        sa, sf = sum(e["actual"] for e in sup), sum(e["floor"] for e in sup)
        saf = sum(e["floor_alt"] for e in sup)
        below = sum(1 for e in eps if e["actual"] < e["floor"])
        pct = lambda x, y: f"{100 * x / y:.0f}%" if y else "n/a"
        out.append(f"| {g[0]} | {g[1]} | {g[2]} | {eps[0]['prompt']} | {len(eps)} | {len(sup)} | {a} | {f} | {a - f} | {pct(a - f, f)} | "
                   f"{sa} | {sf} | {sa - sf} | {pct(sa - sf, sf)} | {sa - saf} | {below} |")
        totals["eps"] += len(eps); totals["sup"] += len(sup); totals["a"] += a; totals["f"] += f
        totals["sa"] += sa; totals["sf"] += sf
    out.append(f"| **all** | | | | {totals['eps']} | {totals['sup']} | {totals['a']} | {totals['f']} | {totals['a'] - totals['f']} | "
               f"{100 * (totals['a'] - totals['f']) / totals['f']:.0f}% | {totals['sa']} | {totals['sf']} | {totals['sa'] - totals['sf']} | "
               f"{100 * (totals['sa'] - totals['sf']) / totals['sf']:.0f}% | | |")

    out.append("\n## Table 2. Reason labels (all requests after the first) and headroom\n")
    out.append("Headroom = (DEP + RED) / labeled requests. 'DEP batch.' = DEP requests whose arguments were available at least one request earlier. "
               "'designed REC' = recovery from the planted missing node in `d1_recovery` (inside the floor).\n")
    out.append("| corpus | model | arm | labeled | " + " | ".join(LABELS) + " | headroom | DEP batch. | designed REC | own-call errors | headroom (supported eps) |")
    out.append("|---|---|---|---:|" + "---:|" * len(LABELS) + "---:|---:|---:|---:|---:|")
    for g in groups:
        sel = [r for r in rows if group_key(r) == g and r["request_index"] != "1"]
        c = collections.Counter(r["label"] for r in sel)
        sup = [r for r in sel if truthy(r["supported_complete"])]
        csup = collections.Counter(r["label"] for r in sup)
        hr = (c["DEP"] + c["RED"]) / len(sel)
        hrs = ((csup["DEP"] + csup["RED"]) / len(sup)) if sup else float("nan")
        dep_b = sum(1 for r in sel if r["label"] == "DEP" and truthy(r["batchable"]))
        designed = sum(1 for r in sel if truthy(r["designed_recovery"]))
        errs = sum(1 for r in sel if truthy(r["own_call_error"]))
        out.append(f"| {g[0]} | {g[1]} | {g[2]} | {len(sel)} | " + " | ".join(str(c[l]) for l in LABELS) +
                   f" | {100 * hr:.0f}% | {dep_b} | {designed} | {errs} | " + (f"{100 * hrs:.0f}%" if sup else "n/a") + " |")
    sel = [r for r in rows if r["request_index"] != "1"]
    c = collections.Counter(r["label"] for r in sel)
    out.append(f"| **all** | | | {len(sel)} | " + " | ".join(str(c[l]) for l in LABELS) +
               f" | {100 * (c['DEP'] + c['RED']) / len(sel):.0f}% | | | | |")
    # Same, with FIN removed, since FIN is never avoidable.
    nofin = [r for r in sel if r["label"] != "FIN"]
    cn = collections.Counter(r["label"] for r in nofin)
    out.append(f"\nExcluding FIN (never avoidable): {len(nofin)} non-final requests; "
               f"(DEP+RED)/non-final = {100 * (cn['DEP'] + cn['RED']) / len(nofin):.0f}%.\n")

    out.append("## Table 3. Batching adoption\n")
    out.append("`multi` = requests that emitted 2+ calls. `missed` = single-call requests flagged batchable (every argument was available at least one "
               "request earlier, so a perfect batcher would have merged them). Adoption among opportunities = multi / (multi + missed). "
               "Baseline arms still carry the original 'never call multiple tools / do not batch' text in every arm; narration and coverage arms do not.\n")
    out.append("| corpus | model | arm | prompt | requests with calls | multi | missed | adoption among opportunities | eps with a multi-call request | `batch_reads` calls |")
    out.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|")
    for g in groups:
        sel = [r for r in rows if group_key(r) == g and int(r["n_calls"]) > 0]
        multi = [r for r in sel if int(r["n_calls"]) > 1]
        eps_multi = len({r["episode"] for r in multi})
        eps = len({r["episode"] for r in rows if group_key(r) == g})
        missed = sum(1 for r in sel if int(r["n_calls"]) == 1 and truthy(r["batchable"]))
        batch_reads = sum(r["calls"].count("batch_reads(") for r in sel)
        denominator = len(multi) + missed
        out.append(f"| {g[0]} | {g[1]} | {g[2]} | {sel[0]['batching_prompt']} | {len(sel)} | {len(multi)} | {missed} | "
                   f"{100 * len(multi) / denominator:.0f}% | {eps_multi}/{eps} | {batch_reads} |")

    out.append("\n## Table 4. Cost of all requests (descriptive)\n")
    out.append("| corpus | model | arm | requests | input tokens | output tokens | model seconds |")
    out.append("|---|---|---|---:|---:|---:|---:|")
    for g in groups:
        eps = [e for e in episodes.values() if e["group"] == g]
        out.append(f"| {g[0]} | {g[1]} | {g[2]} | {sum(e['actual'] for e in eps)} | {sum(e['in'] for e in eps):,} | "
                   f"{sum(e['out'] for e in eps):,} | {sum(e['seconds'] for e in eps):.0f} |")

    out.append("\n## Table 5. Ten most expensive avoidable requests (supported-complete episodes only)\n")
    out.append("Avoidable = RED, or DEP whose arguments were available at least one request earlier (batchable). Ranked by the input tokens the "
               "model re-read for that request (a proxy for what a merge or deletion would save). `trace:line` is the `model_end` line.\n")
    scored = []
    for r in rows:
        if r["request_index"] == "1" or not truthy(r["supported_complete"]):
            continue
        if r["label"] == "RED" or (r["label"] == "DEP" and truthy(r["batchable"])):
            scored.append((int(float(r["input_tokens"] or 0)), r))
    scored.sort(key=lambda t: -t[0])
    out.append("| # | episode | request | label | input tokens | trace:line | calls |")
    out.append("|---:|---|---:|---|---:|---|---|")
    for rank, (tokens, r) in enumerate(scored[:10], 1):
        trace = r["trace_file"].replace("research/_artifacts/autotool_iteration_20261112/", "")
        out.append(f"| {rank} | {r['episode']} ({r['arm']}) | {r['request_index']}/{r['n_requests_episode']} | {r['label']} | {tokens:,} | {trace}:{r['trace_line']} | {r['calls'][:90]} |")
    total_tokens = sum(t for t, _ in scored)
    out.append(f"\n{len(scored)} requests in supported-complete episodes are RED or batchable DEP ({total_tokens:,} input tokens).")

    out.append("\n## Table 6. What the avoidable requests are (all episodes)\n")
    out.append("| mechanism | requests |")
    out.append("|---|---:|")
    def mechanism(r):
        if r["label"] == "RED":
            if "set_debugging" in r["calls"]:
                return "RED: no-information tool (set_debugging)"
            if "param_list" in r["calls"] and "unneeded" in r["label_reason"]:
                return "RED: param_list although the parameter name is in the task"
            if "subset" in r["label_reason"] or "already obtained" in r["label_reason"]:
                return "RED: exact or subset repeat of an earlier successful read"
            return "RED: other"
        if r["label"] == "DEP" and truthy(r["batchable"]):
            return "DEP batchable: independent call serialised (" + r["calls"].split("(")[0] + ")"
        if r["label"] == "DEP" and truthy(r["own_call_error"]):
            return "DEP: failed call with mechanically assemblable full name"
        return None
    counts = collections.Counter(m for m in (mechanism(r) for r in rows if r["request_index"] != "1") if m)
    for name, n in counts.most_common():
        out.append(f"| {name} | {n} |")
    rec_unplanned = sum(1 for r in rows if r["label"] == "REC" and not truthy(r["designed_recovery"]))
    out.append(f"| (not in headroom) REC unplanned, after an own-call error | {rec_unplanned} |")

    out.append("\n## Table 7. Per task: actual vs floor (supported-complete episodes)\n")
    out.append("| task | floor (strict / alt) | supported eps | mean requests | min | max |")
    out.append("|---|---|---:|---:|---:|---:|")
    for task in sorted({e["task"] for e in episodes.values()}):
        eps = [e for e in episodes.values() if e["task"] == task and e["supported"]]
        if not eps:
            continue
        c_ = [e["actual"] for e in eps]
        out.append(f"| {task} | {eps[0]['floor']} / {eps[0]['floor_alt']} | {len(eps)} | {sum(c_) / len(c_):.1f} | {min(c_)} | {max(c_)} |")

    (study / "STAGE0_TABLES.md").write_text("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
