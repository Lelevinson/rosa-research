"""Formats results.json into TABLES.md (no new numbers).  uv run python research/studies/canonical_render_20261118/make_tables.py"""
import json
from pathlib import Path
H = Path(__file__).resolve().parent
r = json.loads((H / "results.json").read_text())
L = [f"# Tables (generated from results.json; protocol hash {r['protocol_sha256'][:16]})", "", f"Episodes {r['episodes']}, menu-tool results {r['results']}. Bars: {r['bars']}. Not idempotent: {r['not_idempotent']}.", "",
     "## Parsed vs passed through, per tool", "| tool | results | changed | leaves | share rendered | lines | key-value | header | bare | chars in rendered leaves | derived lines |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
for t, v in r["tool_table"].items():
    L.append(f"| {t} | {v['results']} | {v['results_changed']} | {v['leaves']} | {v['share_leaves_rendered']} | {v['lines']} | {v['share_key_value']} | {v['share_header']} | {v['share_bare']} | {v['share_chars_in_rendered_leaves']} | {v['derived_lines']} |")
tool = r["tool_table"]
L += ["", f"All tools: leaves {sum(v['leaves'] for v in tool.values())}, rendered {sum(v['leaves_rendered'] for v in tool.values())}; results changed {sum(v['results_changed'] for v in tool.values())} of {r['results']}; derived lines {sum(v['derived_lines'] for v in tool.values())}; R6 skips {sum(sum(v['skips'].values()) for v in tool.values())}.", "",
      "## Size (characters of the JSON text of each result)", f"Change per result: {r['size']['chars_change']}; larger {r['size']['larger']}, equal {r['size']['equal']}, smaller {r['size']['smaller']}; total {r['size']['total_before']} -> {r['size']['total_after']}.", "",
      "| tool | results | mean chars before | mean chars after | median change |", "|---|---:|---:|---:|---:|"]
for t, v in r["size"]["by_tool"].items():
    L.append(f"| {t} | {v['results']} | {v['mean_before']} | {v['mean_after']} | {v['median_change']} |")
h = r["history"]
L += ["", "## Per-episode history effect (estimated input tokens = characters / 4 x later requests)", f"Per episode: {h['delta_tokens_est']}; as % of logged input tokens: {h['percent_of_logged_input_tokens']}. Total {h['total_delta_tokens_est']} estimated tokens against {h['total_logged_input_tokens']} logged input tokens.", "",
      "| group | episodes | estimated token change | logged input tokens | change % |", "|---|---:|---:|---:|---:|"]
for name, group in (("model", h["by_model"]), ("study", h["by_study"])):
    for k, v in group.items():
        L.append(f"| {name}: {k} | {v['episodes']} | {v['total_delta_tokens_est']} | {v['total_logged_input_tokens']} | {100 * v['total_delta_tokens_est'] / v['total_logged_input_tokens']:.2f} |")
f = r["fires"]
L += ["", "## Where the resolution of each name fire lives (item 5)", f"Fires {f['total']}: {f['by_kind']}. Split-only fires whose rendered earlier results contain the full name as one string: {f['split_only_rendered_has_full_name']}. Relation of the typed name to the name field: {f['split_only_relation']}.", "",
      "| group | task text | contiguous earlier | split-only |", "|---|---:|---:|---:|"]
for name, group in (("model", f["by_model"]), ("study", f["by_study"])):
    for k, v in group.items():
        L.append(f"| {name}: {k} | {v.get('task_text', 0)} | {v.get('contiguous_earlier', 0)} | {v.get('split_only', 0)} |")
(H / "TABLES.md").write_text("\n".join(L) + "\n")
print("wrote", len(L), "lines")
