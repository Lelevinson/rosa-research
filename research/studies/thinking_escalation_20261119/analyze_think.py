"""Analysis of the thinking-escalation run, applying the frozen reading rule of PROTOCOL.md sections 4-5. Written and hashed BEFORE the full run starts.
  uv run python research/studies/thinking_escalation_20261119/analyze_think.py [full|smoke]
Reads RESULTS_LOG.jsonl and the traces; writes results.json (phase 'full') or results_smoke.json. CPU only.
Trigger events come from the `call_class` / `trigger_fire` events that the arm logs in ALL arms (same code); outcomes O1-O3 are computed identically in all arms."""
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ARMS = ("FULL", "ESCALATE", "ALWAYS")
PRECEDENCE = ["error", "not_found", "empty", "repeat"]
CHG = {"e1h_chg_1", "e1h_chg_2"}


def read(path):
    return [json.loads(line) for line in (ROOT / path).read_text().splitlines()]


def thinking_estimate(end):
    """Protocol section 4: max(0, output_tokens - ceil(len(content + json(tool_calls)) / 4)). Same formula for every arm and model."""
    message = end.get("message", {})
    visible = (message.get("content") or "") + json.dumps(message.get("tool_calls") or [])
    return max(0, (end.get("usage") or {}).get("output_tokens", 0) - math.ceil(len(visible) / 4))


def episode_detail(row):
    events = read(row["trace_path"])
    ends = [e for e in events if e["kind"] == "model_end"]
    level = {e["request"]: e["level"] for e in events if e["kind"] == "handler" and e.get("event") == "think_request"}
    # request index of each tool_start = number of model_end events before it (final_answer is not a call_class event)
    count, final_requests = 0, set()
    for e in events:
        if e["kind"] == "model_end":
            count += 1
        elif e["kind"] == "tool_start" and e.get("name") == "final_answer":
            final_requests.add(count)
    calls = defaultdict(list)
    for e in events:
        if e["kind"] == "handler" and e.get("event") == "call_class":
            calls[e["request"]].append(dict(klass=e["klass"], key=(e["tool"], json.dumps(e["args"], sort_keys=True, default=str))))
    fires = []
    for e in events:
        if e["kind"] == "handler" and e.get("event") == "trigger_fire":
            t = e["request"]
            classes = [c["klass"] for c in calls[t] if c["klass"] != "ok"]
            klass = next((k for k in PRECEDENCE if k in classes), e["klass"])
            trigger_call = next((c["key"] for c in calls[t] if c["klass"] != "ok"), None)
            outcome = {}
            for step in (1, 2):
                nxt = t + step
                if nxt > len(ends):
                    outcome[step] = None
                    continue
                nc = calls.get(nxt, [])
                outcome[step] = dict(O1=bool(nc) and nc[0]["key"] != trigger_call, O2=any(c["klass"] == "ok" for c in nc), O3=nxt in final_requests, escalated=level.get(nxt) is not None)
            fires.append(dict(request=t, klass=klass, outcome=outcome))
    thinking = [thinking_estimate(e) for e in ends]
    reasoning_chars = sum(len((e["message"].get("additional_kwargs") or {}).get("reasoning_content") or "") for e in ends)
    length_cuts = sum((e.get("response_metadata") or {}).get("done_reason") == "length" for e in ends)
    escalated_out = [(e.get("usage") or {}).get("output_tokens", 0) for i, e in enumerate(ends, 1) if level.get(i) is not None]
    plain_out = [(e.get("usage") or {}).get("output_tokens", 0) for i, e in enumerate(ends, 1) if level.get(i) is None]
    end_event = next((e for e in events if e["kind"] == "episode_end"), {})
    end_text = end_event.get("answer")
    return dict(fires=fires, thinking_tokens_est=sum(thinking), reasoning_chars=reasoning_chars, length_cuts=length_cuts, thinking_requests=len(escalated_out),
                escalated_output_tokens=sum(escalated_out), plain_output_tokens=sum(plain_out), plain_requests=len(plain_out),
                capped=isinstance(end_text, str) and "max iterations" in end_text, backend_error=bool(end_event.get("error")))


def episode_metrics(row):
    d = episode_detail(row)
    timeout = any("episode timeout" in str(a) for a in row["aborts"])
    return dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], supported=bool(row["supported_complete"]), requests=row["llm_requests"],
                input_tokens=row["input_tokens"], output_tokens=row["output_tokens"], wall_seconds=row["wall_seconds"], timeout=timeout,
                no_answer=row["answer"] in (None, {}, ""), infra=row["llm_requests"] == 0, trace=row["trace_path"], **d)


def aggregate(rows):
    fires = [f for r in rows for f in r["fires"]]
    t1 = [f["outcome"][1] for f in fires if f["outcome"][1] is not None]
    rate = lambda key: (sum(o[key] for o in t1) / len(t1)) if t1 else None
    return dict(episodes=len(rows), supported=sum(r["supported"] for r in rows), requests=sum(r["requests"] for r in rows), input_tokens=sum(r["input_tokens"] for r in rows),
                output_tokens=sum(r["output_tokens"] for r in rows), thinking_tokens_est=sum(r["thinking_tokens_est"] for r in rows), reasoning_chars=sum(r["reasoning_chars"] for r in rows),
                wall_seconds=round(sum(r["wall_seconds"] for r in rows)), capped=sum(r["capped"] for r in rows), timeouts=sum(r["timeout"] for r in rows), no_answer=sum(r["no_answer"] for r in rows),
                backend_errors=sum(r["backend_error"] for r in rows), length_cuts=sum(r["length_cuts"] for r in rows), infra_failed=sum(r["infra"] for r in rows),
                fires=len(fires), events_with_next=len(t1), O1_rate=rate("O1"), O2_rate=rate("O2"), O3_rate=rate("O3"), fires_by_class=dict(Counter(f["klass"] for f in fires)),
                thinking_requests=sum(r["thinking_requests"] for r in rows), escalated_output_tokens=sum(r["escalated_output_tokens"] for r in rows),
                plain_output_tokens=sum(r["plain_output_tokens"] for r in rows), plain_requests=sum(r["plain_requests"] for r in rows))


