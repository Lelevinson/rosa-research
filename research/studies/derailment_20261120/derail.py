"""Derailment study (protocol: PROTOCOL.md, frozen; hashes in FREEZE.json). Offline: saved traces and result rows only.

  PYTHONDONTWRITEBYTECODE=1 nice uv run python research/studies/derailment_20261120/derail.py

Writes derail_rows.jsonl (one row per episode), results.json and handread_sample.json (the 10 derailment points to read by hand).
"""
import hashlib
import json
import random
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STUDIES = ROOT / "research/studies"
sys.path.insert(0, str(STUDIES / "loss_map_20261120"))
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import classify as C  # noqa: E402
import episodes as E  # noqa: E402
import answer_gate as ag  # noqa: E402

DERAIL_TYPES = ("format", "repeat", "name_guess")
WASTE = C.WASTE
ABSENT_AMB = {"e1h_abs_1", "e1h_abs_2", "nf_absent", "e1h_amb_1", "e1h_amb_2", "nf_amb_1", "nf_amb_2"}
CHANGE = {"e1h_chg_1", "e1h_chg_2"}
LONG = 3000
SPLIT = re.compile(r"Node name:\s*(\S+)\s*\n\s*Node namespace:\s*(\S+)")
NOT_FOUND = re.compile(r"Unable to find|Unknown (node|topic|service)|Node not found|not found|does not exist", re.I)
REGEX = re.compile(r"multiple repeat|nothing to repeat|bad escape|unterminated|re\.error")
VALIDATION = re.compile(r"^(Invalid arguments|final_answer needs|Answer not accepted)|is not available")
SEED = 20261120


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_freeze():
    f = json.loads((HERE / "FREEZE.json").read_text())
    assert sha(HERE / "PROTOCOL.md") == f["protocol_md_sha256"], "PROTOCOL.md changed after the freeze"
    assert sha(STUDIES / "loss_map_20261120/classify.py") == f["classify_py_sha256"]
    assert sha(STUDIES / "loss_map_20261120/labelled_lossmap.jsonl") == f["labelled_lossmap_sha256"]
    assert sha(ROOT / "research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl") == f["listval_results_log_sha256"]
    assert sha(STUDIES / "offline_replay_20261116/episodes.py") == f["episodes_py_sha256"]


def failed(call):
    return (not call["ok"]) or bool(call["harness_error"])


def error_class(call):
    out, text = call["output"], call["text"] if isinstance(call["text"], str) else ""
    if isinstance(out, dict) and "error" in out and not str(out["error"]).strip():
        return "empty"
    if NOT_FOUND.search(text):
        return "not-found"
    if REGEX.search(text):
        return "regex"
    if VALIDATION.search(text):
        return "validation"
    return "other"


def norm_error(call):
    text = call["text"] if isinstance(call["text"], str) else ""
    return call["tool"] + " | " + re.sub(r"/[\w/\-.]+", "<N>", text)[:110]


def text_of(call):
    return call["text"].replace("\\n", "\n") if isinstance(call.get("text"), str) else ""


def derail_strings(request):
    strings = []
    for c in request["calls"]:
        if c["tool"] == "final_answer":
            continue
        if c["entity"] is not None:
            strings.append(str(c["entity"]))
        else:
            strings.extend(v for v in c["args"].values() if isinstance(v, str) and len(v) >= 3)
    return strings


