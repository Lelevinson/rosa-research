"""Offline common-scorer comparison of matched Forge and original pilot cells."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_full as run


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def key(row):
    return tuple(row[k] for k in ("model", "env", "task", "seed"))


def totals(rows):
    return dict(n=len(rows), supported=sum(r["supported_complete"] for r in rows),
                requests=sum(r["llm_requests"] for r in rows), input=sum(r["input_tokens"] for r in rows),
                output=sum(r["output_tokens"] for r in rows), native=sum(r["native_ops"] for r in rows),
                error_episodes=sum(bool(r.get("error") or r.get("worker_error") or r.get("aborts")) for r in rows),
                worker_crashes=sum(str(r.get("worker_error", "")).startswith("worker exit") for r in rows),
                timeouts=sum("timeout" in str([r.get("worker_error"), r.get("error"), r.get("aborts")]).lower() for r in rows),
                iteration_limits=sum("MaxIterationsError" in str(r.get("error")) for r in rows),
                compactions=sum(r.get("compactions", 0) for r in rows))


def historical():
    cache = HERE / "COMPARATORS_V2.json"
    if cache.exists():
        return json.loads(cache.read_text())
    path = HERE.parent / "residual_failures_20261115/scorer_v2.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9"
    spec = importlib.util.spec_from_file_location("common_frozen_scorer", path)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    tasks = {env: {t["id"]: t for t in run.pilot.load_env(env).TASKS} for env in ("stage3", "e1h")}
    result = []
    for original in json.loads((HERE / "FULL_COMPARATORS_SOURCE.json").read_text()):
        trace = run.ROOT / original["trace_path"]
        assert hashlib.sha256(trace.read_bytes()).hexdigest() == original["trace_hash"]
        events = [dict(json.loads(line), line=i) for i, line in enumerate(trace.read_text().splitlines(), 1)]
        score = scorer.score_events(tasks[original["env"]][original["task"]], events)
        result.append(dict(original, **score))
    cache.write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    matched = read_rows(HERE / "RESULTS_MATCHED.jsonl")
    assert len({key(row) for row in matched}) == len(matched), "duplicate matched cell"
    assert all(row["dataset"] == "matched_full" for row in matched)
    controls = historical()
    a1 = {key(row): row for row in controls if row["arm"] == "A1"}
    c1 = {key(row): row for row in controls if row["arm"] == "C1"}
    forge = {key(row): row for row in matched}
    pairs = [dict(cell=cell, A1=a1[key(cell)], C1=c1[key(cell)], Forge=forge.get(key(cell))) for cell in run.PLAN]
    (HERE / "SAME_CELL_COMPARISON.json").write_text(json.dumps(pairs, indent=2) + "\n")
    lines = ["# Same-cell comparison (common scorer v2)", "", "Historical A1/C1; new matched Forge. Thinking-on smoke excluded.", "",
             "| Model | Environment/task/seed | A1 supported / calls | C1 supported / calls | Forge supported / calls |",
             "|---|---|---:|---:|---:|"]
    for p in pairs:
        cell = p["cell"]
        values = [f"{int(p[arm]['supported_complete'])} / {p[arm]['llm_requests']}" if p[arm] else "pending" for arm in ("A1", "C1", "Forge")]
        lines.append(f"| {cell['model']} | {cell['env']}/{cell['task']}/{cell['seed']} | " + " | ".join(values) + " |")
    (HERE / "SAME_CELL_COMPARISON.md").write_text("\n".join(lines) + "\n")
    complete = len(matched) == 80
    report = ["# Forge released baseline: matched pilot comparison", "",
              f"2026-11-15, Asia/Taipei. **{'80/80 assigned episodes completed' if complete else str(len(matched)) + '/80 episodes recorded; run in progress'}.** "
              "Four local models, 10 development tasks and two seeds per model. Synthetic ROS fixtures with real local Ollama inference. "
              "The two thinking-on smoke episodes are a separate record and never enter these totals. "
              "Frozen scores retain the changing-fixture validity defects described below; those affected failures must not be interpreted as model staleness.", "",
              "## Setup and provenance", "",
              "The owner authorized this full matrix after the smoke. [PROTOCOL_FULL.md](PROTOCOL_FULL.md) freezes the preflight, cells, costs and stop rules; "
              "[FULL_PLAN.json](FULL_PLAN.json) lists every cell. PyPI forge-guardrails 0.10.1 executes through its unmodified WorkflowRunner. "
              "The same 12 C1 read tools plus released respond are offered, with required_steps=[], no prerequisites, terminal respond, 40 calls including retries, "
              "release default validation/error/retry/replay behavior, TieredCompact(keep_recent=2), budget 65536. "
              "Forge and C1 exclude write tools from the model menu as a shared safety setting. No per-task route, answer map, repair policy, cache or C1 validator was added.", "",
              "Exact C1 system messages are preserved separately, with only final_answer -> respond, as printed with the complete diff in "
              "[REPORT_THINKING_ON_SMOKE.md](REPORT_THINKING_ON_SMOKE.md). Their JSON-object wording is unchanged despite respond's string argument. "
              "Identical task text is followed by Forge's own messages/nudges. The isolated uv environment, read-only reuse of project ROSA/LangChain dependencies, "
              "versions and import paths remain as documented in SMOKE_PROVENANCE.json; project dependencies and production source were not modified.", "",
              "Ollama: temperature .7, num_ctx 65536, num_predict 4096, assigned seed, explicit per-model think field. "
              "The installed pilot SDK serializes think:false for **all four models, including gpt-oss**. "
              "PILOT_TRANSPORT.json preserves offline SDK serialization of actual historical logical messages/schemas. Historical raw HTTP bodies were not retained; "
              "this is reconstructed wire evidence, not a claimed historical HTTP capture. The matched HTTP wrapper changes only options and the explicit think field, "
              "leaving inherited send, parsing and Forge logic unchanged. Every real request is retained and checked; first-response checks are in TRANSPORT_CHECKS_FULL.jsonl.", "",
              "ROS domain 220, localhost only, unchanged Stage 3/E1h fixtures and scripted change/reset hook, pilot interpreter for fixture nodes, "
              "before/after oracle and cleanup checks. Scripted fixture writes are outside the agent and are identical to the pilot. "
              "90-second HTTP timeout, 900-second episode timeout, 10-hour full-run cap. Per-session freeze.json, driver snapshot, plan, prompts/diff, "
              "source hashes, worker logs and raw traces live under research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/ "
              "and its separately frozen full_20261115T091338Z-resume1/ continuation.", "",
              "Frozen scorer-v2.0 SHA-256 c6b02716152da0258b1296e7e6e0178d966c1c7c425f96e8c3f725bfd62b4ed9 is shared by all arms. "
              "Historical A1/C1 traces were hash-verified and rescored offline; they were not rerun. A1 is the stock executor with the deconflicted A1 prompt, "
              "not unmodified-prompt ROSA. S0 has no pilot data. Source/control hashes and v2 scores are in FULL_COMPARATORS_SOURCE.json and COMPARATORS_V2.json.", "",
              "Menu fairness limit: the original A1 trace offers the full stock menu, including write-tool schemas, while the unchanged native guard blocks writes before ROS. "
              "C1 and Forge offer only the 12 read tools plus their finish tool. Thus A1 is a historical descriptive comparator with a different menu; "
              "C1 is the relevant strong loop comparator with matched read-tool access. No new A1 run or retroactive menu modification was made.", "",
              "## Results", "",
              "All costs below include failed attempts. Native-operation counts cover agent command starts; fixture setup, oracle and scripted changes are logged separately. "
              "Token totals are reported input plus output. No thinking-on smoke row is included. "
              "Forge has usage for 641 of 643 requests: two recovered HTTP 500 parser errors omit usage, so its token totals exclude unknown work and are lower bounds. "
              "The raw errors are lfm3 u3 seed 1 L41 (unexpected XML EOF) and resumed gpt-oss e1h_amb_1 seed 2 L50 (invalid tool-call JSON). "
              "Neither episode was rerun. TOKEN_USAGE_COVERAGE.json confirms historical A1 472/472 and C1 486/486 requests have usage.", "",
              "| Model | Arm | Recorded / assigned | Supported-complete | LLM requests | Reported input tokens | Reported output tokens | Reported total tokens | Native ops | Error episodes | Timeouts | Compactions |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    summary = {}
    for model in run.FROZEN_PLAN["models"]:
        summary[model] = {}
        for arm, source in [("A1", controls), ("C1", controls), ("Forge", matched)]:
            subset = [r for r in source if r["model"] == model and r["arm"] == arm]
            t = totals(subset)
            summary[model][arm] = t
            report.append(f"| {model} | {arm} | {t['n']}/20 | {t['supported']} | {t['requests']} | {t['input']} | {t['output']} | {t['input']+t['output']} | {t['native']} | {t['error_episodes']} | {t['timeouts']} | {t['compactions'] if arm=='Forge' else 'n/a'} |")
    forge_total, c1_total, a1_total = totals(matched), totals([r for r in controls if r["arm"] == "C1"]), totals([r for r in controls if r["arm"] == "A1"])
    report += ["", f"Descriptive totals over recorded cells: Forge {forge_total['supported']}/{forge_total['n']} supported-complete, "
               f"{forge_total['requests']} requests, {forge_total['input']+forge_total['output']} tokens and {forge_total['native']} native operations. "
               f"Historical C1: {c1_total['supported']}/{c1_total['n']}, {c1_total['requests']} requests, {c1_total['input']+c1_total['output']} tokens and {c1_total['native']} native operations. "
               f"Historical A1: {a1_total['supported']}/{a1_total['n']}, {a1_total['requests']} requests, {a1_total['input']+a1_total['output']} tokens and {a1_total['native']} native operations. "
               "These are frozen-label observations with the validity qualifications below, not a causal or novelty verdict.", "",
               "'Error episodes' counts recorded episode errors/worker errors (or original pilot aborts), including timeouts and budget exhaustion; "
               "it is not a claim that each is a Python process crash. See the per-attempt ledger for exact causes. "
               "Historical timeout classifications in original abort lists are preserved rather than inferred from an empty new-run error field. "
               f"New Forge worker crashes: {sum(t['Forge']['worker_crashes'] for t in summary.values())}; "
               f"iteration-limit errors: {sum(t['Forge']['iteration_limits'] for t in summary.values())}. "
               "If a backend failure provides no usage, token totals include only reported usage, not an estimate of unobserved generation.", "",
               "## Same-cell comparison", "",
               "[All 80 cell rows](SAME_CELL_COMPARISON.md), with raw sources and full costs in [SAME_CELL_COMPARISON.json](SAME_CELL_COMPARISON.json). "
               "The following discordances use only cells with a recorded Forge attempt:", "",
               "| Model | Comparator | Both supported | Only Forge supported | Only comparator supported | Neither supported |",
               "|---|---|---:|---:|---:|---:|"]
    for model in run.FROZEN_PLAN["models"]:
        for arm in ("A1", "C1"):
            cells = [p for p in pairs if p["cell"]["model"] == model and p["Forge"]]
            counts = [sum(bool(p["Forge"]["supported_complete"]) == f and bool(p[arm]["supported_complete"]) == c for p in cells) for f,c in [(True,True),(True,False),(False,True),(False,False)]]
            report.append(f"| {model} | {arm} | " + " | ".join(map(str, counts)) + " |")
    report += ["", "A hand-read disagreement in Forge's favor: matched thinking-off lfm3 p3 seed 2 "
               "(`lfm3_1.7b-stage3/005-p3-Forge-s2/trace.jsonl`) reads the two links at L25/L34 and the correct setpoint at L52, "
               "then submits the correct object at L62. Historical same-cell C1 is unsupported because its first-node assignment is wrong. "
               "This is a descriptive cell disagreement, not evidence that thinking is necessary or that Forge caused the improvement.", "",
               "## Transport checks", "", "| Model | First HTTP status | First live wire think | Matches reconstructed pilot | First response has no thinking |",
               "|---|---|---|---|---|"]
    checks = read_rows(HERE / "TRANSPORT_CHECKS_FULL.jsonl")
    for model in run.FROZEN_PLAN["models"]:
        first = next((c for c in checks if c["model"] == model), None)
        report.append(f"| {model} | {first['http_status'] if first else 'pending'} | {str(first['wire_think']).lower() if first else 'pending'} | {first['think_matches_pilot'] if first else 'pending'} | {first['no_thinking_observed'] if first and first['http_status']==200 else 'not verified'} |")
    report += ["", "Historical raw thinking was not saved. With reasoning=False the pilot's LangChain adapter does not retain returned thinking in additional_kwargs. "
               "Thus absence in historical message logs does not establish wire absence. Current raw responses are retained without removing thinking; the table reports what was actually observed. "
               "gpt-oss returns raw thinking despite the matched think:false field. PILOT_THINKING_VISIBILITY_CHECK.json demonstrates offline, with no model inference, "
               "that the pilot SDK drops a mock raw thinking payload while retaining the answer and token usage. This explains historical invisibility, "
               "but does not recover historical raw responses. No per-model think value was invented, no raw output was suppressed, and no thinking ablation was run.", "",
               "FULL_AUDIT.json independently checks cell uniqueness, raw trace hashes, every wire option/think field, initial system messages, costs, "
               "token-usage coverage, loaded context, agent writes, fixture changes/resets, and oracle/cleanup records. It also verifies all 52 installed Forge Python files "
               "against the wheel RECORD and verifies that the thinking-on smoke report and ledger remain unchanged.", "",
               "## Hand-read Forge failures", ""]
    hand = HERE / "HAND_READ_FAILURES.md"
    report.append(hand.read_text() if hand.exists() else "Pending inspection after the run; no failure causes inferred from automatic labels alone.")
    report += ["", "## Orchestration recovery and fixture validity", "",
               "After 53 recorded cells, a parent-driver check stopped the matrix following a safely rejected malformed read in "
               "gpt-oss e1h_amb_2 seed 1. Forge had already recovered and returned a supported answer. The native guard blocked the malformed command; "
               "no unsafe native operation executed. Only the parent orchestration was corrected to log rejections without aborting independent later cells. "
               "The remaining 27 cells resumed in their original order with fresh fixture/oracle checks under the original 10-hour cap. "
               "RESUME_ORCHESTRATION_AUDIT.json proves that episode, client, tool dispatch, prompt and scoring definitions did not change. "
               "No completed model cell was rerun or excluded. All owned nodes from the interrupted session were cleaned up, but its post-oracle was not performed; "
               "that gap remains in the original evidence.", "",
               "FIXTURE_EVENT_AUDIT.json separately audits the changing-task traces for all three arms. "
               "The unchanged EpisodeHook watches an exact absolute ROS command. In gpt-oss Forge e1h_chg_1 seed 2 "
               "(`gpt-oss_20b-e1h/050-e1h_chg_1-Forge-s2/trace.jsonl`), valid relative-name reads at L9–10 and L27–28 "
               "observe level 30 both times; the scripted change to 45 never fires. L36 reports final_level=30, which matches its last native read, "
               "but the frozen scorer expects 45 and marks failure. This is a fixture scheduling validity issue, not evidence of a stale cached value. "
               "The same missed-trigger pattern also exists in historical A1 gpt-oss e1h_chg_2 seed 2 and A1 bonsai e1h_chg_1 seed 2; "
               "the audit checks the strong C1 controls too. Frozen scores and assigned denominators are retained unchanged. "
               "No corrected success count, post-hoc exclusion, hook repair or replacement run is substituted for those data.", ""]
    fixture_audit = HERE / "FIXTURE_EVENT_AUDIT.json"
    if fixture_audit.exists():
        validity = json.loads(fixture_audit.read_text())
        report += ["| Arm | Audited changing cells | Trigger fired | Valid relative read but trigger missed | Other missing triggers |",
                   "|---|---:|---:|---:|---:|"]
        for arm in ("A1", "C1", "Forge"):
            entries = [r for r in validity if r["arm"] == arm]
            fired = sum(r["status"] == "trigger_fired" for r in entries)
            relative = sum(r["status"] == "missed_trigger_on_valid_relative_read" for r in entries)
            report.append(f"| {arm} | {len(entries)} | {fired} | {relative} | {len(entries)-fired-relative} |")
    report += ["", "## What this comparison can and cannot show", "",
               "The comparison measures complete supported answers and costs on exactly the pilot development cells, using a common scorer and preserved failure denominators. "
               "It does not establish novelty, cross-application generalization, statistical significance, equivalence or universal superiority. "
               "Controls are historical, not concurrent; two seeds, shared fixture structure, model/runtime variability and nonidentical finish-tool schemas remain limitations. "
               "The pilot SDK streams internally whereas the released Forge send path buffers a response; wire serialization and timeout semantics are therefore not identical even with matched sampling and nominal timeout. "
               "Bonsai and Qwen share a model family. A higher success count alone does not establish lower cost. "
               "Native reads and observed tool outputs, rather than a requested call alone, support the scoring.", "",
               "## Open questions (not acted on)", "",
               "Thinking-on Forge solved the smoke p3 cell where historical thinking-off C1 failed. "
               "The owner suggests a separate thinking-on versus thinking-off test later. That observation confounds reasoning setting, session and stochastic generation; "
               "it is not causal evidence for either thinking or Forge. The authorized matched matrix also contains a thinking-off success on p3 seed 2, "
               "so the smoke alone does not establish a thinking benefit. No separate thinking test, prompt tuning or mechanism change was performed.", "",
               "## Code and data flow", "",
               "prepare_full.py extracts valid historical C1 cells and reconstructs the pilot SDK transport without inference. "
               "run_full.py:MatchedTransport injects the explicit think field while PilotOptionsClient changes options only. "
               "episode runs released WorkflowRunner on the ordinary tool callables, logs requests/results/compaction, and manages the unchanged E1h episode hook. "
               "session owns fixture/oracle/context/cleanup; append_result scores and appends every attempt to RESULTS_MATCHED.jsonl. "
               "report_full.py rescored the controls, joins identical model/environment/task/seed cells, and generates this report. "
               "ATTEMPTS_FULL.jsonl preserves starts; RESULTS_MATCHED.jsonl preserves outcomes and trace hashes. "
               "The original smoke reports, logs, source and failed setup sessions remain separate and unchanged.", "",
               "Executed command from the repository root (historical paths retained; not an instruction to overwrite this completed run):", "",
               "```bash\nUV_CACHE_DIR=/tmp/rosa-forge-uv-cache \\\nROS_DOMAIN_ID=220 ROS_LOCALHOST_ONLY=1 \\\nROS_HOME=/tmp/rosa-forge-ros-home ROS_LOG_DIR=/tmp/rosa-forge-ros-logs \\\nuv run --no-project --python /tmp/rosa-forge-env-20261115/bin/python \\\n  python research/studies/forge_baseline_20261115/run_full.py full \\\n  research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z\n```", "",
               "The continuation used the same environment and command with mode `resume` and output suffix `-resume1`. "
               "`uv run` executes with uv; `--no-project` avoids syncing the project environment, and `--python` selects the isolated interpreter. "
               "The ROS variables select the disposable domain, localhost discovery and temporary log locations. "
               "A new reproduction needs fresh output and ledger locations; the driver refuses to rerun already-recorded cells in full mode.", ""]
    (HERE / "REPORT.md").write_text("\n".join(report))
    (HERE / "FULL_SUMMARY.json").write_text(json.dumps(dict(completed=len(matched), assigned=80, models=summary), indent=2) + "\n")
    print(json.dumps(dict(completed=len(matched), assigned=80, models={m: summary[m]["Forge"] for m in summary})))


if __name__ == "__main__":
    main()
