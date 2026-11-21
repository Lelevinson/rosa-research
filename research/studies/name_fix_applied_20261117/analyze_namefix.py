"""Analysis and audit of the name-fix applied test (design section 'Dual scoring' and 'Decision bars'). uv run python analyze_namefix.py -> TABLES.md, results.json, AUDIT.md
The audit re-derives, from the saved traces and the fixture graph (not from the rewriter's ledger), for every changed answer: where the submitted answer differs from the original, whether each changed field equals the
required identity, whether the short form was a unique suffix in the full graph, whether the evidence (successful tool results of the trace) shows the identity, and every strict score change."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import namefix_fixture as fixture  # noqa: E402
import namefix_scoring as scoring  # noqa: E402

MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
TASKS = {t["id"]: t for t in fixture.TASKS}
NAMES = scoring.graph_names(fixture.GRAPH)


def diff_paths(a, b, path=""):
    """Paths where two answer objects differ (keys renamed count as a difference of the object)."""
    if isinstance(a, dict) and isinstance(b, dict):
        if list(a) != list(b):
            return [f"{path}.keys {list(a)} -> {list(b)}"]
        return [p for k in a for p in diff_paths(a[k], b[k], f"{path}.{k}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in diff_paths(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: {a!r} -> {b!r}"]


def evidence_names(row):
    """(contiguous, joined): full names that appear as a contiguous string in a successful tool result of the trace, and full names that exist only as the join of the
    `Node name:` and `Node namespace:` fields of one endpoint block (ledger rule of answer_gate.names_in_text; see LEDGER_DEFINITION.md). This check mirrors the ledger's join, so it is NOT independent of it."""
    contiguous, joined = set(), set()
    for line in (REPO / row["trace_path"]).read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "tool_end":
            text = str(e.get("output")).replace("\\n", "\n")
            if "Unable to find" in text or text.startswith("Invalid"):
                continue
            contiguous |= set(re.findall(r"(?<![\w/.:-])/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+", text))
            joined |= {f"{ns.rstrip('/')}/{name}" for name, ns in re.findall(r"Node name:\s*(\S+)\s+Node namespace:\s*(\S+)", text)}
    return contiguous, joined - contiguous


def summarize(rs):
    return dict(episodes=len(rs), answers_emitted=sum(r["answer_emitted"] for r in rs), no_answer=sum(not r["answer_emitted"] for r in rs), aborts=sum(bool([a for a in r["aborts"] if a != "iteration limit"]) for r in rs),
                rewritten_episodes=sum(r["rewritten"] for r in rs), rewrite_events=sum(r["rule_event_counts"]["rewrite"] for r in rs), ambiguous=sum(r["rule_event_counts"]["reject_ambiguous"] for r in rs),
                never_seen=sum(r["rule_event_counts"]["reject_never_seen"] for r in rs), collisions=sum(r["rule_event_counts"]["collision"] for r in rs),
                strict=dict(Counter(f"{'S' if r['strict_original'] else 'U'}->{'S' if r['strict_applied'] else 'U'}" for r in rs)), lenient=dict(Counter(f"{'S' if r['lenient_original'] else 'U'}->{'S' if r['lenient_applied'] else 'U'}" for r in rs)),
                strict_original=sum(r["strict_original"] for r in rs), strict_applied=sum(r["strict_applied"] for r in rs), lenient_original=sum(r["lenient_original"] for r in rs), lenient_applied=sum(r["lenient_applied"] for r in rs),
                requests=sum(r["llm_requests"] for r in rs), tokens=sum(r["input_tokens"] + r["output_tokens"] for r in rs), rewrite_cpu_seconds=sum(r["rewrite_cpu_seconds"] for r in rs))


