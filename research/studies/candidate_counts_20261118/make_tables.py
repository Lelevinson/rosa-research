"""Formats results.json (frozen counts) and posthoc.json into TABLES.md. No new rules or counts.  uv run python research/studies/candidate_counts_20261118/make_tables.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "results.json").read_text())
MODELS = ["bonsai-2:4b", "lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b"]
lines = ["# Tables (generated from results.json; protocol hash " + r["protocol_sha256"][:16] + ")", ""]


def grid(title, by_study):
    lines.append(f"## {title}")
    lines.append("| study | " + " | ".join(MODELS) + " | all |")
    lines.append("|---|" + "---:|" * (len(MODELS) + 1))
    for study, cells in by_study.items():
        lines.append(f"| {study} | " + " | ".join(str(cells.get(m, 0)) for m in MODELS) + f" | {cells.get('ALL', 0)} |")
    lines.append("")


pop = r["population"]["per_study_model"]
studies = sorted({k.split("|")[0] for k in pop})
grid("Population (episodes)", {s: {m: pop.get(f"{s}|{m}", 0) for m in MODELS + ["ALL"]} for s in studies})
a = r["a_name_binding"]
grid("(a) Name-binding fires (not-found, no leading slash, unique whole-segment suffix of a clean-ledger name)", {**{s: v for s, v in a["by_study_model"].items() if s != "ALL STUDIES"}, "ALL STUDIES": a["by_study_model"]["ALL STUDIES"]})
lines += ["### (a) verdict by model (agree = the model's next successful call on that short name used the resolution; differ = a different entity; no_later_use = never used successfully)", "| model | agree | differ | no_later_use |", "|---|---:|---:|---:|"]
for m in MODELS:
    v = a["verdict_by_model"].get(m, {})
    lines.append(f"| {m} | {v.get('agree', 0)} | {v.get('differ', 0)} | {v.get('no_later_use', 0)} |")
lines += ["", f"Request distance (fire to next successful call on that name), median {a['request_distance_median']}, mean {a['request_distance_mean']}. Bar: {a['bar']}.", ""]
b = r["b_partial_match"]
grid("(b) Partial-match exposure events (list/pattern call, absolute name, no exact match, >= 1 partial match)", b["by_study_model"])
lines += [f"Events {b['events']} in {b['episodes']} episodes. Final answer names an exposed partial match: {b['answer_names_partial']} events (supported episodes among all events: {b['supported_events']} of {b['events']}). Answer names the typed, non-existent name: {b['answer_names_typed_nonexistent']} events. Partial match is part of the fixture truth: {b['partial_is_truth']} events.", ""]
lines += ["## (c) Finish tool: ending class and supported rate", "### FULL-type arms (pilot C1, round1 C1, round2 CONTROL, ablation FULL, compaction FULL), by model", "| model | ending | episodes | supported | rate |", "|---|---|---:|---:|---:|"]
for m in MODELS + ["ALL"]:
    for e, v in r["c_finish_tool"]["full_type_by_model"].get(m, {}).items():
        lines.append(f"| {m} | {e} | {v['episodes']} | {v['supported']} | {v['supported_rate']} |")
lines += ["", "### By group, study/arm (all models)", "| group | study/arm | ending | episodes | supported |", "|---|---|---|---:|---:|"]
for g, arms in r["c_finish_tool"]["by_group"].items():
    for arm, models in arms.items():
        for e, v in models.get("ALL", {}).items():
            lines.append(f"| {g} | {arm} | {e} | {v['episodes']} | {v['supported']} |")
lines += ["", "Round-1 bare-text nudge result is quoted in the report from `decisions/2026-11-17-finish-gate-check.md`, not recomputed.", ""]
d = r["d_needle_missed"]
grid("(d) D1 needle-missed episodes (failed, answer wrong, every support fact present by the scorer's rule)", d["D1_by_study_model"])
lines += [f"D1 {d['D1_episodes']} episodes, {d['D1_distinct_task_model']} distinct (task, model) pairs, models {d['D1_models']}; D0 (no answer, facts present) {d['D0_episodes']}; S (answer exact, fact not read) {d['S_episodes']}; long (>= 8,000 chars) D1 {d['D1_long']} over {d['D1_long_models']}. Bar: {d['bar']}; long subset alone reaches bar: {d['long_alone_reaches_bar']}.", ""]
lines += ["## (e) Detector counts (all arms; per study, all models)", "| detector | " + " | ".join(studies) + " |", "|---|" + "---:|" * len(studies)]
for name, cells in r["e_detectors"].items():
    lines.append(f"| {name} | " + " | ".join(str(cells.get(f"{s}|ALL", 0)) for s in studies) + " |")
lines += ["", "Examples (first three traces per detector) are in results.json `e_examples`.", ""]
lines += ["## B0 disagreements (excluded from (c) and (d))", ""] + [f"- {x['run_id']}: {x['labels']}" for x in pop_b0] if (pop_b0 := r["population"]["b0_disagreements"]) else ["## B0: none", ""]
(HERE / "TABLES.md").write_text("\n".join(lines) + "\n")
print("wrote TABLES.md", len(lines), "lines")
