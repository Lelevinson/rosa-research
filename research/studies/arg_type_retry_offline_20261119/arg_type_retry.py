"""Argument-type retry requests and a lossless schema-generic conversion: offline count. Protocol: PROTOCOL.md (hash in PROTOCOL.sha256); read it first. CPU only.
  nice uv run python research/studies/arg_type_retry_offline_20261119/arg_type_retry.py
Flow: saved episodes (candidate_counts population) -> per request, judge each tool call against the schema of the same request (harness.schema_problems, unchanged)
-> try conversions K1-K6 -> check the converted call passes -> find the later exact retries -> counts, bar, events.jsonl."""
import ast
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "research/studies"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIES / "candidate_counts_20261118"))
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import count_candidates as C  # noqa: E402
import harness  # noqa: E402

WRITE_TOOLS = set(harness.WRITE_TOOLS)
STOCK_ARMS = {("s0", "S0"), ("pilot", "A1"), ("fairness", "E0"), ("fairness", "E1")}


# ------------------------------------------------------------------ conversions (protocol section 2)
def scalar(value):
    return isinstance(value, (str, int, float, bool)) and not isinstance(value, type(None))


def convert(value, schema, required):
    """Return (converted_value, [kinds]) or None when a problem has no lossless reading. A value that already matches is returned unchanged (nested values are converted too)."""
    if "anyOf" in schema:
        if any(not harness.schema_problems(value, alt, "") for alt in schema["anyOf"]):
            return value, []
        for alt in schema["anyOf"]:
            got = convert(value, alt, required)
            if got is not None and not harness.schema_problems(got[0], alt, ""):
                return got
        return None
    expected = schema.get("type")
    if expected is None:
        return value, []
    if harness.matches_type(value, expected):
        kinds = []
        if expected == "array" and "items" in schema:
            items = []
            for item in value:
                got = convert(item, schema["items"], True)
                if got is None:
                    return None
                items.append(got[0]); kinds += got[1]
            return items, kinds
        if expected == "object" and "properties" in schema:
            out = dict(value)
            for key, child in schema["properties"].items():
                if key in value:
                    got = convert(value[key], child, key in schema.get("required", []))
                    if got is None:
                        return None
                    out[key] = got[0]; kinds += got[1]
            return out, kinds
        return value, []
    if expected == "array":
        if isinstance(value, str):
            if value == "" and not required:
                return [], ["K3"]
            try:
                parsed = json.loads(value)
            except ValueError:
                parsed = None
            if isinstance(parsed, list):
                got = convert(parsed, schema, required)
                return (got[0], ["K1"] + got[1]) if got is not None else None
        if value is None and not required:
            return [], ["K3"]
        if scalar(value) and not (isinstance(value, str) and (not value.strip() or value.lstrip()[:1] in ("[", "{"))) and not harness.schema_problems(value, schema.get("items", {}), ""):
            return [value], ["K2"]
        return None
    if expected == "object":
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except ValueError:
                return None
            if isinstance(parsed, dict):
                got = convert(parsed, schema, required)
                return (got[0], ["K1"] + got[1]) if got is not None else None
        return None
    if expected in ("integer", "number") and isinstance(value, str):
        try:
            number = int(value)
            if str(number) == value:
                return number, ["K4"]
        except ValueError:
            pass
        if expected == "number":
            try:
                number = float(value)
                if repr(number) == value:
                    return number, ["K4"]
            except ValueError:
                pass
        return None
    if expected == "integer" and isinstance(value, float) and value == int(value):
        return int(value), ["K6"]
    if expected == "boolean" and isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true", ["K5"]
    return None