def decide(agg, by_model):
    """PROTOCOL.md section 5. agg: arm -> aggregate; by_model: arm -> model -> aggregate."""
    full, esc, alw = agg["FULL"], agg["ESCALATE"], agg["ALWAYS"]
    have_always = alw["episodes"] > 0  # part B may not have run yet: C0 (headroom) is then not evaluated
    c0 = (alw["supported"] - full["supported"] >= 4) if have_always else None
    pooled_gain = None if full["O2_rate"] is None or esc["O2_rate"] is None else esc["O2_rate"] - full["O2_rate"]
    models, hits, evaluable = {}, 0, 0
    for m in by_model["FULL"]:
        f, e = by_model["FULL"][m], by_model["ESCALATE"][m]
        if f["events_with_next"] < 15 or e["events_with_next"] < 15:
            models[m] = dict(status="not evaluable", full_events=f["events_with_next"], esc_events=e["events_with_next"])
            continue
        evaluable += 1
        gain = e["O2_rate"] - f["O2_rate"]
        hit = gain > 0
        hits += hit
        models[m] = dict(status="higher" if hit else "not higher", gain=gain, full_events=f["events_with_next"], esc_events=e["events_with_next"])
    mechanism = pooled_gain is not None and pooled_gain >= 0.10 - 1e-9 and hits >= 2  # tolerance for float rounding: the 10-point threshold is inclusive
    flags = []
    if esc["supported"] - full["supported"] < -3:
        flags.append("supported lower by more than 3 cells")
    if full["requests"] and (esc["requests"] - full["requests"]) / full["requests"] >= 0.15:
        flags.append("requests up by 15% or more")
    bad = lambda a: a["timeouts"] + a["capped"] + a["no_answer"]
    if bad(esc) - bad(full) >= 5:
        flags.append("timeouts + cap endings + no-answer endings up by 5 or more")
    if esc["length_cuts"] - full["length_cuts"] >= 10:
        flags.append("length-cut responses up by 10 or more")
    tokens = lambda a: a["input_tokens"] + a["output_tokens"]
    cost = []
    if tokens(esc) >= 1.5 * tokens(full):
        cost.append("tokens at least 1.5x FULL")
    if esc["wall_seconds"] >= 1.5 * full["wall_seconds"]:
        cost.append("wall seconds at least 1.5x FULL")
    klass = "A" if mechanism and not flags else ("B" if not mechanism and not flags else ("D" if mechanism else "C"))
    return dict(C0_headroom=c0, always_minus_full_supported=(alw["supported"] - full["supported"]) if have_always else None, escalate_minus_full_supported=esc["supported"] - full["supported"], pooled_O2_gain=pooled_gain,
                per_model=models, models_higher=hits, evaluable_models=evaluable, mechanism_met=mechanism, harm_flags=flags, cost_flags=cost, klass=klass)


def main(phase="full"):
    rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
    # amendment A1: the full study is part A (FULL, ESCALATE) and part B (ALWAYS, later, separate sessions); phase "full" reads both parts (and the original combined phase if present)
    wanted = {"full", "partA", "partB"} if phase == "full" else {phase}
    rows = [r for r in rows if r.get("phase") in wanted]
    metrics = [episode_metrics(r) for r in rows]
    models = sorted({m["model"] for m in metrics})
    by = lambda arm, key=lambda m: True: [m for m in metrics if m["arm"] == arm and key(m)]
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], phase=phase, episodes=len(metrics), tables={})
    for arm in ARMS:
        out["tables"][arm] = dict(overall=aggregate(by(arm)), by_model={m: aggregate(by(arm, lambda r, m=m: r["model"] == m)) for m in models},
                                  by_task={t: aggregate(by(arm, lambda r, t=t: r["task"] == t)) for t in sorted({m["task"] for m in metrics})})
        by_class = {}
        for klass in PRECEDENCE:
            sel = [f["outcome"][1] for r in by(arm) for f in r["fires"] if f["klass"] == klass and f["outcome"][1] is not None]
            by_class[klass] = dict(events=len(sel), O1=sum(o["O1"] for o in sel), O2=sum(o["O2"] for o in sel), O3=sum(o["O3"] for o in sel))
        out["tables"][arm]["outcomes_by_class"] = by_class
    cells = defaultdict(dict)
    for m in metrics:
        cells[(m["task"], m["model"], m["seed"])][m["arm"]] = m["supported"]
    out["paired"] = {}
    for other in ("ESCALATE", "ALWAYS"):
        counter = Counter()
        for c in cells.values():
            if "FULL" in c and other in c:
                counter["both" if c["FULL"] and c[other] else "FULL_only" if c["FULL"] else f"{other}_only" if c[other] else "neither"] += 1
        out["paired"][other] = dict(counter)
    out["decision"] = decide({a: out["tables"][a]["overall"] for a in ARMS}, {a: out["tables"][a]["by_model"] for a in ARMS})
    out["episode_rows"] = [{k: v for k, v in m.items()} for m in metrics]
    name = "results.json" if phase == "full" else f"results_{phase}.json"
    (HERE / name).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(dict(episodes=len(metrics), paired=out["paired"], decision=out["decision"], overall={a: out["tables"][a]["overall"] for a in ARMS}), indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