def categories(task, previous, derail_request, ledger_before_previous):
    """(primary, underlying, error class, error text, split flag) for a context = the previous request (None for the task-only context k=0) and the task."""
    errclass = errtext = None
    result_cat = None
    split = False
    if previous is not None:
        bad = [c for c in previous["calls"] if failed(c)]
        if bad:
            result_cat, errclass, errtext = 1, error_class(bad[0]), norm_error(bad[0])
        else:
            pairs = [m for c in previous["calls"] if c["tool"] != "final_answer" for m in SPLIT.findall(text_of(c))]
            if derail_request is not None and pairs:
                ents = [c["entity"] for c in derail_request["calls"] if c["entity"] is not None]
                for name_field, namespace_field in pairs:
                    for entity in ents:
                        if entity in (name_field, namespace_field) and not C.known(entity, ledger_before_previous):
                            split = True
            if split:
                result_cat = 2
            elif any(len(c["text"]) >= LONG for c in previous["calls"] if isinstance(c.get("text"), str)):
                result_cat = 3
    task_cat = 4 if task in ABSENT_AMB else 5 if task in CHANGE else None
    primary = result_cat or task_cat or 6
    underlying = result_cat or 6
    return primary, underlying, errclass, errtext, split


def analyse_episode(pop, row, lab, tasks):
    ep = E.parse(pop, dict(row, run_id=row["run_id"], arm=row["arm"]), tasks)
    types = lab["request_types"]
    reqs = ep["requests"]
    n = len(reqs)
    assert n == len(types), (row["run_id"], n, len(types))
    events, _ = E.ledger_events(ep)
    added = defaultdict(set)
    for index, _c, new in events:
        added[index] |= new
    ledger_after = {0: set(ag.names_in_text(ep["task_text"]))}
    for r in reqs:
        ledger_after[r["index"]] = ledger_after[r["index"] - 1] | added[r["index"]]
    D = next((i + 1 for i, t in enumerate(types) if t in DERAIL_TYPES), None)
    task = row["task"]

    def ctx(k, derail_idx):
        previous = reqs[k - 1] if k >= 1 else None
        dreq = reqs[derail_idx - 1] if derail_idx is not None else None
        return categories(task, previous, dreq, ledger_after[max(k - 1, 0)])

    # exposures: contexts before the first derailment (all contexts of a clean episode)
    exposures = []
    for k in range(0, n):
        if D is not None and k + 1 > D:
            break
        derails = D == k + 1
        primary, underlying, errclass, _t, _s = ctx(k, k + 1)
        exposures.append(dict(k=k, primary=primary, underlying=underlying, errclass=errclass, derails=derails))
    out = dict(run_id=row["run_id"], pop=pop, model=row["model"], task=task, seed=row["seed"], supported=lab["supported"], requests=n, floor=lab["floor"], excess=lab["excess"],
               failure=lab["failure"], trace_path=row["trace_path"], derailed=D is not None, derail_index=D, exposures=exposures)
    if D is not None:
        primary, underlying, errclass, errtext, split = ctx(D - 1, D)
        dreq = reqs[D - 1]
        prev_text = " ".join(text_of(c) for c in reqs[D - 2]["calls"] if c["tool"] != "final_answer") if D >= 2 else None
        strings = derail_strings(dreq)
        reuse = None if prev_text is None else any(s in prev_text for s in strings)
        waste_after = sum(t in WASTE for t in types[D - 1:])
        later = [i for i in range(D, n) if types[i] == "productive"]
        d = (later[0] + 1 - D) if later else None
        outcome = "never" if not lab["supported"] else ("quick" if d is not None and d <= 3 else "slow")
        out.update(derail_type=types[D - 1], category=primary, underlying=underlying, error_class=errclass, error_text=errtext, split=split, first_request=D == 1, reuse=reuse,
                   waste_after=waste_after, return_distance=d, outcome=outcome,
                   previous=None if D == 1 else [dict(tool=c["tool"], entity=c["entity"], args=c["args"], chars=len(c["text"]) if isinstance(c["text"], str) else None, failed=failed(c), text=text_of(c)[:160]) for c in reqs[D - 2]["calls"]],
                   derailing=[dict(tool=c["tool"], entity=c["entity"], args=c["args"], failed=failed(c), text=text_of(c)[:160]) for c in dreq["calls"]])
    return out


def pct(a, b):
    return round(100 * a / b, 1) if b else None