def judge_call(name, args, schema):
    """dict(problems, fixable, converted, kinds, reasons). Write tools are never fixable."""
    problems = harness.schema_problems(args, schema, "")
    if not problems:
        return None
    reasons = [f"{path.lstrip('.') or '(root)'}: expected {expected}, received {harness.type_name(received) if received != 'missing' else 'missing'}" for path, expected, received in problems]
    got = None if name in WRITE_TOOLS else convert(args, schema, True)
    fixable = got is not None and not harness.schema_problems(got[0], schema, "")
    return dict(problems=reasons, fixable=fixable, converted=got[0] if fixable else None, kinds=sorted(set(got[1])) if fixable else [])


# ------------------------------------------------------------------ one episode
def read_episode(row):
    events = [json.loads(line) for line in (ROOT / row["trace_path"]).read_text().splitlines()]
    requests, current = [], None
    for e in events:
        if e["kind"] == "model_start":
            current = dict(index=len(requests) + 1, schemas={s["function"]["name"]: s["function"]["parameters"] for s in e.get("schemas", []) if "function" in s}, calls=[], events=[])
            requests.append(current)
        elif e["kind"] == "model_end" and current is not None:
            current["usage"] = e.get("usage") or {}
            current["calls"] = [dict(name=c["name"], args=c.get("args") or {}) for c in (e["message"].get("tool_calls") or [])]
        elif current is not None:
            current["events"].append(e)
    return events, requests


def consequence(request, call, last_request, tool_ends):
    pre = [e for e in request["events"] if e["kind"] == "handler" and e.get("event") == "validation_error" and e.get("tool") == call["name"] and e.get("args") == call["args"]]
    if pre:
        return "precheck_rejected"
    for e in request["events"]:
        if e["kind"] == "tool_start" and e.get("name") == call["name"]:
            try:
                args = ast.literal_eval(e["input"]) if isinstance(e["input"], str) else e["input"]
            except (ValueError, SyntaxError):
                args = None
            if args == call["args"]:
                out = tool_ends.get(e.get("run_id"), {}).get("output")
                if isinstance(out, str) and (out.startswith("Invalid arguments") or "validation error" in out.lower()):
                    return "error_text_returned"
                return "executed_by_stock" if out is not None else "no_result"
    return "episode_ended" if last_request else "unknown"


def episode_events(study, row):
    events, requests = read_episode(row)
    tool_ends = {e.get("run_id"): e for e in events if e["kind"] == "tool_end"}
    found, converted_calls = [], {}
    for request in requests:
        for position, call in enumerate(request["calls"]):
            schema = request["schemas"].get(call["name"])
            if schema is None:
                continue
            verdict = judge_call(call["name"], call["args"], schema)
            if verdict is None:
                continue
            ev = dict(request=request["index"], position=position, tool=call["name"], args=call["args"], consequence=consequence(request, call, request["index"] == len(requests), tool_ends), **verdict)
            found.append(ev)
            if verdict["fixable"]:
                converted_calls.setdefault((call["name"], json.dumps(verdict["converted"], sort_keys=True)), []).append(request["index"])
    # retry requests (protocol section 3, item 4)
    pure, mixed, retried = [], [], set()
    for request in requests:
        keys = [(c["name"], json.dumps(c["args"], sort_keys=True)) for c in request["calls"]]
        hits = [k for k in keys if any(r < request["index"] for r in converted_calls.get(k, []))]
        if hits and len(hits) == len(keys):
            pure.append(request["index"])
        elif hits:
            mixed.append(request["index"])
        retried |= set(hits)
    for ev in found:
        if ev["fixable"]:
            ev["retried_exactly"] = (ev["tool"], json.dumps(ev["converted"], sort_keys=True)) in retried
    usage = {r["index"]: (r.get("usage", {}).get("input_tokens", 0) + r.get("usage", {}).get("output_tokens", 0)) for r in requests}
    return found, dict(pure=pure, mixed=mixed, pure_tokens=sum(usage.get(i, 0) for i in pure), requests=len(requests))


