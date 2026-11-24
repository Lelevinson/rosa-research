"""Fault-injection tests of queue_core_rev2.py (compact-row crash window, torn lines, interrupted attempts, integrity stops). Dummy system only: no GPU, no model, no ROS.
  uv run --no-sync python -m unittest discover -s research/studies/final_exam_draft_20261118/exam_queue/tests_rev2 -v      (about 1-2 minutes)
Every test runs the 12-cell dummy queue in a subprocess, kills it (SIGKILL of itself) at one boundary, restarts it until it finishes, then audits the logs:
 no lost cell, no duplicate full or compact row, no wrongly skipped cell, the compact table joins the full log one to one, a further restart changes nothing byte for byte."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE.parent
CONFIG = tempfile.mkdtemp(prefix="rosa-rev2-config-")
os.environ["ROSA_EXAM_CONFIG_DIR"] = CONFIG
sys.path.insert(0, str(QUEUE))
import queue_core_rev2 as Q  # noqa: E402

SPEC = HERE / "rev2_spec.json"
PLANNED = [c["id"] for c in Q.build_cells(Q.load_spec(SPEC))]
opaque = lambda text: hashlib.sha256(("unsalted" + text).encode()).hexdigest()[:12]
jsonl = lambda p: [json.loads(l) for l in Path(p).read_text().splitlines() if l.strip()] if Path(p).exists() else []


class Harness:
    def __init__(self, name):
        self.name = name
        self.root = Path(tempfile.mkdtemp(prefix=f"rosa-rev2-{name}-"))
        self.art, self.cmp = self.root / "artifacts" / name, self.root / "compact" / name

    def env(self, extra=None):
        return {**os.environ, "ROSA_REV2_ARTIFACTS": str(self.root), "ROSA_EXAM_CONFIG_DIR": CONFIG, "ROSA_EXAM_NOTIFY_DRY": str(self.root / "notify_dry.log"), "ROS_DOMAIN_ID": "77",
                "DUMMY_FAULT_DIR": str(self.root / "faults"), "ROSA_FAULT_DIR": str(self.root / "faults"), "DUMMY_DELAY_SECONDS": "0.2", **(extra or {})}

    spec = SPEC

    def run(self, extra=None, command="run"):
        args = [sys.executable, str(HERE / "run_rev2.py"), command, "--spec", str(self.spec), "--run-name", self.name, "--machine", "all", "--machines", "all:1"]
        if command == "run":
            args.append("--dummy")
        p = subprocess.run(args, env=self.env(extra), capture_output=True, text=True, timeout=240, start_new_session=True)
        return p.returncode, p.stdout + p.stderr

    def finish(self, extra=None, max_runs=5):
        """Run (with the fault), restart until the queue exits 0. Returns the list of (code, output)."""
        outcomes = []
        for _ in range(max_runs):
            outcomes.append(self.run(extra))
            if outcomes[-1][0] == 0:
                break
        return outcomes

    def snapshot(self):
        return {p.name: p.read_bytes() for d in (self.art, self.cmp) for p in sorted(d.glob("*.jsonl"))}

    def audit(self, test, expect_starts=None):
        full, compact = jsonl(self.art / "RESULTS_LOG_all.jsonl"), jsonl(self.cmp / "compact_all.jsonl")
        test.assertEqual(sorted(r["cell_id"] for r in full), sorted(PLANNED), "a cell is lost, duplicated or unplanned in the full log")
        test.assertEqual(sorted(r["cell"] for r in compact), sorted(opaque(i) for i in PLANNED), "compact table does not join the full log one to one")
        starts = [r["cell_id"] for r in jsonl(self.art / "STARTS_all.jsonl") if r["event"] == "start"]
        counts = {i: starts.count(i) for i in PLANNED}
        if expect_starts is not None:
            test.assertEqual({i: n for i, n in counts.items() if n != 1}, expect_starts)
        before = self.snapshot()                                   # a further restart must change nothing
        code, out = self.run()
        test.assertEqual(code, 0, out[-400:])
        test.assertEqual(self.snapshot(), before, "a restart after completion changed a log")
        code, out = self.run(command="merge-check")
        test.assertEqual(code, 0, out[-600:])
        return full, compact, counts


def cell(task, system, model):
    return next(i for i in PLANNED if f"|{task}|{system}|{model}|" in i)


class WriteBoundaryTests(unittest.TestCase):
    def check(self, fault, n=3, expect_starts=None, expect_torn=False, extra=None):
        h = Harness(f"b_{fault}")
        outcomes = h.finish({"ROSA_FAULT": fault, "ROSA_FAULT_N": str(n), **(extra or {})})
        h.audit(self, expect_starts)
        torn = list(h.art.glob("*.torn_*")) + list(h.cmp.glob("*.torn_*"))
        self.assertEqual(bool(torn), expect_torn, torn)
        return h, outcomes

    def test_a_crash_before_the_full_row_is_written_logs_it_from_the_trace_without_a_rerun(self):
        h, outcomes = self.check("full_before")
        self.assertEqual(len(outcomes), 2)                                           # killed once, then completed
        self.assertEqual(jsonl(h.art / "INTERRUPTED_all.jsonl"), [])                  # the attempt line exists: not an interrupted attempt

    def test_a_crash_after_the_full_row_and_before_the_compact_row_rebuilds_the_compact_row(self):
        h, outcomes = self.check("full_after")
        self.assertEqual(len(outcomes), 2)
        self.assertIn('"compact_rows_rebuilt": 1', outcomes[1][1])

    def test_a_torn_full_row_is_kept_as_evidence_and_the_cell_is_logged_again_from_its_trace(self):
        self.check("full_torn", expect_torn=True)

    def test_a_crash_before_the_compact_row(self):
        self.check("compact_before")

    def test_a_torn_compact_row_is_kept_as_evidence_and_rebuilt(self):
        self.check("compact_torn", expect_torn=True)

    def test_a_crash_after_the_compact_row_needs_no_repair(self):
        h, outcomes = self.check("compact_after")
        self.assertIn('"compact_rows_rebuilt": 0', outcomes[1][1])

    def test_a_failing_compact_write_in_a_live_runner_never_adds_a_second_full_row(self):
        h, outcomes = self.check("compact_raise")
        self.assertEqual(len(outcomes), 1)                                           # no crash: the live runner repaired it itself before the next dispatch
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 12)

    def test_the_fault_at_the_first_and_at_the_last_cell(self):
        for fault in ("full_after", "full_before"):
            for n in (1, 12):
                with self.subTest(fault=fault, n=n):
                    h = Harness(f"edge_{fault}_{n}")
                    h.finish({"ROSA_FAULT": fault, "ROSA_FAULT_N": str(n)})
                    h.audit(self)


class InterruptedAttemptTests(unittest.TestCase):
    def test_killed_during_the_episode_no_episode_end_runs_the_cell_once_more_and_records_it(self):
        target = cell("t2", "M", "m1")
        h = Harness("i_during")
        h.finish({"DUMMY_FAULT": "during_episode", "DUMMY_FAULT_CELL": target})
        full, compact, counts = h.audit(self, expect_starts={target: 2})
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl") if e["event"] == "interrupted"]
        self.assertEqual(len(ledger), 1)
        self.assertEqual((ledger[0]["cell_id"], ledger[0]["requests_seen"] > 0, ledger[0]["trace_had_episode_end"]), (target, True, False))

    def test_terminal_trace_without_attempt_line_is_also_interrupted_and_runs_once_more(self):
        """The case Codex found: episode_end exists, but there is no attempt line, ending marker or result row."""
        target = cell("t3", "E1", "m2")
        h = Harness("i_terminal")
        h.finish({"DUMMY_FAULT": "after_worker_before_attempt", "DUMMY_FAULT_CELL": target})
        h.audit(self, expect_starts={target: 2})
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl") if e["event"] == "interrupted"]
        self.assertEqual(len(ledger), 1)
        self.assertEqual((ledger[0]["requests_seen"] > 0, ledger[0]["trace_had_episode_end"]), (True, True))   # the decision does not depend on this flag, it is only recorded

    def test_the_discarded_attempt_stays_on_disk_and_never_becomes_a_result(self):
        target = cell("t1", "M", "m2")
        h = Harness("i_kept")
        h.finish({"DUMMY_FAULT": "after_worker_before_attempt", "DUMMY_FAULT_CELL": target})
        full, compact, counts = h.audit(self)
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl") if e["event"] == "interrupted"]
        discarded = h.art / "runs_all" / ledger[0]["run_id"]
        self.assertTrue((discarded / "trace.jsonl").exists())
        self.assertNotIn(ledger[0]["run_id"], {r["run_id"] for r in full})

    def test_an_interruption_before_any_model_request_is_charged_from_the_ledger_and_the_cell_runs_again(self):
        target = cell("t2", "E1", "m1")
        h = Harness("i_zero")
        h.finish({"DUMMY_FAULT": "before_model", "DUMMY_FAULT_CELL": target})
        h.audit(self, expect_starts={target: 2})
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl") if e["event"] == "interrupted"]
        self.assertEqual([e["requests_seen"] for e in ledger], [0])
        failures_file = h.art / "failures_all.json"
        self.assertFalse(failures_file.exists() and target in json.loads(failures_file.read_text())["cells"])   # charged from the ledger (derived, idempotent), not by the in-place counter

    def test_a_second_interrupted_attempt_with_model_requests_quarantines_the_cell(self):
        target = cell("t2", "M", "m1")
        h = Harness("i_twice")
        outcomes = h.finish({"DUMMY_FAULT": "during_episode", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_TIMES": "2"})
        self.assertEqual(outcomes[-1][0], 0)
        ids = [r["cell_id"] for r in jsonl(h.art / "RESULTS_LOG_all.jsonl")]
        self.assertEqual(sorted(ids), sorted(i for i in PLANNED if i != target))      # 11 results, the quarantined cell is reported as missing, not dropped silently
        ledger = jsonl(h.art / "INTERRUPTED_all.jsonl")
        self.assertEqual([e["event"] for e in ledger], ["interrupted", "interrupted", "quarantined"])
        status = json.loads((h.art / "status_all.json").read_text())
        self.assertEqual((status["state"], status["skipped"], status["interrupted_attempts"]), ("finished_with_skips", 1, 2))
        starts = [r["cell_id"] for r in jsonl(h.art / "STARTS_all.jsonl") if r["event"] == "start"]
        self.assertEqual(starts.count(target), 2)                                       # never started a third time


class IntegrityStopTests(unittest.TestCase):
    def finished(self, name):
        h = Harness(name)
        self.assertEqual(h.run()[0], 0)
        return h

    def test_conflicting_duplicate_full_rows_stop_the_run(self):
        h = self.finished("x_conflict")
        rows = jsonl(h.art / "RESULTS_LOG_all.jsonl")
        bad = dict(rows[0], supported_complete=not rows[0]["supported_complete"])
        with (h.art / "RESULTS_LOG_all.jsonl").open("a") as f:
            f.write(json.dumps(bad) + "\n")
        code, out = h.run()
        self.assertNotEqual(code, 0)
        self.assertIn("conflicting duplicate", out)

    def test_agreeing_duplicates_are_counted_and_merge_check_needs_them_in_the_accepted_list(self):
        h = self.finished("x_agree")
        rows = jsonl(h.art / "RESULTS_LOG_all.jsonl")
        with (h.art / "RESULTS_LOG_all.jsonl").open("a") as f:
            f.write(json.dumps(dict(rows[0], logged_at="2000-01-01T00:00:00+0000")) + "\n")
        code, out = h.run()
        self.assertEqual(code, 0, out[-300:])
        self.assertIn('"duplicate_full_rows_agreeing": 1', out)
        self.assertNotEqual(h.run(command="merge-check")[0], 0)                          # an unlisted duplicate is reported and fails the audit
        (h.art / "ACCEPTED_DUPLICATES.json").write_text(json.dumps([rows[0]["cell_id"]]))
        self.assertEqual(h.run(command="merge-check")[0], 0)

    def test_a_broken_line_in_the_middle_stops_the_run_and_changes_nothing(self):
        h = self.finished("x_middle")
        path = h.art / "RESULTS_LOG_all.jsonl"
        lines = path.read_text().splitlines()
        lines[3] = lines[3][:20]
        path.write_text("\n".join(lines) + "\n")
        before = path.read_bytes()
        code, out = h.run()
        self.assertNotEqual(code, 0)
        self.assertIn("not valid JSON", out)
        self.assertEqual(path.read_bytes(), before)

    def test_a_compact_row_without_a_full_row_stops_the_run(self):
        h = self.finished("x_orphan_compact")
        with (h.cmp / "compact_all.jsonl").open("a") as f:
            f.write(json.dumps(dict(jsonl(h.cmp / "compact_all.jsonl")[0], cell="000000000000")) + "\n")
        code, out = h.run()
        self.assertNotEqual(code, 0)
        self.assertIn("without a full row", out)

    def test_a_compact_row_that_differs_from_its_full_row_stops_the_run(self):
        h = self.finished("x_differs")
        rows = jsonl(h.cmp / "compact_all.jsonl")
        rows[0]["supported"] = not rows[0]["supported"]
        (h.cmp / "compact_all.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
        code, out = h.run()
        self.assertNotEqual(code, 0)
        self.assertIn("differs from the compact row rebuilt", out)

    def test_a_torn_last_line_that_is_complete_json_keeps_the_record(self):
        h = self.finished("x_newline")
        path = h.art / "RESULTS_LOG_all.jsonl"
        path.write_bytes(path.read_bytes().rstrip(b"\n"))
        code, out = h.run()
        self.assertEqual(code, 0, out[-300:])
        self.assertEqual(len(jsonl(path)), 12)
        self.assertTrue(path.read_bytes().endswith(b"\n"))


class IntegrityLookTests(unittest.TestCase):
    def look(self, h):
        p = subprocess.run([sys.executable, str(QUEUE / "integrity_look.py"), "--spec", str(SPEC), "--run-name", h.name, "--artifacts", str(h.root / "artifacts"), "--compact", str(h.root / "compact")],
                           env=h.env(), capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        return p.stdout, json.loads(p.stdout)["tiers"]["tier1"]

    def test_complete_tier_is_reported_as_analysable_and_no_outcome_field_is_printed(self):
        h = Harness("l_complete")
        self.assertEqual(h.run()[0], 0)
        text, info = self.look(h)
        self.assertTrue(info["COMPLETE"])
        self.assertEqual((info["planned"], info["done"]), (12, 12))
        for forbidden in ("supported", "input_tokens", "output_tokens", "requests", "\"answer\""):
            self.assertNotIn(forbidden, text)

    def test_incomplete_tier_says_x_of_y_and_is_not_complete(self):
        h = Harness("l_partial")
        h.run({"ROSA_FAULT": "full_before", "ROSA_FAULT_N": "6"})                       # killed after 5 results
        text, info = self.look(h)
        self.assertFalse(info["COMPLETE"])
        self.assertEqual(info["report_as"], "5 of 12 cells done; no comparison")

    def test_a_quarantined_cell_keeps_the_tier_incomplete(self):
        target = cell("t2", "M", "m1")
        h = Harness("l_quarantine")
        h.finish({"DUMMY_FAULT": "during_episode", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_TIMES": "2"})
        text, info = self.look(h)
        self.assertEqual((info["done"], info["quarantined_cells"], info["COMPLETE"], info["ledger_attempts_that_reached_the_model"]), (11, 1, False, 2))


SMALL = HERE / "rev2_spec_small.json"
ROS_ENV = {"ROS_LOCALHOST_ONLY": "1", "DUMMY_ROS": "1", "ROSA_QUEUE_DAEMON_CLEANUP": "1"}


def ros_run(args, domain="77", extra_env=None):
    return subprocess.run(["ros2", *args], env={**os.environ, "ROS_DOMAIN_ID": domain, "ROS_LOCALHOST_ONLY": "1", **(extra_env or {})}, capture_output=True, text=True, timeout=60)


def stop_daemon(domain="77"):
    ros_run(["daemon", "stop"], domain)            # test-side cleanup only (the queue itself never uses this RPC)


def any_daemon_pids(domain):
    """Every ROS discovery daemon of a domain, owned or not (what a static fixture's strict graph check would trip over)."""
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
            environ = (entry / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        if cmdline.startswith(("/usr/bin/python", "python")) and "ros2cli.daemon.daemonize" in cmdline and f"ROS_DOMAIN_ID={domain}".encode() in environ:
            found.append(int(entry.name))
    return sorted(found)


def owned_daemon_pids(domain, run_name, home=None):
    return Q.run_daemon_pids(domain, home, f"{run_name}/all")


def static_fixture_starts(domain="77"):
    """What the real static fixture needs: no discovery daemon node in the graph (hidden nodes included), then a node can be created."""
    graph = ros_run(["node", "list", "-a", "--no-daemon", "--spin-time", "3"], domain).stdout
    if any(line.startswith("/_ros2cli_daemon") for line in graph.splitlines()):
        return False
    probe = subprocess.run([sys.executable, "-c", "import rclpy; rclpy.init(); n = rclpy.create_node('static_probe'); n.destroy_node(); rclpy.shutdown()"],
                           env={**os.environ, "ROS_DOMAIN_ID": domain, "ROS_LOCALHOST_ONLY": "1"}, capture_output=True, text=True, timeout=60)
    return probe.returncode == 0


class DaemonTests(unittest.TestCase):
    """Blocker 1 and its hardening. Test domains 77 and 78 only (never 219), localhost only, dummy system whose worker starts the discovery daemon like the agent's tools do."""
    def setUp(self):
        self.addCleanup(stop_daemon, "77")
        self.addCleanup(stop_daemon, "78")
        stop_daemon("77")
        stop_daemon("78")

    def test_rev2_stops_the_daemon_after_every_episode_and_a_static_fixture_starts_afterwards(self):
        h = Harness("d_between")
        h.spec = SMALL
        code, out = h.run(ROS_ENV)
        self.assertEqual(code, 0, out[-400:])
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 2)               # the second episode's strict start check saw an empty graph
        self.assertEqual(any_daemon_pids("77"), [])
        self.assertTrue(static_fixture_starts("77"))

    def test_control_the_frozen_queue_leaves_the_daemon_and_the_second_episode_fails_without_any_crash(self):
        h = Harness("d_frozen")
        h.spec = SMALL
        code, out = h.run({**ROS_ENV, "ROSA_QUEUE_MODULE": "queue_core"})
        self.assertLess(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 2, "the frozen path should have failed the second episode")
        self.assertTrue(any_daemon_pids("77"), "the frozen path should have left the daemon")
        self.assertFalse(static_fixture_starts("77"))

    def test_resume_cleanup_stops_an_owned_daemon_that_survived_a_crash(self):
        ros_run(["node", "list"], extra_env={"ROSA_EXAM_RUN": "d_resume/all"})            # a daemon of the same run name, as left by a killed run
        self.assertTrue(owned_daemon_pids("77", "d_resume"))
        h = Harness("d_resume")
        h.spec = SMALL
        code, out = h.run(ROS_ENV)
        self.assertEqual(code, 0, out[-400:])
        self.assertIn('"discovery_daemons_stopped": 1', out)
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 2)
        self.assertEqual(any_daemon_pids("77"), [])

    def test_a_daemon_of_another_domain_is_never_touched(self):
        ros_run(["node", "list"], "78", {"ROSA_EXAM_RUN": "d_scope/all"})
        other = any_daemon_pids("78")
        self.assertTrue(other)
        h = Harness("d_scope")
        h.spec = SMALL
        self.assertEqual(h.run(ROS_ENV)[0], 0)
        self.assertEqual(any_daemon_pids("78"), other)

    def test_only_positively_owned_daemons_are_signalled_and_no_domain_wide_rpc_is_used(self):
        from unittest import mock
        home = tempfile.mkdtemp()
        cases = {"no marker": {}, "marker of another run name": {"ROSA_EXAM_RUN": "someone_else/all"}, "right marker, other ROS_HOME": {"ROSA_EXAM_RUN": "u/all", "ROS_HOME": "/tmp/other_home"}}
        for label, extra in cases.items():
            with self.subTest(label):
                stop_daemon("77")
                ros_run(["node", "list"], extra_env=extra)
                pids = any_daemon_pids("77")
                self.assertTrue(pids)
                with mock.patch.dict(os.environ, {"ROS_DOMAIN_ID": "77", "ROSA_EXAM_RUN": "u/all", "ROS_HOME": home}), \
                        mock.patch("subprocess.run", side_effect=AssertionError("the queue must not call any ros2 command to stop the daemon")):
                    self.assertEqual(Q.stop_run_daemon(), ([], []))
                self.assertEqual(any_daemon_pids("77"), pids)                              # untouched
        stop_daemon("77")
        ros_run(["node", "list"], extra_env={"ROSA_EXAM_RUN": "u/all", "ROS_HOME": home})   # the owned one: stopped by PID, with subprocess.run forbidden
        owned = any_daemon_pids("77")
        with mock.patch.dict(os.environ, {"ROS_DOMAIN_ID": "77", "ROSA_EXAM_RUN": "u/all", "ROS_HOME": home}), \
                mock.patch("subprocess.run", side_effect=AssertionError("the queue must not call any ros2 command to stop the daemon")):
            found, left = Q.stop_run_daemon()
        self.assertEqual((found, left), (owned, []))
        self.assertEqual(any_daemon_pids("77"), [])

    def test_without_a_run_marker_or_domain_nothing_is_matched(self):
        ros_run(["node", "list"], extra_env={"ROSA_EXAM_RUN": "u/all"})
        self.assertEqual(Q.run_daemon_pids("77", None, None), [])
        self.assertEqual(Q.run_daemon_pids(None, None, "u/all"), [])
        self.assertTrue(Q.run_daemon_pids("77", None, "u/all"))

    def test_a_surviving_owned_daemon_blocks_the_next_dispatch_and_the_run_never_ends_as_finished(self):
        h = Harness("d_survivor")
        h.spec = SMALL
        code, out = h.run({**ROS_ENV, "ROSA_FAULT_DAEMON_SURVIVES": "1"})
        self.assertEqual(code, 5, out[-500:])
        self.assertIn("still alive after TERM and KILL", out)
        status = json.loads((h.art / "status_all.json").read_text())
        self.assertEqual(status["state"], "integrity_error")
        self.assertNotEqual(status["state"], "finished")
        starts = [r for r in jsonl(h.art / "STARTS_all.jsonl") if r["event"] == "start"]
        self.assertEqual(len(starts), 1)                                                   # the second episode was never dispatched
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 1)                   # the first result is kept
        self.assertTrue(owned_daemon_pids("77", "d_survivor"))
        code, out = h.run(ROS_ENV)                                                         # the fault is gone: the start-up cleanup stops it by PID and the run finishes
        self.assertEqual(code, 0, out[-400:])
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 2)
        self.assertEqual(any_daemon_pids("77"), [])

    def test_a_survivor_at_start_up_blocks_before_any_dispatch(self):
        ros_run(["node", "list"], extra_env={"ROSA_EXAM_RUN": "d_start/all"})
        h = Harness("d_start")
        h.spec = SMALL
        code, out = h.run({**ROS_ENV, "ROSA_FAULT_DAEMON_SURVIVES": "1"})
        self.assertEqual(code, 5, out[-500:])
        self.assertEqual(json.loads((h.art / "status_all.json").read_text())["state"], "integrity_error")
        self.assertEqual([r for r in jsonl(h.art / "STARTS_all.jsonl") if r["event"] == "start"], [])
        self.assertEqual(jsonl(h.art / "RESULTS_LOG_all.jsonl"), [])


