"""Aggregation of raw_P1.json / raw_P2.json (written by size_candidates.py) into results.json, detail files and bars (protocol sections 2-8).
Run after size_candidates.py:  PYTHONDONTWRITEBYTECODE=1 uv run python research/studies/idea_search_20261120/claude_lane/aggregate.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABELS = {json.loads(l)["run_id"]: json.loads(l) for l in (ROOT / "research/studies/loss_map_20261120/labelled_lossmap.jsonl").read_text().splitlines() if l.strip()}
MODELS = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]


def by(rows, key):
    out = Counter()
    for r in rows:
        out[r[key]] += 1
    return dict(out)


def key_of(e):
    return e["run_id"] + "|" + e["study"] + "|" + e["arm"]


def share(a, b):
    return round(100 * a / b, 2) if b else None


def per_model_task(rows, value=lambda r: 1):
    pm, pt = Counter(), Counter()
    for r in rows:
        pm[r["model"]] += value(r)
        pt[r["task"]] += value(r)
    return dict(pm), dict(sorted(pt.items()))


def candidate1(raw, name):
    episodes = {key_of(e): e for e in raw["episodes"]}
    total_requests = sum(e["requests"] for e in raw["episodes"])
    out = {}
    for variant in ("res", "task"):
        fires = raw["fires"][variant]
        truth = Counter(f["truth"] for f in fires)
        pm, pt = per_model_task(fires)
        # saved-max: union of the intervals (r, k] per episode
        saved = defaultdict(set)
        for f in fires:
            if f["later_request"]:
                saved[key_of(f)].update(range(f["request"] + 1, f["later_request"] + 1))
        saved_total = sum(len(v) for v in saved.values())
        saved_by_model = Counter()
        for k, v in saved.items():
            saved_by_model[episodes[k]["model"]] += len(v)
        distances = [f["later_request"] - f["request"] for f in fires if f["later_request"]]
        res = dict(fires=len(fires), episodes_with_fire=len({key_of(f) for f in fires}), by_model=pm, by_task=pt, truth=dict(truth), slash_only=sum(f["slash_only"] for f in fires),
                   joined_only=sum(f["joined_only"] for f in fires), differ=sum(f["differ"] for f in fires), absent_task_fires=sum(f["absent_task"] for f in fires),
                   no_later_use=sum(1 for f in fires if not f["later_request"]), saved_max=saved_total, saved_max_pct_of_requests=share(saved_total, total_requests), saved_by_model=dict(saved_by_model),
                   distance_median=sorted(distances)[len(distances) // 2] if distances else None, distance_mean=round(sum(distances) / len(distances), 2) if distances else None,
                   max_task_share_pct=share(max(pt.values()), len(fires)) if fires else None, unsupported_episode_fires=sum(1 for f in fires if not f["supported"]),
                   harm_cases=[f for f in fires if f["truth"] in ("wrong", "absent_made_present")])
        if name == "P1":
            guess_cov = rec_cov = other_saved = 0
            fire_requests = {(key_of(f), f["request"]) for f in fires}
            saved_pairs = {(k, r) for k, v in saved.items() for r in v}
            guess_total = rec_total = 0
            for e in raw["episodes"]:
                types = LABELS[e["run_id"]]["request_types"]
                for i, t in enumerate(types, start=1):
                    k = key_of(e)
                    if t == "name_guess":
                        guess_total += 1
                        guess_cov += (k, i) in fire_requests
                    if t == "name_recovery":
                        rec_total += 1
                        rec_cov += (k, i) in saved_pairs
            saved_typed = sum(1 for (k, i) in saved_pairs if LABELS[k.split("|")[0]]["request_types"][i - 1] in ("name_guess", "name_recovery"))
            res["coverage"] = dict(name_guess_total=guess_total, name_guess_fire_requests=guess_cov, name_recovery_total=rec_total, name_recovery_in_saved_set=rec_cov,
                                   saved_requests_typed_guess_or_recovery=saved_typed, of_218_pct=share(saved_typed, guess_total + rec_total))
            by_failure = Counter()
            for f in fires:
                lab = LABELS[f["run_id"]]
                if not lab["supported"]:
                    by_failure[lab["failure"]] += 1
            res["fires_in_unsupported_by_failure"] = dict(by_failure)
            res["fires_in_unsupported_episodes"] = len({key_of(f) for f in fires if not LABELS[f["run_id"]]["supported"]})
        res["saved_set"] = {k: sorted(v) for k, v in saved.items()} if variant == "res" else None
        out[variant] = res
    outs = [o for o in raw["out"] if o.get("applicable")]
    flips_down = [o for o in outs if o["old_supported"] and not o["new_supported"]]
    flips_up = [o for o in outs if not o["old_supported"] and o["new_supported"]]
    rewritten = [o for o in outs if o["changed"]]
    out["out_replay"] = dict(applicable=len(outs), not_applicable=len(raw["out"]) - len(outs), free_text_answers=sum(1 for o in outs if o["answer_source"] != "final_answer"), rewritten_episodes=len(rewritten),
                             rewrites=sum(len(o["rewrites"]) for o in rewritten), old_supported=sum(o["old_supported"] for o in outs), new_supported=sum(o["new_supported"] for o in outs),
                             supported_to_unsupported=len(flips_down), unsupported_to_supported=len(flips_up), down_cases=[{k: o[k] for k in ("run_id", "model", "task", "trace", "rewrites", "new_issues")} for o in flips_down],
                             up_cases=[{k: o[k] for k in ("run_id", "model", "task", "trace", "rewrites")} for o in flips_up],
                             rewritten_not_flipped=[{k: o[k] for k in ("run_id", "model", "task", "rewrites", "old_supported")} for o in rewritten if o["old_supported"] == o["new_supported"]][:12])
    if name == "P1":
        wrong = {k for k, v in LABELS.items() if v["failure"] == "wrong_conclusion_facts_present"}
        out["out_replay"]["wrong_conclusion_26"] = dict(total=len(wrong), flipped_to_supported=sorted(o["run_id"] for o in flips_up if o["run_id"] in wrong),
                                                         rewritten_but_still_unsupported=sorted(o["run_id"] for o in rewritten if o["run_id"] in wrong and not o["new_supported"]))
    return out


def candidate2(raw, name):
    total_requests = sum(e["requests"] for e in raw["episodes"])
    scans = [s for s in raw["scans"] if s["gate"]]
    pm, pt = per_model_task(scans, lambda s: 1)
    saved_pm, saved_pt = per_model_task(scans, lambda s: s["saved_max"])
    saved = sum(s["saved_max"] for s in scans)
    unsupported_eps = {k: e for k, e in ((key_of(e), e) for e in raw["episodes"]) if not e["supported"]}
    guesses = {v: [g for g in raw["guesses"] if g["variant"] == v] for v in ("frozen", "with_task_roles")}
    res = dict(scans=len(scans), scans_gated_out=len(raw["scans"]) - len(scans), scans_by_model=pm, scans_by_task=pt, requests_in_scans=sum(s["length"] for s in scans), saved_max=saved, saved_max_pct=share(saved, total_requests),
               saved_by_model=saved_pm, saved_by_task=saved_pt, scans_with_param_get=sum(s["has_param_get"] for s in scans), scans_node_info_only=sum(not s["has_param_get"] for s in scans),
               scans_in_unsupported=sum(1 for s in scans if key_of(s) in unsupported_eps), scan_length_distribution=dict(Counter(s["length"] for s in scans)),
               est_added_tokens_total=round(sum(s["est_added_tokens"] for s in scans), 1), est_added_tokens_mean=round(sum(s["est_added_tokens"] for s in scans) / len(scans), 1) if scans else None,
               saved_request_input_tokens=sum(s["saved_request_input_tokens"] for s in scans), models_with_scans=sorted({s["model"] for s in scans}), tasks_with_scans=sorted({s["task"] for s in scans}))
    clean = [s for s in scans if s["all_calls_ok"]]
    relation = [s for s in scans if "amb" not in s["task"]]
    res["post_hoc_splits"] = dict(label="added after the first look at the counts; descriptive only, no bar uses them",
                                  clean_scans_all_calls_ok=len(clean), clean_saved_max=sum(s["saved_max"] for s in clean), clean_by_task=dict(Counter(s["task"] for s in clean)),
                                  relation_tasks_scans=len(relation), relation_tasks_saved_max=sum(s["saved_max"] for s in relation), amb_value_filter_tasks_scans=len(scans) - len(relation),
                                  amb_value_filter_saved_max=saved - sum(s["saved_max"] for s in relation))
    for variant, rows in guesses.items():
        distinct = {(key_of(g), g["request"]) for g in rows}
        res[f"derived_guess_{variant}"] = dict(calls=len(rows), requests=len(distinct), episodes=len({key_of(g) for g in rows}), by_model=by(rows, "model"), by_task=dict(sorted(by(rows, "task").items())),
                                               in_unsupported=len({key_of(g) for g in rows if key_of(g) in unsupported_eps}))
    both = {key_of(s) for s in scans} | {key_of(g) for g in guesses["frozen"]}
    res["unsupported_with_scan_or_derived_guess"] = dict(episodes=len(both & set(unsupported_eps)), by_task=dict(Counter(unsupported_eps[k]["task"] for k in both & set(unsupported_eps))))
    res["examples"] = [dict(run_id=s["run_id"], task=s["task"], model=s["model"], requests=s["requests"], trace=s["trace"]) for s in scans[:8]]
    res["saved_set"] = {}
    for s in scans:
        res["saved_set"].setdefault(key_of(s), set()).update(s["in_scan_requests_saved"])
    res["saved_set"] = {k: sorted(v) for k, v in res["saved_set"].items()}
    return res


def candidate3(raw, name):
    total_requests = sum(e["requests"] for e in raw["episodes"])
    ep_by = {key_of(e): e for e in raw["episodes"]}
    lists = [(k, row) for k, c in raw["c3"].items() for row in c["list_rows"]]
    list_calls = len(lists)
    followed = [(k, r) for k, r in lists if r["followed_by_get"]]
    known = sum(1 for _k, r in followed if r["name_known_before"])
    saved_rows = [(k, r) for k, c in raw["c3"].items() for r in c["saved_requests"]]
    saved_by_model = Counter(ep_by[k]["model"] for k, _r in saved_rows)
    saved_by_task = Counter(ep_by[k]["task"] for k, _r in saved_rows)
    added_by_model, saved_tok_by_model, worse = Counter(), Counter(), 0
    for k, c in raw["c3"].items():
        added_by_model[ep_by[k]["model"]] += c["added_tokens_carried"]
        saved_tok_by_model[ep_by[k]["model"]] += c["saved_tokens"]
        worse += c["added_tokens_carried"] > c["saved_tokens"]
    added = sum(added_by_model.values())
    saved_tok = sum(saved_tok_by_model.values())
    list_by_model = Counter(ep_by[k]["model"] for k, _r in lists)
    over_cap = [(k, r) for k, r in lists if not r["under_cap"]]
    flagged = [(ep_by[k]["run_id"], ep_by[k]["trace"], r) for k, c in raw["c3"].items() for r in c["flagged_chg"]]
    saved_set = {k: sorted(c["saved_requests"]) for k, c in raw["c3"].items() if c["saved_requests"]}
    res = dict(list_calls=list_calls, list_calls_by_model=dict(list_by_model), followed_by_get=len(followed), followed_by_get_by_model=dict(Counter(ep_by[k]["model"] for k, _r in followed)),
               followed_with_name_known_before_list=known, over_cap=len(over_cap), over_cap_pct=share(len(over_cap), list_calls),
               chars_with_values_median=sorted(r["chars_with_values"] for _k, r in lists)[len(lists) // 2] if lists else None,
               added_chars_mean_under_cap=round(sum(r["added_chars"] for _k, r in lists if r["under_cap"]) / max(1, sum(1 for _k, r in lists if r["under_cap"])), 1),
               estimated_param_share_pct=share(sum(r["estimated_params"] for _k, r in lists), sum(r["params"] for _k, r in lists) or 1),
               saved_max=len(saved_rows), saved_max_pct=share(len(saved_rows), total_requests), saved_by_model=dict(saved_by_model), saved_by_task=dict(sorted(saved_by_task.items())),
               added_tokens_carried_total=round(added), saved_tokens_total=saved_tok, added_tokens_by_model={m: round(v) for m, v in added_by_model.items()}, saved_tokens_by_model=dict(saved_tok_by_model),
               episodes_added_exceeds_saved=worse, episodes_with_eligible_list=sum(1 for c in raw["c3"].values() if c["added_tokens_carried"] > 0), flagged_chg_saved=len(flagged),
               flagged_chg_examples=[dict(run_id=a, trace=b, request=c) for a, b, c in flagged[:5]])
    res["saved_set"] = saved_set
    return res


def candidate4(raw, name):
    total_requests = sum(e["requests"] for e in raw["episodes"])
    ep_by = {key_of(e): e for e in raw["episodes"]}
    out = {}
    for k in ("4", "5", "6"):
        trig = {key: v["per_k"][k] for key, v in raw["c4"].items() if v["per_k"].get(k)}
        rows = [(key, t) for key, t in trig.items()]
        harm = [(key, t) for key, t in rows if t["harm"]]
        chg = [(key, t) for key, t in rows if t["chg"]]
        chg_harm = [(key, t) for key, t in chg if t["missing"]]
        unsup = [(key, t) for key, t in rows if not t["supported"]]
        saved = sum(t["saved_max"] for _k, t in rows)
        saved_by_model, saved_by_task = Counter(), Counter()
        for key, t in rows:
            saved_by_model[ep_by[key]["model"]] += t["saved_max"]
            saved_by_task[ep_by[key]["task"]] += t["saved_max"]
        res = dict(episodes_with_trigger=len(rows), by_model=dict(Counter(ep_by[key]["model"] for key, _t in rows)), by_task=dict(sorted(Counter(ep_by[key]["task"] for key, _t in rows).items())),
                   ended_supported=sum(1 for _k, t in rows if t["supported"]), ended_unsupported=len(unsup), ended_capped=sum(1 for _k, t in rows if t["capped"]),
                   harm=len(harm), harm_by_model=dict(Counter(ep_by[key]["model"] for key, _t in harm)), harm_by_task=dict(Counter(ep_by[key]["task"] for key, _t in harm)),
                   harm_cases=[dict(run_id=ep_by[key]["run_id"], model=ep_by[key]["model"], task=ep_by[key]["task"], trace=ep_by[key]["trace"], trigger=t["trigger"], n=t["n"], missing=t["missing"][:3]) for key, t in harm],
                   unsupported_with_all_facts_at_trigger=sum(1 for _k, t in unsup if t["facts_present"]), unsupported_facts_missing_at_trigger=sum(1 for _k, t in unsup if not t["facts_present"]),
                   chg_triggers=len(chg), chg_harm=len(chg_harm), chg_harm_cases=[dict(run_id=ep_by[key]["run_id"], trace=ep_by[key]["trace"], trigger=t["trigger"], supported=t["supported"], missing=t["missing"][:2]) for key, t in chg_harm],
                   saved_max=saved, saved_max_pct=share(saved, total_requests), saved_loose=sum(t["saved_loose"] for _k, t in rows), saved_tokens=sum(t["saved_tokens"] for _k, t in rows),
                   saved_by_model=dict(saved_by_model), saved_by_task=dict(sorted(saved_by_task.items())),
                   capped_episodes_total=sum(1 for v in raw["c4"].values() if v["capped"]),
                   capped_with_trigger=[dict(run_id=ep_by[key]["run_id"], model=ep_by[key]["model"], task=ep_by[key]["task"], trigger=t["trigger"], n=t["n"], trace=ep_by[key]["trace"]) for key, t in rows if t["capped"]])
        res["saved_set"] = {key: t["saved_requests"] for key, t in rows if t["saved_requests"]}
        out[k] = res
    return out


def main():
    results = {}
    for name in ("P1", "P2"):
        raw = json.loads((HERE / f"raw_{name}.json").read_text())
        episodes = raw["episodes"]
        disagree = [e["run_id"] for e in episodes if e["logged_supported"] is not None and bool(e["logged_supported"]) != e["supported"]]
        results[name] = dict(episodes=len(episodes), requests=sum(e["requests"] for e in episodes), input_tokens=sum(e["input_tokens"] for e in episodes),
                             supported=sum(e["supported"] for e in episodes), parse_errors=raw["errors"], logged_vs_rescored_disagreements=len(disagree), disagreement_run_ids=disagree[:10],
                             models=by(episodes, "model"), c1=candidate1(raw, name), c2=candidate2(raw, name), c3=candidate3(raw, name), c4=candidate4(raw, name), c3_value_medians=raw["c3_value_medians"])
    # overlap on P1 and P2: sets of (episode, request)
    for name in ("P1", "P2"):
        r = results[name]
        chosen_k = "6"
        for k in ("4", "5", "6"):
            if r["c4"][k]["harm"] == 0 and r["c4"][k]["chg_harm"] == 0 and results["P1"]["c4"][k]["harm"] == 0 and results["P2"]["c4"][k]["harm"] == 0 and results["P1"]["c4"][k]["chg_harm"] == 0 and results["P2"]["c4"][k]["chg_harm"] == 0:
                chosen_k = k
                break
        sets = {"C1": {(k, i) for k, v in (r["c1"]["res"]["saved_set"] or {}).items() for i in v}, "C2": {(k, i) for k, v in r["c2"]["saved_set"].items() for i in v},
                "C3": {(k, i) for k, v in r["c3"]["saved_set"].items() for i in v}, "C4": {(k, i) for k, v in r["c4"][chosen_k]["saved_set"].items() for i in v}}
        names = list(sets)
        pair = {f"{a}&{b}": len(sets[a] & sets[b]) for i, a in enumerate(names) for b in names[i + 1:]}
        union = set().union(*sets.values())
        r["overlap"] = dict(c4_k_used=chosen_k, sizes={n: len(s) for n, s in sets.items()}, pairwise=pair, union=len(union), union_pct=share(len(union), r["requests"]), sum_of_sizes=sum(len(s) for s in sets.values()))
        for c in ("c1", "c2", "c3"):
            pass
    for name in ("P1", "P2"):  # saved_set blobs are large: keep them out of results.json
        for variant in ("res", "task"):
            results[name]["c1"][variant].pop("saved_set", None)
        results[name]["c2"].pop("saved_set", None)
        results[name]["c3"].pop("saved_set", None)
        for k in results[name]["c4"]:
            results[name]["c4"][k].pop("saved_set", None)
    (HERE / "results.json").write_text(json.dumps(results, indent=1, default=str))
    p1 = results["P1"]
    print(json.dumps(dict(P1_requests=p1["requests"], overlap=p1["overlap"]), indent=1))


if __name__ == "__main__":
    main()
