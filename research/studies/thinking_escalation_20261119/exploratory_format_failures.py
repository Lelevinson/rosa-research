"""EXPLORATORY offline count (owner's request 2026-11-19; no protocol, CPU only, existing traces): in FULL-type arms, how many episodes and requests are lost to interface / format failures
that schema-constrained decoding (a grammar that forces a valid tool name, valid JSON arguments of the right types, and a valid final_answer call) would make impossible.
  nice uv run python research/studies/thinking_escalation_20261119/exploratory_format_failures.py
Populations (FULL-type = the 12-tool loop with soft errors, strict pre-check and a finish tool): P1 = the 416 FULL-type episodes of candidate_counts_20261118; P2 = the later FULL arms:
canonical rendering FULL (144), finish split FULL (80), repeat-finish nudge FULL (80), thinking part A FULL (80), thinking replication FULL (144). Categories are defined in the report; an episode can have several."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S = ROOT / "research/studies"
sys.path.insert(0, str(S / "candidate_counts_20261118"))
sys.path.insert(0, str(S / "small_model_harness_20261115"))
import count_candidates as C  # noqa: E402
import harness  # noqa: E402

TOOLS = list(harness.DOMAIN_TOOLS) + ["final_answer"]
CALL_LIKE = re.compile(r'(<function|<tool_call|<\|tool_call|"name"\s*:\s*"(?:%s)"|\b(?:%s)\s*\(|\b(?:%s)\s*\{)' % ("|".join(TOOLS), "|".join(TOOLS), "|".join(TOOLS)))
CAP_TEXT = "Agent stopped due to max iterations."
PILOT = {r["run_id"]: r["new"] for r in json.loads((S / "residual_failures_20261115/rescore_v2.json").read_text())}


def has_json_object(text):
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[m.start():])
            if isinstance(value, dict):
                return True
        except ValueError:
            continue
    return False


def classify(trace_path):
    events = [json.loads(line) for line in (ROOT / trace_path).read_text().splitlines()]
    out = dict(requests=0, A_events=0, B_events=0, C_text_calls=0, E_xml=0, E_parse_tool_call=0, E_other_backend=0, G_value_errors=0, A_req=set(), B_req=set(), C_req=set(), E_req=set(), empty_req=set(),
               text_ending=False, text_ending_json=False, final_invalid=0, ending="")
    request = 0
    accepted = False
    for e in events:
        k = e["kind"]
        if k == "model_end":
            request += 1
            m = e["message"]
            if not (m.get("tool_calls") or []):
                content = m.get("content") or ""
                if CALL_LIKE.search(content):
                    out["C_text_calls"] += 1; out["C_req"].add(request)
        elif k == "model_start":
            out["requests"] += 1
        elif k == "handler":
            ev = e.get("event")
            if ev in ("validation_error", "stock_validation_error"):
                out["A_events"] += 1; out["A_req"].add(request)
            elif ev in ("tool_not_offered", "blocked_write_tool"):
                out["B_events"] += 1; out["B_req"].add(request)
            elif ev == "final_answer_invalid":
                out["final_invalid"] += 1
            elif ev == "tool_exception" and "multiple repeat" in str(e.get("error")):
                out["G_value_errors"] += 1
        elif k == "tool_end" and isinstance(e.get("output"), str) and "is not a valid tool" in e["output"]:
            out["B_events"] += 1; out["B_req"].add(request)
        elif k == "model_error":
            msg = str(e.get("error"))
            if "XML syntax error" in msg:
                out["E_xml"] += 1; out["E_req"].add(request + 1)
            elif "error parsing tool call" in msg:
                out["E_parse_tool_call"] += 1; out["E_req"].add(request + 1)
            elif "llama-server process has terminated" in msg:
                out["E_other_backend"] += 1   # a backend crash, not a format failure
            else:
                out["E_other_backend"] += 1
        elif k == "final_answer_accepted":
            accepted = True
        elif k == "episode_end":
            answer, error = e.get("answer"), e.get("error")
            if error:
                out["ending"] = "backend_error"
            elif isinstance(answer, str) and answer.strip() == CAP_TEXT:
                out["ending"] = "iteration_cap"
            elif accepted:
                out["ending"] = "final_answer"
            elif isinstance(answer, str) and answer.strip():
                out["ending"] = "text_answer"
                out["text_ending"], out["text_ending_json"] = True, has_json_object(answer)
            else:
                out["ending"] = "empty_message"
                out["empty_req"].add(request)
    return out


def populations():
    p1 = [(r["run_id"], r["model"], r["trace_path"], r.get("supported_complete", PILOT.get(r["run_id"]))) for s, r in C.load_population() if (s, r["arm"]) in C.FULL_TYPE]
    p2 = []
    for label, path, phases in (("render", S / "canonical_render_20261118/RESULTS_LOG_LIVE.jsonl", {"full"}), ("finish_split", S / "finish_split_20261118/RESULTS_LOG.jsonl", {"full"}),
                                ("nudge", S / "repeat_finish_nudge_20261118/RESULTS_LOG.jsonl", {"full"}), ("thinking", HERE / "RESULTS_LOG.jsonl", {"partA", "replA2"})):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            if r.get("arm") in ("FULL", "TH-FULL") and r.get("phase") in phases and r.get("trace_path"):
                p2.append((f"{label}/{r['run_id']}", r["model"], r["trace_path"], r.get("supported_complete")))
    return p1, p2


def summarize(rows):
    by = defaultdict(lambda: Counter())
    for _id, model, trace, supported in rows:
        c = classify(trace)
        for key in (model, "ALL"):
            b = by[key]
            b["episodes"] += 1; b["requests"] += c["requests"]
            for cat, n_key, req_key in (("A", "A_events", "A_req"), ("B", "B_events", "B_req"), ("C", "C_text_calls", "C_req")):
                b[cat + "_events"] += c[n_key]; b[cat + "_episodes"] += c[n_key] > 0; b[cat + "_requests"] += len(c[req_key])
            e_events = c["E_xml"] + c["E_parse_tool_call"]
            b["E_events"] += e_events; b["E_episodes"] += e_events > 0; b["E_xml"] += c["E_xml"]; b["E_parse_tool_call"] += c["E_parse_tool_call"]; b["E_requests"] += len(c["E_req"])
            b["D_text_ending_episodes"] += c["text_ending"]; b["D_text_ending_with_json"] += c["text_ending_json"]
            b["D_text_ending_supported"] += bool(c["text_ending"] and supported); b["D_final_answer_invalid_events"] += c["final_invalid"]
            b["F_" + c["ending"]] += 1
            b["F_empty_message_requests"] += len(c["empty_req"])
            b["G_value_error_events"] += c["G_value_errors"]; b["G_value_error_episodes"] += c["G_value_errors"] > 0
            lost_req = c["A_req"] | c["B_req"] | c["C_req"] | c["E_req"] | c["empty_req"]
            b["lost_requests_A_B_C_E_empty"] += len(lost_req)
            touched = bool(c["A_events"] or c["B_events"] or c["C_text_calls"] or e_events or c["ending"] == "empty_message")
            b["episodes_touched_A_B_C_E_empty"] += touched; b["touched_supported"] += bool(touched and supported)
            b["C_plus_E_parse_text_tool_calls_events"] += c["C_text_calls"] + c["E_parse_tool_call"]
            b["episodes_with_any_format_failure"] += bool(c["A_events"] or c["B_events"] or c["C_text_calls"] or e_events or c["ending"] == "empty_message" or c["text_ending_json"])
            b["episodes_without_answer_from_format"] += c["ending"] in ("backend_error", "empty_message") and (e_events > 0 or c["ending"] == "empty_message")
    return {k: dict(v) for k, v in by.items()}


def main():
    p1, p2 = populations()
    result = dict(P1_candidate_counts_FULL_type=summarize(p1), P2_later_FULL_arms=summarize(p2), P_all=summarize(p1 + p2), populations=dict(P1=len(p1), P2=len(p2)))
    (HERE / "exploratory_format_failures.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result["populations"]))
    for name in ("P1_candidate_counts_FULL_type", "P2_later_FULL_arms", "P_all"):
        print(name, json.dumps(result[name]["ALL"]))


if __name__ == "__main__":
    main()