def summarise(rows):
    res = {}
    derailed = [r for r in rows if r["derailed"]]
    res["episodes"] = len(rows)
    res["derailed"] = len(derailed)
    res["clean"] = len(rows) - len(derailed)
    res["supported_derailed"] = sum(r["supported"] for r in derailed)
    res["supported_clean"] = sum(r["supported"] for r in rows if not r["derailed"])
    res["derail_type"] = dict(Counter(r["derail_type"] for r in derailed))
    res["first_request_derailments"] = sum(r["first_request"] for r in derailed)
    res["derail_index"] = dict(median=statistics.median(r["derail_index"] for r in derailed) if derailed else None, min=min((r["derail_index"] for r in derailed), default=None), max=max((r["derail_index"] for r in derailed), default=None))
    res["waste_after_total"] = sum(r["waste_after"] for r in derailed)
    res["excess_total_all_episodes"] = sum(r["excess"] for r in rows)
    for key in ("model", "task"):
        block = {}
        for g in sorted({r[key] for r in rows}):
            eps = [r for r in rows if r[key] == g]
            dd = [r for r in eps if r["derailed"]]
            block[g] = dict(episodes=len(eps), derailed=len(dd), clean=len(eps) - len(dd), unsupported=sum(not r["supported"] for r in eps), waste_after=sum(r["waste_after"] for r in dd),
                            median_index=statistics.median(r["derail_index"] for r in dd) if dd else None, categories=dict(Counter(r["category"] for r in dd)), outcomes=dict(Counter(r["outcome"] for r in dd)))
        res["by_" + key] = block
    for field in ("category", "underlying"):
        table = {}
        for cat in range(1, 7):
            eps = [r for r in derailed if r[field] == cat]
            row = dict(episodes=len(eps), waste_after=sum(r["waste_after"] for r in eps), mean_waste_after=round(statistics.mean(r["waste_after"] for r in eps), 2) if eps else None,
                       unsupported=sum(not r["supported"] for r in eps), outcomes=dict(Counter(r["outcome"] for r in eps)), models=dict(Counter(r["model"] for r in eps)), tasks=dict(Counter(r["task"] for r in eps)),
                       median_index=statistics.median(r["derail_index"] for r in eps) if eps else None, first_request=sum(r["first_request"] for r in eps), reuse=dict(Counter(str(r["reuse"]) for r in eps)),
                       supported_by_outcome={o: sum(r["supported"] for r in eps if r["outcome"] == o) for o in ("quick", "slow", "never")},
                       waste_by_outcome={o: sum(r["waste_after"] for r in eps if r["outcome"] == o) for o in ("quick", "slow", "never")},
                       derail_types=dict(Counter(r["derail_type"] for r in eps)), examples=[r["trace_path"] for r in sorted(eps, key=lambda r: -r["waste_after"])[:3]])
            table[cat] = row
        res["key_" + field] = table
    # category 1 error texts and classes
    errs = defaultdict(list)
    for r in derailed:
        if r["category"] == 1:
            errs[r["error_text"]].append(r)
    res["error_texts_top10"] = [dict(text=t, episodes=len(v), waste_after=sum(r["waste_after"] for r in v), mean=round(statistics.mean(r["waste_after"] for r in v), 2), never=sum(r["outcome"] == "never" for r in v),
                                     models=dict(Counter(r["model"] for r in v)), examples=[r["trace_path"] for r in sorted(v, key=lambda r: -r["waste_after"])[:3]])
                                for t, v in sorted(errs.items(), key=lambda kv: -sum(r["waste_after"] for r in kv[1]))[:10]]
    res["error_texts_all_count"] = len(errs)
    classes = defaultdict(list)
    for r in derailed:
        if r["category"] == 1:
            classes[r["error_class"]].append(r)
    res["error_classes"] = {c: dict(episodes=len(v), waste_after=sum(r["waste_after"] for r in v), never=sum(r["outcome"] == "never" for r in v)) for c, v in classes.items()}
    # rates
    exposures = defaultdict(lambda: dict(exposures=0, derails=0, in_clean=0, in_derailed=0))
    exposures_model = defaultdict(lambda: dict(exposures=0, derails=0))
    exposures_u = defaultdict(lambda: dict(exposures=0, derails=0))
    exposures_err = defaultdict(lambda: dict(exposures=0, derails=0))
    for r in rows:
        for x in r["exposures"]:
            for tbl, key in ((exposures, x["primary"]), (exposures_u, x["underlying"])):
                tbl[key]["exposures"] += 1
                tbl[key]["derails"] += x["derails"]
            exposures[x["primary"]]["in_clean" if not r["derailed"] else "in_derailed"] += 1
            exposures_model[(x["primary"], r["model"])]["exposures"] += 1
            exposures_model[(x["primary"], r["model"])]["derails"] += x["derails"]
            if x["errclass"]:
                exposures_err[x["errclass"]]["exposures"] += 1
                exposures_err[x["errclass"]]["derails"] += x["derails"]
    res["rates_primary"] = {c: dict(v, rate_pct=pct(v["derails"], v["exposures"])) for c, v in sorted(exposures.items())}
    res["rates_underlying"] = {c: dict(v, rate_pct=pct(v["derails"], v["exposures"])) for c, v in sorted(exposures_u.items())}
    res["rates_error_class"] = {c: dict(v, rate_pct=pct(v["derails"], v["exposures"])) for c, v in sorted(exposures_err.items())}
    res["rates_primary_by_model"] = {f"{c}|{m}": dict(v, rate_pct=pct(v["derails"], v["exposures"])) for (c, m), v in sorted(exposures_model.items())}
    return res