class LegacyRecordTests(unittest.TestCase):
    """Blocker 2: the two pre-start cells have full records without model and seed (four records, duplicates), and compact rows that were rebuilt later."""
    def legacy(self, name, mutate=None):
        h = Harness(name)
        self.assertEqual(h.run()[0], 0)
        path = h.art / "RESULTS_LOG_all.jsonl"
        rows = jsonl(path)
        legacy = []
        for row in rows[:2]:
            old = {k: v for k, v in row.items() if k not in ("model", "seed")}
            legacy += [old, dict(old, logged_at="2000-01-01T00:00:00+0000", gpu_state={"state": "ok", "samples": 9})]   # a duplicate that differs only in time and GPU metadata
        if mutate:
            mutate(legacy)
        lines = [json.dumps(r) for r in legacy] + [json.dumps(r) for r in rows[2:]]
        path.write_text("\n".join(lines) + "\n")
        return h, [json.dumps(r) for r in legacy]

    def test_both_legacy_cells_are_carried_forward_without_keyerror_and_nothing_is_rewritten(self):
        h, legacy_lines = self.legacy("g_ok")
        before_compact = (h.cmp / "compact_all.jsonl").read_bytes()
        starts_before = len(jsonl(h.art / "STARTS_all.jsonl"))
        code, out = h.run()
        self.assertEqual(code, 0, out[-500:])
        self.assertNotIn("KeyError", out)
        self.assertIn('"duplicate_full_rows_agreeing": 2', out)
        self.assertIn('"compact_rows_rebuilt": 0', out)
        lines = (h.art / "RESULTS_LOG_all.jsonl").read_text().splitlines()
        self.assertEqual(lines[:4], legacy_lines)                                           # the archived records are byte-identical
        self.assertEqual((h.cmp / "compact_all.jsonl").read_bytes(), before_compact)       # the existing compact rows were verified, not rewritten
        self.assertEqual(len(jsonl(h.art / "STARTS_all.jsonl")), starts_before)             # nothing was run again
        accepted = [json.loads(l)["cell_id"] for l in legacy_lines[::2]]
        (h.art / "ACCEPTED_DUPLICATES.json").write_text(json.dumps(accepted))
        self.assertEqual(h.run(command="merge-check")[0], 0)

    def test_a_missing_compact_row_of_a_legacy_cell_is_rebuilt_from_the_cell_id(self):
        h, _ = self.legacy("g_rebuild")
        rows = jsonl(h.cmp / "compact_all.jsonl")
        (h.cmp / "compact_all.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows[2:]))   # the first two compact rows are lost
        code, out = h.run()
        self.assertEqual(code, 0, out[-500:])
        self.assertIn('"compact_rows_rebuilt": 2', out)
        rebuilt = {r["cell"]: r for r in jsonl(h.cmp / "compact_all.jsonl")}
        for row in rows[:2]:
            self.assertEqual({k: v for k, v in rebuilt[row["cell"]].items() if k not in ("gpu_state", "gpu_samples")}, {k: v for k, v in row.items() if k not in ("gpu_state", "gpu_samples")})

    def test_a_row_that_disagrees_with_its_cell_id_stops_the_run(self):
        def mutate(rows):
            rows[0]["system"] = "E1" if rows[0]["system"] == "M" else "M"
        h, _ = self.legacy("g_bad", mutate)
        code, out = h.run()
        self.assertNotEqual(code, 0)
        self.assertIn("disagrees with its cell id", out)


class FinalCellAndReceiptTests(unittest.TestCase):
    def test_a_failed_compact_append_on_the_final_cell_is_repaired_before_the_run_ends(self):
        h = Harness("f_last")
        code, out = h.run({"ROSA_FAULT": "compact_raise", "ROSA_FAULT_N": "12"})
        self.assertEqual(code, 0, out[-400:])
        self.assertEqual((len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), len(jsonl(h.cmp / "compact_all.jsonl"))), (12, 12))
        self.assertEqual(json.loads((h.art / "status_all.json").read_text())["state"], "finished")
        h.audit(self)

    def test_a_persistent_compact_failure_never_ends_as_finished_and_quarantines_nothing(self):
        h = Harness("f_always")
        code, out = h.run({"ROSA_FAULT": "compact_raise_always", "ROSA_FAULT_N": "3"})
        self.assertEqual(code, 5, out[-400:])
        self.assertIn("integrity_error", out)
        self.assertEqual(json.loads((h.art / "status_all.json").read_text())["state"], "integrity_error")
        failures = json.loads((h.art / "failures_all.json").read_text()) if (h.art / "failures_all.json").exists() else {}
        self.assertEqual((failures.get("quarantined_cells", []), failures.get("quarantined_groups", [])), ([], []))   # the integrity error was not a block retry
        code, out = h.run()                                                                # the disk is fine again: the next start repairs and finishes
        self.assertEqual(code, 0, out[-400:])
        h.audit(self)

    def test_a_torn_attempt_receipt_does_not_block_recovery_and_the_cell_is_accounted_once(self):
        h = Harness("f_torn_receipt")
        h.run({"ROSA_FAULT": "full_before", "ROSA_FAULT_N": "6"})                          # killed with 5 results
        attempts = sorted((h.art / "runs_all").glob("*/attempts.jsonl"))[-1]
        lines = attempts.read_text().splitlines()
        victim = json.loads(lines[-1])["cell"]["id"]
        attempts.write_text("\n".join(lines[:-1]) + "\n" + lines[-1][: len(lines[-1]) // 2])   # the last receipt is torn
        outcomes = h.finish()
        self.assertEqual(outcomes[-1][0], 0, outcomes[-1][1][-500:])
        self.assertNotIn("JSONDecodeError", "".join(o for _, o in outcomes))
        self.assertTrue(list((h.art / "runs_all").glob("*/attempts.jsonl.torn_*")))         # evidence kept
        full, compact, counts = h.audit(self)
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl") if e["event"] == "interrupted"]
        self.assertEqual([e["cell_id"] for e in ledger], [victim])                         # the cell with the torn receipt is an interrupted attempt: one ledger entry, one re-run
        self.assertEqual(counts[victim], 2)

    def test_torn_evidence_is_never_overwritten(self):
        path = Path(tempfile.mkdtemp()) / "log.jsonl"
        for number in range(2):
            path.write_text('{"a": 1}\n{"broken')
            self.assertIn("torn last line", Q.repair_torn_tail(path))
        self.assertEqual(len(list(path.parent.glob("log.jsonl.torn_*"))), 2)


class OnceOnlyLedgerTests(unittest.TestCase):
    """D2: an attempt that has an attempt line but no result after model requests (nonzero worker exit) is under the same once-only ledger."""
    LIKE = {"ROSA_BRIDGE_LIKE_LOG": "1"}

    def test_one_failed_attempt_after_requests_is_run_once_more(self):
        target = cell("t2", "M", "m1")
        h = Harness("o_once")
        h.finish({**self.LIKE, "DUMMY_FAULT": "exit_after_requests", "DUMMY_FAULT_CELL": target})
        h.audit(self, expect_starts={target: 2})
        ledger = [e for e in jsonl(h.art / "INTERRUPTED_all.jsonl")]
        self.assertEqual([(e["event"], e["requests_seen"] > 0) for e in ledger], [("failed_after_requests", True)])
        failures_file = h.art / "failures_all.json"
        self.assertEqual(json.loads(failures_file.read_text())["cells"].get(target, 0) if failures_file.exists() else 0, 0)   # not charged to the generic 3-strike count

    def test_a_second_failed_attempt_after_requests_quarantines_the_cell(self):
        target = cell("t2", "M", "m1")
        h = Harness("o_twice")
        outcomes = h.finish({**self.LIKE, "DUMMY_FAULT": "exit_after_requests", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_TIMES": "5"})
        self.assertEqual(outcomes[-1][0], 0)
        self.assertEqual(sorted(r["cell_id"] for r in jsonl(h.art / "RESULTS_LOG_all.jsonl")), sorted(i for i in PLANNED if i != target))
        self.assertEqual([e["event"] for e in jsonl(h.art / "INTERRUPTED_all.jsonl")], ["failed_after_requests", "failed_after_requests", "quarantined"])
        starts = [r["cell_id"] for r in jsonl(h.art / "STARTS_all.jsonl") if r["event"] == "start"]
        self.assertEqual(starts.count(target), 2)

    def test_an_interrupted_and_a_failed_attempt_together_also_quarantine(self):
        target = cell("t1", "E1", "m2")
        h = Harness("o_mixed")
        h.run({"DUMMY_FAULT": "during_episode", "DUMMY_FAULT_CELL": target})                                # attempt 1: the runner is killed during the episode
        code, out = h.run({**self.LIKE, "DUMMY_FAULT": "exit_after_requests", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_DIR": str(h.root / "faults2")})   # attempt 2: nonzero exit after requests
        self.assertEqual(code, 0, out[-400:])
        self.assertEqual([e["event"] for e in jsonl(h.art / "INTERRUPTED_all.jsonl")], ["interrupted", "failed_after_requests", "quarantined"])
        self.assertNotIn(target, [r["cell_id"] for r in jsonl(h.art / "RESULTS_LOG_all.jsonl")])
        self.assertEqual(len(jsonl(h.art / "RESULTS_LOG_all.jsonl")), 11)

    def test_a_failed_attempt_without_any_model_request_keeps_the_generic_count(self):
        target = cell("t2", "M", "m1")
        h = Harness("o_zero")
        h.finish({**self.LIKE, "DUMMY_FAULT": "exit_early", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_TIMES": "2"})
        h.audit(self, expect_starts={target: 3})                                            # two generic failures, then success
        self.assertEqual(jsonl(h.art / "INTERRUPTED_all.jsonl"), [])
        self.assertGreaterEqual(json.loads((h.art / "failures_all.json").read_text())["cells"][target], 2)

    def test_zero_request_interruptions_are_charged_from_the_ledger_even_if_the_failure_file_is_lost(self):
        target = cell("t2", "E1", "m1")
        h = Harness("o_zero_ledger")
        for _ in range(3):                                                                 # three interruptions before any model request, the failure file is lost every time
            h.run({"DUMMY_FAULT": "before_model", "DUMMY_FAULT_CELL": target, "DUMMY_FAULT_TIMES": "3"})
            (h.art / "failures_all.json").unlink(missing_ok=True)
        code, out = h.run()
        self.assertEqual(code, 0, out[-400:])
        events = jsonl(h.art / "INTERRUPTED_all.jsonl")
        self.assertEqual([e["requests_seen"] for e in events if e["event"] == "interrupted"], [0, 0, 0])
        self.assertEqual([e["event"] for e in events].count("quarantined"), 1)
        self.assertNotIn(target, [r["cell_id"] for r in jsonl(h.art / "RESULTS_LOG_all.jsonl")])
        self.assertEqual(h.run()[0], 0)                                                    # idempotent: no second quarantine entry
        self.assertEqual([e["event"] for e in jsonl(h.art / "INTERRUPTED_all.jsonl")].count("quarantined"), 1)


class MultiAttemptCountTests(unittest.TestCase):
    def count(self, h):
        p = subprocess.run([sys.executable, str(QUEUE / "multi_attempt_count.py"), "--spec", str(SPEC), "--run-name", h.name, "--artifacts", str(h.root / "artifacts")], env=h.env(), capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        return json.loads(p.stdout)

    def test_a_clean_run_has_no_cell_with_two_model_request_attempts(self):
        h = Harness("m_clean")
        self.assertEqual(h.run()[0], 0)
        result = self.count(h)
        self.assertEqual({s: v["cells_with_more_than_one_model_request_attempt"] for s, v in result.items()}, {"E1": 0, "M": 0})
        self.assertEqual({s: v["cells_with_a_model_request_attempt"] for s, v in result.items()}, {"E1": 6, "M": 6})

    def test_a_rerun_after_an_interrupted_attempt_with_requests_is_counted_per_system(self):
        target = cell("t2", "M", "m1")
        h = Harness("m_rerun")
        h.finish({"DUMMY_FAULT": "during_episode", "DUMMY_FAULT_CELL": target})
        result = self.count(h)
        self.assertEqual({s: v["cells_with_more_than_one_model_request_attempt"] for s, v in result.items()}, {"E1": 0, "M": 1})

    def test_the_count_does_not_depend_on_the_ledger(self):
        target = cell("t1", "E1", "m2")
        h = Harness("m_noledger")
        h.finish({"DUMMY_FAULT": "after_worker_before_attempt", "DUMMY_FAULT_CELL": target})
        (h.art / "INTERRUPTED_all.jsonl").unlink()                                       # a lost ledger (the known limitation)
        self.assertEqual(self.count(h)["E1"]["cells_with_more_than_one_model_request_attempt"], 1)


class AnalyzeWhenCompleteTests(unittest.TestCase):
    def tool(self, h, out, tier="tier1"):
        args = [sys.executable, str(QUEUE / "analyze_when_complete.py"), "--spec", str(SPEC), "--run-name", h.name, "--tier", tier, "--primary", "M", "--baseline", "E1", "--out", str(out),
                "--machine", "all", "--models", "m1", "m2", "--artifacts", str(h.root / "artifacts"), "--compact", str(h.root / "compact")]
        return subprocess.run(args, env=h.env(), capture_output=True, text=True, timeout=120)

    def test_an_incomplete_tier_is_not_analysed(self):
        h = Harness("a_partial")
        h.run({"ROSA_FAULT": "full_before", "ROSA_FAULT_N": "6"})
        out = h.root / "an"
        p = self.tool(h, out)
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertIn("5 of 12 cells done; no comparison", p.stdout)
        self.assertEqual(list(h.root.glob("an_*")), [])                                      # nothing was computed or written

    def test_a_complete_tier_is_analysed_with_and_without_the_prestart_cells(self):
        h = Harness("a_complete")
        self.assertEqual(h.run()[0], 0)
        (h.art / "PRESTART_CELLS.json").write_text(json.dumps([PLANNED[0]]))
        out = h.root / "an"
        p = self.tool(h, out)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertTrue((h.root / "an_all.json").exists() and (h.root / "an_without_prestart.json").exists())
        self.assertIn('"group": "all", "pairs": 6', p.stdout)
        self.assertIn('"group": "without_prestart", "pairs": 5', p.stdout)

    def test_an_orphan_compact_row_blocks_the_gate_and_is_flagged(self):
        h = Harness("a_orphan")
        self.assertEqual(h.run()[0], 0)
        with (h.cmp / "compact_all.jsonl").open("a") as f:
            f.write(json.dumps(dict(jsonl(h.cmp / "compact_all.jsonl")[0], cell="000000000000")) + "\n")
        p = subprocess.run([sys.executable, str(QUEUE / "integrity_look.py"), "--spec", str(SPEC), "--run-name", h.name, "--artifacts", str(h.root / "artifacts"), "--compact", str(h.root / "compact")],
                           env=h.env(), capture_output=True, text=True, timeout=120)
        report = json.loads(p.stdout)
        self.assertEqual(report["compact_rows_outside_plan"], 1)
        self.assertFalse(report["tiers"]["tier1"]["COMPLETE"])
        self.assertFalse(report["tiers"]["tier1"]["compact_joins_full"])
        self.assertEqual(self.tool(h, h.root / "an").returncode, 3)

    def test_infrastructure_is_reported_on_rows_and_at_attempt_level(self):
        target = cell("t2", "M", "m1")
        h = Harness("a_infra")
        h.finish({"DUMMY_FAULT": "before_model", "DUMMY_FAULT_CELL": target})
        p = subprocess.run([sys.executable, str(QUEUE / "integrity_look.py"), "--spec", str(SPEC), "--run-name", h.name, "--artifacts", str(h.root / "artifacts"), "--compact", str(h.root / "compact")],
                           env=h.env(), capture_output=True, text=True, timeout=120)
        info = json.loads(p.stdout)["tiers"]["tier1"]
        self.assertEqual(info["infrastructure_rows_in_compact_share"]["M"], 0.0)
        self.assertEqual(info["attempt_level"]["M"]["zero_request_attempts"], 1)
        self.assertGreater(info["attempt_level"]["M"]["share"], 0)


if __name__ == "__main__":
    unittest.main()
