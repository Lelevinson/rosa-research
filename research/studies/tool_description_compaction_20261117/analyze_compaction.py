"""Analysis of the compaction test (PROTOCOL.md section 4 and 5). uv run python analyze_compaction.py -> TABLES.md, results.json, DISCORDANT_CELLS.json"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
ARMS = ["FULL", "COMPACT"]
REGEX_ERROR = re.compile(r"multiple repeat|nothing to repeat|bad escape|unterminated|unbalanced parenthesis|bad character range|missing \)", re.I)
GLOB = re.compile(r"(?<![.\])])[*?]")
LIST_TOOLS = ("ros2_node_list", "ros2_topic_list", "ros2_service_list")
tok = lambda r: r["input_tokens"] + r["output_tokens"]


def errors_of(row):
    ev = [json.loads(l) for l in (REPO / row["trace_path"]).read_text().splitlines()]
    starts = {e["run_id"]: e for e in ev if e["kind"] == "tool_start"}
    out = Counter()
    cells = []
    for e in ev:
        if e["kind"] == "tool_start" and e["name"] in LIST_TOOLS:
            try:
                args = eval(e["input"]) if isinstance(e["input"], str) else e["input"]
            except Exception:
                args = {}
            pattern = args.get("pattern")
            if isinstance(pattern, str) and GLOB.search(pattern):
                out["E1_glob_style_pattern"] += 1
        if e["kind"] == "tool_end":
            text = str(e.get("output"))
            if REGEX_ERROR.search(text):
                out["E1_regex_error"] += 1
            elif text.startswith("Invalid arguments") or (text.startswith("Tool ") and "failed" in text):
                out["E2_wrong_argument"] += 1
            elif "Unable to find" in text:
                out["E3_not_found"] += 1
    return out


def summarize(rs):
    n, sup = len(rs), sum(r["supported_complete"] for r in rs)
    req, inp, tokens = sum(r["llm_requests"] for r in rs), sum(r["input_tokens"] for r in rs), sum(tok(r) for r in rs)
    return dict(episodes=n, supported=sup, requests=req, input_tokens=inp, output_tokens=sum(r["output_tokens"] for r in rs), tokens=tokens, input_per_request=inp / req if req else None,
                requests_per_supported=req / sup if sup else None, tokens_per_supported=tokens / sup if sup else None, input_per_supported=inp / sup if sup else None,
                aborts=sum(bool([a for a in r["aborts"] if a != "iteration limit"]) for r in rs), no_answer=sum(r["answer"] is None for r in rs), cap_hits=sum("iteration limit" in r["aborts"] for r in rs),
                wall_seconds=sum(r["wall_seconds"] for r in rs))


def main():
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    excluded = set(json.loads((HERE / "INFRA_EXCLUDED.json").read_text())["run_ids"]) if (HERE / "INFRA_EXCLUDED.json").exists() else set()
    data = [r for r in rows if r["phase"] == "full" and r["run_id"] not in excluded]
    by = {a: {(r["task"], r["model"]): r for r in data if r["arm"] == a} for a in ARMS}
    res = dict(arms={a: dict(total=summarize(list(by[a].values())), per_model={m: summarize([r for r in by[a].values() if r["model"] == m]) for m in MODELS}) for a in ARMS})
    errors = {a: Counter() for a in ARMS}
    error_cells = {a: defaultdict(Counter) for a in ARMS}
    for a in ARMS:
        for c, r in by[a].items():
            e = errors_of(r)
            errors[a] += e
            if e:
                error_cells[a][f"{c[0]}|{c[1]}"] = e
    res["errors"] = {a: dict(errors[a]) for a in ARMS}
    res["error_cells"] = {a: {k: dict(v) for k, v in error_cells[a].items()} for a in ARMS}
    f, g = by["FULL"], by["COMPACT"]
    common = sorted(set(f) & set(g))
    pair = dict(cells=len(common), both=sum(f[c]["supported_complete"] and g[c]["supported_complete"] for c in common), full_only=sum(f[c]["supported_complete"] and not g[c]["supported_complete"] for c in common),
                compact_only=sum(g[c]["supported_complete"] and not f[c]["supported_complete"] for c in common), neither=sum(not f[c]["supported_complete"] and not g[c]["supported_complete"] for c in common))
    pair["compact_minus_full_supported"] = pair["compact_only"] - pair["full_only"]
    res["paired"] = pair
    sf, sg = res["arms"]["FULL"]["total"], res["arms"]["COMPACT"]["total"]
    e12 = lambda a: errors[a]["E1_regex_error"] + errors[a]["E1_glob_style_pattern"] + errors[a]["E2_wrong_argument"]
    drop = sf["supported"] - sg["supported"]
    res["bars"] = dict(primary="FAIL (drop beyond noise)" if drop >= 5 else ("no drop beyond noise" + (" (within noise but a loss: audit)" if drop >= 3 else "")),
                       supported_full=sf["supported"], supported_compact=sg["supported"], drop=drop,
                       input_per_request_change=(sg["input_per_request"] - sf["input_per_request"]) / sf["input_per_request"], input_per_supported_change=(sg["input_per_supported"] - sf["input_per_supported"]) / sf["input_per_supported"],
                       efficiency_b=((sg["input_per_request"] - sf["input_per_request"]) / sf["input_per_request"] <= -0.03 and (sg["input_per_supported"] - sf["input_per_supported"]) / sf["input_per_supported"] <= -0.03),
                       e12_full=e12("FULL"), e12_compact=e12("COMPACT"), error_flag=(e12("COMPACT") - e12("FULL") >= 3 and e12("COMPACT") >= 1.5 * max(1, e12("FULL"))))
    (HERE / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (HERE / "DISCORDANT_CELLS.json").write_text(json.dumps([dict(task=c[0], model=c[1], full=f[c]["supported_complete"], compact=g[c]["supported_complete"], full_trace=f[c]["trace_path"], compact_trace=g[c]["trace_path"])
                                                             for c in common if f[c]["supported_complete"] != g[c]["supported_complete"]], indent=1))
    L = ["# Compaction test tables (generated by analyze_compaction.py)", "", "## Per arm: tokens and requests first", "| arm | episodes | requests | tokens (in+out) | input | output | input per request | tokens per supported | requests per supported | supported /40 | aborts | no answer |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for a in ARMS:
        t = res["arms"][a]["total"]
        L.append(f"| {a} | {t['episodes']} | {t['requests']} | {t['tokens']:,} | {t['input_tokens']:,} | {t['output_tokens']:,} | {t['input_per_request']:,.0f} | {t['tokens_per_supported']:,.0f} | {t['requests_per_supported']:.2f} | {t['supported']} | {t['aborts']} | {t['no_answer']} |")
    L += ["", "## Per model: supported /10 (requests, input per request)", "| model | FULL | COMPACT |", "|---|---|---|"]
    for m in MODELS:
        L.append(f"| {m} | " + " | ".join(f"{res['arms'][a]['per_model'][m]['supported']}/10 ({res['arms'][a]['per_model'][m]['requests']}, {res['arms'][a]['per_model'][m]['input_per_request']:,.0f})" for a in ARMS) + " |")
    L += ["", f"## Paired: {pair}", "", "## Errors (E1 regex/glob, E2 wrong argument, E3 not found), counted from the traces", json.dumps(res["errors"]), "", "## Bars", json.dumps(res["bars"], indent=1)]
    (HERE / "TABLES.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