def main():
    check_freeze()
    tasks = C.all_tasks()
    labelled = {l["run_id"]: l for l in map(json.loads, (STUDIES / "loss_map_20261120/labelled_lossmap.jsonl").read_text().splitlines())}
    p1_rows = {r["run_id"]: r for r in C.load_rows("lossmap")}
    rows = []
    for rid, lab in labelled.items():
        rows.append(analyse_episode("P1", p1_rows[rid], lab, tasks))
    p3_rows, dropped = [], []
    for line in (ROOT / "research/_artifacts/exam/listval/RESULTS_LOG_all.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["arm"] == "FULL":
            p3_rows.append(r)
    labs = {l["run_id"]: l for l in C.analyse(p3_rows)}
    for r in p3_rows:
        try:
            rows.append(analyse_episode("P3", r, labs[r["run_id"]], tasks))
        except Exception as exc:  # report, never hide
            dropped.append((r["run_id"], repr(exc)))
    (HERE / "derail_rows.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    results = dict(dropped_p3=dropped, P1=summarise([r for r in rows if r["pop"] == "P1"]), P3=summarise([r for r in rows if r["pop"] == "P3"]), POOLED=summarise(rows))
    # pooled per-model key table (primary category x model x outcome)
    pm = {}
    for m in sorted({r["model"] for r in rows}):
        pm[m] = summarise([r for r in rows if r["model"] == m])["key_category"]
    results["pooled_key_by_model"] = pm
    # hand-reading sample
    rng = random.Random(SEED)
    models = sorted({r["model"] for r in rows})
    quota = dict(zip(models, (3, 3, 2, 2)))
    sample = []
    for m in models:
        pool = sorted((r for r in rows if r["derailed"] and r["model"] == m), key=lambda r: r["run_id"])
        sample += [r["run_id"] for r in rng.sample(pool, quota[m])]
    results["handread_sample"] = sample
    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=list))
    by_id = {r["run_id"]: r for r in rows}
    (HERE / "handread_sample.json").write_text(json.dumps([by_id[i] | {"exposures": None} for i in sample], indent=1))
    print(json.dumps({k: results[k] for k in ("dropped_p3",)}), {p: (results[p]["episodes"], results[p]["derailed"], results[p]["clean"]) for p in ("P1", "P3", "POOLED")})


if __name__ == "__main__":
    main()
