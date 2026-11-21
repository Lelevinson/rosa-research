"""Markdown tables from results.json (no new computation)."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
d = json.loads((HERE / "results.json").read_text())
L = ["# Tables (generated from results.json; protocol hash " + d["protocol_sha256"][:12] + "...)", ""]
i1 = d["item1"]
L += ["## Item 1. Write-tool attempts by arm and execution status", "", "| arm | episodes in arm | episodes with an attempt | no_result_validation | validation_text | guard_rejected | not_available | executed | by model |", "|---|---|---|---|---|---|---|---|---|"]
for k, v in i1["by_arm"].items():
    L.append(f"| {k} | {v['episodes_in_arm']} | {v['episodes_with_attempt']} | {v.get('no_result_validation', 0)} | {v.get('validation_text', 0)} | {v.get('guard_rejected', 0)} | {v.get('not_available', 0)} | {v.get('executed', 0)} | {i1['per_model_by_arm'][k]} |")
L += ["", "Would have changed (inference from arguments and fixture listings):", "", "| arm | classes |", "|---|---|"]
for k, v in i1["would_change_by_arm"].items():
    L.append(f"| {k} | {v} |")
L += ["", "Arms with 0 attempts (episodes): " + "; ".join(f"{k} ({v['episodes']})" for k, v in i1["arms_with_no_attempt"].items()) + ".", ""]
L += ["## Item 2. Per-episode requests and tokens", "", "| arm | n | requests median / p90 / max | tokens median / p90 / max | cap endings (>=40 requests) | top-decile share of requests | models with a cap |", "|---|---|---|---|---|---|---|"]
for k, v in d["item2"].items():
    p = v["pooled"]
    L.append(f"| {k} | {v['episodes']} | {p['requests']['median']} / {p['requests']['p90']} / {p['requests']['max']} | {p['tokens']['median']:.0f} / {p['tokens']['p90']:.0f} / {p['tokens']['max']:.0f} | {p['cap_endings']} ({p['requests_ge_40']}) | {v['top_decile_share_of_requests']} | {v['cap_models']} |")
L += ["", "Per model (requests median / p90 / max; tokens median / p90 / max; caps):", ""]
for k, v in d["item2"].items():
    L.append(f"- **{k}**: " + "; ".join(f"{m} {p['requests']['median']}/{p['requests']['p90']}/{p['requests']['max']}, {p['tokens']['median']:.0f}/{p['tokens']['p90']:.0f}/{p['tokens']['max']:.0f}, cap {p['cap_endings']}" for m, p in v["per_model"].items()))
i3 = d["item3"]
L += ["", "## Item 3. Repeat loops (episodes with >= 2 identical successful repeats)", "", f"Rebuild check B3a: {i3['b3a_rebuild_agreement']}. Episodes of interest: {i3['episodes_of_interest']}.", "",
      "| group | facts_present: episodes / unsupported / no answer / requests after first repeat (median) | facts_not_yet: episodes / unsupported / no answer / requests after (median) |", "|---|---|---|"]
def row(name, t):
    a, b = t["facts_present"], t["facts_not_yet"]
    return f"| {name} | {a['episodes']} / {a['unsupported']} / {a['no_answer']} / {a['requests_after_first_repeat_median']} | {b['episodes']} / {b['unsupported']} / {b['no_answer']} / {b['requests_after_first_repeat_median']} |"
L.append(row("pooled", i3["pooled"]))
for m, t in i3["per_model"].items():
    L.append(row(m, t))
L += [row("stock-executor arms", i3["stock_arms"]), row("menu arms", i3["menu_arms"]), "", f"Bar B3 inputs: {i3['bar_B3']}"]
(HERE / "TABLES.md").write_text("\n".join(L) + "\n")