def main():
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    excluded = set(json.loads((HERE / "INFRA_EXCLUDED.json").read_text())["run_ids"]) if (HERE / "INFRA_EXCLUDED.json").exists() else set()
    data = [r for r in rows if r["phase"] == "full" and r["run_id"] not in excluded]
    res = dict(total=summarize(data), per_model={m: summarize([r for r in data if r["model"] == m]) for m in MODELS}, per_task={t: summarize([r for r in data if r["task"] == t]) for t in TASKS},
               per_template={t: summarize([r for r in data if r["template"] == t]) for t in sorted({r["template"] for r in data})})
    changed = [r for r in data if r["answer_original"] != r["answer_submitted"]]
    harms = [r for r in data if r["strict_original"] and not r["strict_applied"]]
    rewritten_supported = [r for r in changed if r["strict_original"]]
    audit = []
    for r in changed:
        task = TASKS[r["task"]]
        differences = diff_paths(r["answer_original"], r["answer_submitted"])
        contiguous, joined_only = evidence_names(r)
        checks = []
        for e in r["rule_events"]:
            if e["kind"] != "rewrite":
                continue
            new, old = e["new"], e["old"]
            kind = scoring.kind_of(new, NAMES)
            unique_in_graph = [n for n in NAMES.get(kind, []) if n.endswith("/" + old.lstrip("/"))] == [new]
            required_here = new in json.dumps(task["answer"])
            checks.append(dict(old=old, new=new, kind=kind, unique_suffix_in_full_graph=unique_in_graph, is_required_identity=required_here, contiguous_in_a_tool_result=new in contiguous,
                           only_joined_from_name_and_namespace_fields=new in joined_only))
        audit.append(dict(run_id=r["run_id"], task=r["task"], model=r["model"], seed=r["seed"], original=r["answer_original"], submitted=r["answer_submitted"], truth=task["answer"], differences=differences,
                          strict=f"{'S' if r['strict_original'] else 'U'}->{'S' if r['strict_applied'] else 'U'}", lenient=f"{'S' if r['lenient_original'] else 'U'}->{'S' if r['lenient_applied'] else 'U'}",
                          support_missing_applied=r["support_missing_applied"], issues_original=r["issues_original"], issues_applied=r["issues_applied"], checks=checks,
                          all_rewrites_verified=all(c["unique_suffix_in_full_graph"] and c["is_required_identity"] and (c["contiguous_in_a_tool_result"] or c["only_joined_from_name_and_namespace_fields"]) for c in checks) and not r["support_missing_applied"] and not r["issues_applied"]))
    unsupported = [r for r in data if not r["strict_applied"]]
    exact_unchanged = [r for r in data if r["answer_original"] == r["answer_submitted"] and r["strict_original"]]
    res["audit"] = dict(changed_answers=len(changed), rewritten_originally_supported=len(rewritten_supported), harmful_rewrites=len(harms), strict_improvements=sum(a["strict"] == "U->S" for a in audit),
                        improvements_verified=sum(a["strict"] == "U->S" and a["all_rewrites_verified"] for a in audit), unchanged_supported_answers=len(exact_unchanged),
                        unsupported_after=[dict(run_id=r["run_id"], task=r["task"], model=r["model"], issues=r["issues_applied"], missing=r["support_missing_applied"], answer=r["answer_submitted"]) for r in unsupported],
                        collisions=res["total"]["collisions"], episodes_with_names_only_joined=sum(any(c["only_joined_from_name_and_namespace_fields"] for c in a["checks"]) for a in audit), episodes_with_all_names_contiguous=sum(all(c["contiguous_in_a_tool_result"] for c in a["checks"]) for a in audit), models_with_rewrite=sorted({a["model"] for a in audit}), templates_with_rewrite=sorted({TASKS[a["task"]]["template"] for a in audit}))
    a = res["audit"]
    res["bars"] = dict(safety_fail=bool(harms) or any(not x["all_rewrites_verified"] and x["strict"] != "U->S" for x in audit),
                       eligible=(not harms) and len(changed) >= 8 and len(a["models_with_rewrite"]) >= 2 and len(a["templates_with_rewrite"]) >= 2 and a["improvements_verified"] >= 2,
                       harm_rate="unavailable (0 originally supported answers were rewritten)" if not rewritten_supported else f"{len(harms)}/{len(rewritten_supported)}",
                       wrong_identity_rewrites=sum(not c["is_required_identity"] for x in audit for c in x["checks"]))
    (HERE / "results.json").write_text(json.dumps(res, indent=1, default=str))
    L = ["# Name-fix applied test: tables (generated by analyze_namefix.py)", "", "## Four cells for every planned episode (denominator 64)", "| | strict original | strict applied | lenient original | lenient applied | rewritten episodes | rewrite events | ambiguous | never seen | collisions | no answer | aborts |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key, s in [("all", res["total"])] + [(m, res["per_model"][m]) for m in MODELS] + [(t, res["per_task"][t]) for t in TASKS]:
        L.append(f"| {key} ({s['episodes']}) | {s['strict_original']} | {s['strict_applied']} | {s['lenient_original']} | {s['lenient_applied']} | {s['rewritten_episodes']} | {s['rewrite_events']} | {s['ambiguous']} | {s['never_seen']} | {s['collisions']} | {s['no_answer']} | {s['aborts']} |")
    L += ["", "Paired transitions (strict): " + json.dumps(res["total"]["strict"]) + "; (lenient): " + json.dumps(res["total"]["lenient"]), "", "## Audit", json.dumps(res["audit"], indent=1, default=str), "", "## Bars", json.dumps(res["bars"], indent=1)]
    (HERE / "TABLES.md").write_text("\n".join(L) + "\n")
    A = ["# Audit of every changed answer (against fixture truth and the trace evidence; generated by analyze_namefix.py)", ""]
    for x in audit:
        A += [f"## {x['task']} / {x['model']} / seed {x['seed']}: strict {x['strict']}, lenient {x['lenient']}, all rewrites verified: {x['all_rewrites_verified']}",
              f"- original: `{json.dumps(x['original'])}`", f"- submitted: `{json.dumps(x['submitted'])}`", f"- truth: `{json.dumps(x['truth'])}`", f"- differences: {x['differences']}",
              f"- checks per rewrite (unique suffix in the full graph, equals the required identity, contiguous in a tool result or only joined from the Node name + Node namespace fields): {json.dumps(x['checks'])}", f"- strict issues original: {x['issues_original']}; after: {x['issues_applied']}; support missing after: {x['support_missing_applied']}", ""]
    A += ["## Unsupported after the fix (strict)"] + [f"- {u['run_id']}: issues {u['issues']}, missing {u['missing']}, answer `{json.dumps(u['answer'])}`" for u in res["audit"]["unsupported_after"]]
    (HERE / "AUDIT.md").write_text("\n".join(A) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
