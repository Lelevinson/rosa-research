"""Measured-only: size of each offered tool schema (name+arguments vs description text), from the saved ablation traces. CPU only.
Characters are exact (the serialized schema in the model_start event). Tokens are ESTIMATED from characters with a per-model ratio taken from the exact measurement
'35 extra schemas of the 48-tool menu = +N input tokens at request 1' (same cell, same prompt): ratio = N / characters of those 35 schemas. uv run python schema_sizes.py"""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["phase"] == "full"]
first = lambda r: next(json.loads(l) for l in (REPO / r["trace_path"]).read_text().splitlines() if json.loads(l)["kind"] == "model_start")
req1 = lambda r: next((json.loads(l).get("usage") or {}).get("input_tokens") for l in (REPO / r["trace_path"]).read_text().splitlines() if json.loads(l)["kind"] == "model_end")
full = {(r["task"], r["model"]): r for r in rows if r["arm"] == "FULL"}
menu = {(r["task"], r["model"]): r for r in rows if r["arm"] == "NO_MENU"}
ex_f, ex_m = first(next(iter(full.values()))), first(next(iter(menu.values())))
schemas13 = {s["function"]["name"]: s for s in ex_f["schemas"]}
schemas48 = {s["function"]["name"]: s for s in ex_m["schemas"]}
assert len(schemas13) == 13 and len(schemas48) == 48
size = lambda s: dict(name_args=len(json.dumps(dict(name=s["function"]["name"], parameters=s["function"]["parameters"]), separators=(", ", ": "))), description=len(s["function"]["description"]))
extra = [n for n in schemas48 if n not in schemas13]
extra_chars = sum(sum(size(schemas48[n]).values()) for n in extra)
# the same schema in every trace (tools are static): verify
for r in list(full.values())[:5] + list(menu.values())[:5]:
    ss = {s["function"]["name"]: s for s in first(r)["schemas"]}
    assert all(ss[n] == (schemas13 if len(ss) == 13 else schemas48)[n] for n in ss)
ratio = {}
for model in sorted({k[1] for k in full}):
    deltas = {req1(menu[k]) - req1(full[k]) for k in full if k[1] == model}
    assert len(deltas) == 1, (model, deltas)
    ratio[model] = dict(extra_tokens=deltas.pop())
    ratio[model]["tokens_per_char"] = ratio[model]["extra_tokens"] / extra_chars
# second ratio (lower bound of the range): fit to each model's own request-1 total, assuming 0.25 tokens per character for the prose of system prompt + task (an ASSUMPTION)
chars13 = sum(sum(size(s).values()) for s in schemas13.values())
for model in ratio:
    fits = []
    for k, r in full.items():
        if k[1] != model:
            continue
        msgs = first(r)["messages"]
        prose = sum(len(m["content"]) for m in msgs)
        fits.append((req1(r) - 0.25 * prose) / chars13)
    ratio[model]["tokens_per_char_fit"] = sum(fits) / len(fits)
out = dict(extra_35_tools_characters=extra_chars, per_model=ratio, tools={})
lines = ["| tool | name+arguments chars | description chars | total chars | est. tokens as a range fit-to-total to 35-tool ratio (lfm3 / qwen3.5 / gpt-oss / bonsai) | description share |", "|---|---:|---:|---:|---|---:|"]
tot = dict(name_args=0, description=0)
for name, s in schemas13.items():
    z = size(s)
    tot["name_args"] += z["name_args"]; tot["description"] += z["description"]
    est = {m: f'{round((z["name_args"] + z["description"]) * ratio[m]["tokens_per_char_fit"])}-{round((z["name_args"] + z["description"]) * ratio[m]["tokens_per_char"])}' for m in ratio}
    out["tools"][name] = dict(z, total=z["name_args"] + z["description"], est_tokens=est)
    lines.append(f"| {name} | {z['name_args']} | {z['description']} | {z['name_args'] + z['description']} | {est['lfm3:1.7b']} / {est['qwen3.5:9b']} / {est['gpt-oss:20b']} / {est['bonsai-2:4b']} | {z['description'] / (z['name_args'] + z['description']):.0%} |")
t_all = tot["name_args"] + tot["description"]
est_all = {m: f'{round(t_all * ratio[m]["tokens_per_char_fit"])}-{round(t_all * ratio[m]["tokens_per_char"])}' for m in ratio}
lines.append(f"| **all 13** | {tot['name_args']} | {tot['description']} | {t_all} | {est_all['lfm3:1.7b']} / {est_all['qwen3.5:9b']} / {est_all['gpt-oss:20b']} / {est_all['bonsai-2:4b']} | {tot['description'] / t_all:.0%} |")
out["all13"] = dict(tot, total=t_all, est_tokens=est_all)
out["table"] = "\n".join(lines)
(HERE / "schema_sizes.json").write_text(json.dumps(out, indent=1))
print("35 extra tools: chars", extra_chars, {m: (v["extra_tokens"], round(v["tokens_per_char"], 3), round(v["tokens_per_char_fit"], 3)) for m, v in ratio.items()})
print("\n".join(lines))