def main():
    tasks = C.all_tasks()
    out_events, episodes = [], []
    for study, row in C.load_population():
        found, retry = episode_events(study, row)
        group = "stock" if (study, row["arm"]) in STOCK_ARMS else "menu"
        full_type = (study, row["arm"]) in C.FULL_TYPE
        episodes.append(dict(run_id=row["run_id"], study=study, arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], group=group, full_type=full_type, requests=row["llm_requests"],
                             events=len(found), fixable=sum(e["fixable"] for e in found), write_events=sum(e["tool"] in WRITE_TOOLS for e in found), saved_max=len(retry["pure"]), mixed_retry=len(retry["mixed"]),
                             tokens_saved_max=retry["pure_tokens"], trace=row["trace_path"]))
        for e in found:
            out_events.append(dict(run_id=row["run_id"], arm=row["arm"], model=row["model"], task=row["task"], group=group, full_type=full_type, trace=row["trace_path"], **e))
    return episodes, out_events


def tally(episodes, events):
    fixable = [e for e in events if e["fixable"]]
    return dict(episodes=len(episodes), requests=sum(e["requests"] for e in episodes), events=len(events), episodes_with_event=sum(bool(e["events"]) for e in episodes),
                fixable_events=len(fixable), episodes_with_fixable=sum(bool(e["fixable"]) for e in episodes), write_tool_events=sum(e["tool"] in WRITE_TOOLS for e in events),
                saved_max_requests=sum(e["saved_max"] for e in episodes), mixed_retry_requests=sum(e["mixed_retry"] for e in episodes), tokens_saved_max=sum(e["tokens_saved_max"] for e in episodes),
                by_kind=dict(Counter(k for e in fixable for k in e["kinds"])), by_tool=dict(Counter(e["tool"] for e in events)), fixable_by_tool=dict(Counter(e["tool"] for e in fixable)),
                consequence=dict(Counter(e["consequence"] for e in events)), fixable_consequence=dict(Counter(e["consequence"] for e in fixable)),
                not_convertible_reasons=dict(Counter(r.split(":", 1)[1].strip() for e in events if not e["fixable"] for r in e["problems"]).most_common(12)),
                fixable_ended_episode=sum(1 for e in fixable if e["consequence"] == "episode_ended"))


if __name__ == "__main__":
    episodes, events = main()
    by = lambda key: {k: tally([e for e in episodes if key(e) == k], [v for v in events if key(v) == k]) for k in sorted({key(e) for e in episodes})}
    full_menu = [e for e in episodes if e["full_type"]]
    full_events = [v for v in events if v["full_type"]]
    t = tally(full_menu, full_events)
    models_fixable = {e["model"] for e in full_menu if e["fixable"]}
    fixable_full = [v for v in full_events if v["fixable"]]
    tool_share = (max(Counter(v["tool"] for v in fixable_full).values()) / len(fixable_full)) if fixable_full else None
    not_sparse = t["saved_max_requests"] >= 0.01 * t["requests"] and t["episodes_with_fixable"] >= 10 and len(models_fixable) >= 2
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], overall=tally(episodes, events), full_type_menu=t, by_group=by(lambda x: x["group"]), by_model=by(lambda x: x["model"]),
               bar=dict(not_sparse=not_sparse, saved_share=t["saved_max_requests"] / max(t["requests"], 1), episodes_with_fixable=t["episodes_with_fixable"], models=sorted(models_fixable),
                        top_tool_share=tool_share, verdict="not sparse: a live test may be proposed to the owner" if not_sparse else "sparse: executor-level fix for every arm, no live test"))
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=str))
    with (HERE / "events.jsonl").open("w") as handle:
        for v in events:
            handle.write(json.dumps(v, default=str) + "\n")
    (HERE / "episodes.jsonl").write_text("\n".join(json.dumps(e, default=str) for e in episodes) + "\n")
    print(json.dumps(dict(overall=out["overall"], full_type_menu=t, bar=out["bar"]), indent=1, default=str))
