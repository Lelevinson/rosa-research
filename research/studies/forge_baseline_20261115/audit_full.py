"""Independent trace/provenance checks; no model, ROS or scoring-rule changes."""
import base64
import hashlib
import importlib.metadata
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main():
    plan = json.loads((HERE / "FULL_PLAN.json").read_text())
    wanted = {(c["model"], c["env"], c["task"], c["seed"]) for cells in plan["sessions"].values() for c in cells}
    rows = [json.loads(line) for line in (HERE / "RESULTS_MATCHED.jsonl").read_text().splitlines()]
    assert (HERE / "RESULTS_LOG.jsonl").read_bytes() == (HERE / "RESULTS_THINKING_ON_SMOKE.jsonl").read_bytes()
    smoke_manifest = json.loads((HERE / "MANIFEST_SMOKE.json").read_text())["sha256"]
    assert hashlib.sha256((HERE / "REPORT_THINKING_ON_SMOKE.md").read_bytes()).hexdigest() == smoke_manifest["REPORT.md"]
    keys = [(r["model"], r["env"], r["task"], r["seed"]) for r in rows]
    assert len(keys) == len(set(keys))
    assert set(keys) <= wanted
    attempts = [json.loads(line) for line in (HERE / "ATTEMPTS_FULL.jsonl").read_text().splitlines()]
    attempt_keys = [(r["cell"]["model"], r["cell"]["env"], r["cell"]["task"], r["cell"]["seed"]) for r in attempts]
    assert len(attempt_keys) == len(set(attempt_keys))
    assert set(keys) <= set(attempt_keys)
    transport = json.loads((HERE / "PILOT_TRANSPORT.json").read_text())
    requests = responses = thinking = compactions = 0
    inline_thinking = scripted_changes = scripted_resets = 0
    issues, first, sessions = [], {}, {}
    usage_missing = []
    file_tool_calls = []
    for row in rows:
        trace = ROOT / row["trace_path"]
        assert hashlib.sha256(trace.read_bytes()).hexdigest() == row["trace_hash"]
        events = [json.loads(line) for line in trace.read_text().splitlines()]
        starts = [e for e in events if e["kind"] == "model_start"]
        ends = [e for e in events if e["kind"] == "model_end"]
        assert len(starts) == row["llm_requests"]
        assert sum(e["usage"]["input_tokens"] for e in ends) == row["input_tokens"]
        assert sum(e["usage"]["output_tokens"] for e in ends) == row["output_tokens"]
        requests += len(starts)
        responses += len(ends)
        thinking += sum(bool(e["message"].get("thinking")) for e in ends)
        inline_thinking += sum("<think>" in (e["message"].get("content") or "") for e in ends)
        scripted_changes += sum(e["kind"] == "scripted_change" for e in events)
        scripted_resets += sum(e["kind"] == "scripted_reset" and e.get("ok") for e in events)
        compactions += sum(e["kind"] == "compaction" for e in events)
        if len(ends) != len(starts):
            usage_missing.append(dict(run_id=row["run_id"], requests=len(starts), usage_records=len(ends)))
        for e in starts:
            body = e["request"]
            assert body["model"] == row["model"]
            assert body["think"] == transport[row["model"]]["think"]
            assert body["options"] == dict(num_ctx=65536, num_predict=4096, temperature=.7, seed=row["seed"])
            assert set(e["changed_fields"]) == {"options", "think"}
            assert len(body["tools"]) == 13
            assert {t["function"]["name"] for t in body["tools"]}.isdisjoint({"ros2_param_set", "ros2_service_call"})
        prompt_file = trace.parents[1] / "prompts.json"
        prompts = json.loads(prompt_file.read_text())
        if starts:
            assert [m["content"] for m in starts[0]["request"]["messages"] if m["role"] == "system"] == [text for _, text in prompts["forge"]]
        for e in events:
            if e["kind"] == "tool_start" and e["name"] == "read_log":
                file_tool_calls.append(dict(run_id=row["run_id"], arguments=e["input"]))
            if e["kind"] == "ros_start":
                assert tuple(e["command"][1:3]) not in {("param", "set"), ("service", "call"), ("topic", "pub")}
            if e["kind"] == "guard_rejection":
                issues.append(dict(run_id=row["run_id"], kind="guard_rejection"))
        check = next((e for e in events if e["kind"] == "first_response_transport_check"), None)
        if check and row["model"] not in first:
            first[row["model"]] = check
        session = trace.parents[1]
        if str(session) not in sessions:
            setup = [json.loads(line) for line in (session / "setup.jsonl").read_text().splitlines()]
            checks = [e for e in setup if e["kind"] == "context_check"]
            assert all(e["ok"] for e in checks)
            oracles = {p.parent.name: json.loads(p.read_text())["mismatches"] for p in session.glob("oracle-*/oracle.json")}
            sessions[str(session.relative_to(ROOT))] = dict(oracles=oracles,
                cleanup_ok=any(e["kind"] == "cleanup_ok" and e.get("ok") for e in setup),
                context_checks=len(checks),
                errors=[e for e in setup if e["kind"] == "session_error"])
    dist = importlib.metadata.distribution("forge-guardrails")
    checked = 0
    for f in dist.files:
        if str(f).startswith("forge/") and str(f).endswith(".py") and f.hash:
            actual = base64.urlsafe_b64encode(hashlib.sha256(dist.locate_file(f).read_bytes()).digest()).decode().rstrip("=")
            assert actual == f.hash.value
            checked += 1
    audit = dict(recorded=len(rows), assigned=len(wanted), complete=set(keys) == wanted, requests=requests,
                 usage_records=responses, returned_thinking_responses=thinking, compactions=compactions,
                 inline_thinking_responses=inline_thinking, scripted_changes=scripted_changes,
                 successful_scripted_resets=scripted_resets,
                 requests_without_usage=usage_missing, first_model_checks=first, sessions=sessions,
                 issues=issues, unchanged_released_python_files=checked,
                 model_attempt_starts=len(attempts), file_tool_calls=file_tool_calls,
                 thinking_on_smoke_rows_excluded=2)
    (HERE / "FULL_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({k: audit[k] for k in ["recorded", "assigned", "complete", "requests", "returned_thinking_responses", "compactions", "unchanged_released_python_files"]}))


if __name__ == "__main__":
    main()
