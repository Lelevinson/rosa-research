"""Measured-only: how often is a tool result used again more than 2 requests after it arrived (fresh FULL arm, 40 episodes)? CPU only, saved traces.
Definitions (fixed before the numbers were computed):
- A RESULT is the output of one tool call issued in request r. It is part of the prompt of every later request k > r (it 'arrives' at the end of request r).
  A trimming rule 'keep the 2 newest requests' results' would drop it from requests k >= r + 3: those are the 'trimmable' re-sends.
- ITEMS of a result: the full ROS names in it (answer-gate name rule), message/service type strings (`pkg/msg|srv/Type`), and for parameter results the value.
- A USE of the result in request k: an item of it appears in the arguments of a call of request k (names, types) or, for a parameter value, in the arguments of the final_answer call.
- LAST-COPY USE: a use in request k >= r+3 of an item that is not in the task text and not in any result issued in requests r+1 .. k-1 (so dropping the result would remove the last copy of that item).
- Result tokens: the new-content tokens of request r+1 (input_(r+1) - input_r, exact) minus the output tokens of request r (the assistant message), shared across that request's results in proportion to their characters (an ESTIMATE of the split, exact in the total).
uv run python result_reuse.py -> result_reuse.json, RESULT_REUSE.md"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
REPO = HERE.parents[2]
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E  # noqa: E402

ag = E.ag
tasks = E.load_tasks()
TYPE = re.compile(r"[A-Za-z0-9_]+/(?:msg|srv|action)/[A-Za-z0-9_]+")
VALUE = re.compile(r"(?:String|Integer|Double|Boolean) value is:\s*(.+)")
word = lambda item: re.compile(r"(?<![\w/])" + re.escape(item) + r"(?![\w/])")


def items_of(text):
    names = set(ag.names_in_text(text))
    types = set(TYPE.findall(text))
    values = {v.strip() for v in VALUE.findall(text.replace("\\n", "\n"))}
    return names | types, values


def main():
    log = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [r for r in log if r["phase"] == "full" and r["arm"] == "FULL"]
    totals = Counter()
    per_model = defaultdict(Counter)
    ages = Counter()
    for row in rows:
        ep = E.parse("round 2", row, tasks)
        requests = ep["requests"]
        n = len(requests)
        if n == 0:
            continue
        task_items, _ = items_of(ep["task_text"])
        # tokens per request r: new content that arrives with request r's results
        inputs = [q["input_tokens"] for q in requests]
        results = []  # dict(r, items, values, chars, tokens)
        for q in requests:
            r = q["index"]
            units = [u for u in q["units"] if u["tool"] != "final_answer"]
            if not units or r == n:
                continue
            delta = max(0, inputs[r] - inputs[r - 1] - q["output_tokens"])
            chars = [max(1, len(u["text"])) for u in units]
            for u, c in zip(units, chars):
                names, values = items_of(u["text"]) if u["ok"] else (set(), set())
                results.append(dict(r=r, items=names, values=values, chars=c, tokens=delta * c / sum(chars), ok=u["ok"]))
        args_text = {q["index"]: " ".join(json.dumps(u["args"], sort_keys=True) for u in q["units"]) for q in requests}
        final_args = {q["index"]: " ".join(json.dumps(u["args"], sort_keys=True) for u in q["units"] if u["tool"] == "final_answer") for q in requests}
        for res in results:
            r = res["r"]
            uses_late, last_copy_late, first_ages = False, False, []
            for k in range(r + 1, n + 1):
                used = {i for i in res["items"] if word(i).search(args_text[k])}
                val_used = {v for v in res["values"] if final_args[k] and re.search(r"(?<![\w.])" + re.escape(v) + r"(?![\w.])", final_args[k])}
                if used or val_used:
                    ages[min(k - r, 5)] += 1
                if k >= r + 3 and (used or val_used):
                    uses_late = True
                    newer = set()
                    for rr in results:
                        if r < rr["r"] < k:
                            newer |= rr["items"]
                    if any(i not in task_items and i not in newer for i in used) or val_used:
                        last_copy_late = True
            res["late_use"], res["last_copy_late_use"] = uses_late, last_copy_late
            # re-sends at age >= 3: requests k in [r+3, n]
            res["trimmable_requests"] = max(0, n - (r + 3) + 1)
        for res in results:
            for target in (totals, per_model[row["model"]]):
                target["results"] += 1
                target["result_tokens"] += res["tokens"]
                target["results_with_trimmable_resend"] += res["trimmable_requests"] > 0
                target["trimmable_resend_tokens"] += res["tokens"] * res["trimmable_requests"]
                if res["trimmable_requests"] > 0:
                    target["trimmable_results_with_late_use"] += res["late_use"]
                    target["trimmable_results_with_last_copy_use"] += res["last_copy_late_use"]
                    target["resend_tokens_of_results_without_late_use"] += res["tokens"] * res["trimmable_requests"] * (not res["late_use"])
                    target["resend_tokens_of_results_without_last_copy_use"] += res["tokens"] * res["trimmable_requests"] * (not res["last_copy_late_use"])
        for target in (totals, per_model[row["model"]]):
            target["episodes"] += 1
            target["requests"] += n
            target["input_tokens"] += sum(inputs)
    out = dict(all=dict(totals), per_model={m: dict(v) for m, v in per_model.items()}, use_ages_pairs=dict(ages))
    (HERE / "result_reuse.json").write_text(json.dumps(out, indent=1))
    L = ["# Tool-result reuse after the trimming point (fresh FULL arm; measured only; definitions in result_reuse.py)", "",
         "| group | episodes | requests | results | results re-sent at age >= 3 | of those: any later use | of those: last-copy use | input tokens | re-sent tokens of results at age >= 3 | of which results never used later | of which results never used as last copy |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key, t in [("all", totals)] + sorted(per_model.items()):
        L.append(f"| {key} | {t['episodes']} | {t['requests']} | {t['results']} | {t['results_with_trimmable_resend']} | {t['trimmable_results_with_late_use']} | {t['trimmable_results_with_last_copy_use']} | {t['input_tokens']:,} | "
                 f"{t['trimmable_resend_tokens']:,.0f} ({t['trimmable_resend_tokens'] / t['input_tokens']:.1%}) | {t['resend_tokens_of_results_without_late_use']:,.0f} | {t['resend_tokens_of_results_without_last_copy_use']:,.0f} |")
    L += ["", "Age of the request that uses an item of a result (r+1 = 1, r+2 = 2, ... capped at 5), counting every (result, request) use pair: " + json.dumps(dict(sorted(ages.items())))]
    (HERE / "RESULT_REUSE.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
