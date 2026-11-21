"""Tests of the exam queue (no ROS, no Ollama; the integration tests use the dummy system with real subprocesses).
  uv run python -m unittest discover -s research/studies/final_exam_draft_20261118/exam_queue/tests -v      (about 1-2 minutes)"""
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
os.environ["ROSA_EXAM_CONFIG_DIR"] = tempfile.mkdtemp(prefix="rosa-exam-test-config-")
import commit_results  # noqa: E402
import gpu_state  # noqa: E402
import health  # noqa: E402
import monitor  # noqa: E402
import notify  # noqa: E402
import queue_core as Q  # noqa: E402

SPEC = HERE / "specs" / "dummy_spec.json"
CORE = HERE / "queue_core.py"
RUNS = []


def run_queue(name, machine="all", machines="all:1", extra_env=None, wait=True, spec=SPEC):
    env = {**os.environ, "DUMMY_DELAY_SECONDS": "0.2", "ROSA_EXAM_NOTIFY_DRY": str(Path(os.environ["ROSA_EXAM_CONFIG_DIR"]) / f"dry_{name}.log"), **(extra_env or {})}
    command = [sys.executable, str(CORE), "run", "--spec", str(spec), "--run-name", name, "--machine", machine, "--machines", machines, "--dummy"]
    RUNS.append(name)
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    if wait:
        output, _ = process.communicate(timeout=300)
        return process.returncode, output
    return process, env


def rows(name, machine="all"):
    path = Q.ARTIFACTS / name / f"RESULTS_LOG_{machine}.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def cleanup():
    for name in RUNS:
        shutil.rmtree(Q.ARTIFACTS / name, ignore_errors=True)
        shutil.rmtree(Q.COMPACT_ROOT / name, ignore_errors=True)


def tearDownModule():
    cleanup()


class PlanTests(unittest.TestCase):
    def test_priority_order_and_pair_adjacency(self):
        cells = Q.build_cells(Q.load_spec(SPEC))
        tiers = [c["tier_index"] for c in cells]
        self.assertEqual(tiers, sorted(tiers))                                        # tier 1 before tier 2 before tier 4
        for tier in set(tiers):
            seeds = [c["seed"] for c in cells if c["tier_index"] == tier]
            self.assertEqual(seeds, sorted(seeds))
        pair_positions = {}
        for index, c in enumerate(cells):
            pair_positions.setdefault((c["tier"], c["pair"]), []).append(index)
        for positions in pair_positions.values():                                      # all systems of a pair are neighbours: a stop leaves complete pairs
            self.assertEqual(positions, list(range(positions[0], positions[0] + len(positions))))
        self.assertEqual(len({c["id"] for c in cells}), len(cells))

    def test_sharding_is_disjoint_complete_and_keeps_pairs_together(self):
        spec = dict(Q.load_spec(SPEC), models=["m1", "m2", "m3", "m4"])
        spec["pools"] = {"p": {"tasks": {f"t{i}": "stage3" for i in range(60)}}}
        cells = Q.build_cells(spec)
        machines = Q.parse_machines("laptop:0.4,lab:0.6")
        mine = {name: {c["id"] for c in Q.my_cells(cells, name, machines)} for name, _ in machines}
        self.assertEqual(mine["laptop"] & mine["lab"], set())
        self.assertEqual(mine["laptop"] | mine["lab"], {c["id"] for c in cells})
        for c in cells:
            owners = {name for name in mine if c["id"] in mine[name]}
            self.assertEqual(len(owners), 1)
        pair_owner = {}
        for c in cells:
            owner = Q.owner_of(c["pair"], machines)
            self.assertEqual(pair_owner.setdefault(c["pair"], owner), owner)
        share = len(mine["lab"]) / len(cells)
        self.assertTrue(0.5 < share < 0.7, share)                                      # about the configured 60 percent

    def test_next_block_groups_same_tier_seed_model_env(self):
        cells = Q.build_cells(Q.load_spec(SPEC))
        block = Q.next_block(cells, 4)
        self.assertTrue(1 <= len(block) <= 4)
        self.assertEqual(len({(c["tier"], c["seed"], c["model"], c["env"]) for c in block}), 1)


class HeldOutPoolTests(unittest.TestCase):
    def test_pool_from_an_environment_variable_and_loud_failure_when_missing(self):
        spec = dict(Q.load_spec(SPEC))
        spec["pools"] = {"h": {"tasks_file_env": "ROSA_TEST_TASKS_FILE"}}
        spec["tiers"] = [{"name": "tier1", "systems": ["M", "E1"], "pools": ["h"], "seeds": [1]}]
        os.environ.pop("ROSA_TEST_TASKS_FILE", None)
        with self.assertRaises(RuntimeError):
            Q.build_cells(spec)
        path = Path(tempfile.mkdtemp()) / "tasks.json"
        path.write_text(json.dumps({"x1": "stage3", "x2": "e1h"}))
        os.environ["ROSA_TEST_TASKS_FILE"] = str(path)
        try:
            cells = Q.build_cells(spec)
        finally:
            del os.environ["ROSA_TEST_TASKS_FILE"]
        self.assertEqual(len(cells), 2 * len(spec["models"]) * 2)
        self.assertTrue(all(c["pool"] == "h" for c in cells))


class FrozenPlanTests(unittest.TestCase):
    def test_thinking_part_a_plan_is_the_frozen_one_and_a_changed_hash_stops_the_planner(self):
        path = HERE / "specs" / "thinking_partA_spec.json"
        spec = Q.load_spec(path)
        cells = Q.build_cells(spec)
        self.assertEqual(len(cells), 160)
        self.assertEqual({c["system"] for c in cells}, {"TH-FULL", "TH-ESCALATE"})
        self.assertEqual(len({c["session"] for c in cells}), 8)
        block = Q.next_block(cells, 48)
        self.assertEqual(len({c["session"] for c in block}), 1)                       # one frozen session = one block
        self.assertEqual({c["seed"] for c in block}, {1, 2})                          # both seeds shuffled together in a session
        bad = json.loads(json.dumps(spec))
        bad["tiers"][0]["frozen_plan"]["manifest_sha256"] = "0" * 64
        with self.assertRaises(RuntimeError):
            Q.build_cells(bad)


class NotifyTests(unittest.TestCase):
    def test_only_status_values_pass(self):
        title, message, _ = notify.build_message("finished", machine="laptop", done=3, total=8, skipped=0)
        self.assertIn("3 of 8", message)
        for bad in ("p|t1|M|m1|1", "/e1h/willow", "answer: {'node': 1}", "x" * 40, ""):
            with self.assertRaises(ValueError):
                notify.build_message("finished", machine=bad, done=1, total=2, skipped=0)
        with self.assertRaises(ValueError):
            notify.build_message("unknown_kind")
        with self.assertRaises(ValueError):
            notify.build_message("finished", machine="laptop", done=True, total=2, skipped=0)   # a bool is not a count

    def test_init_creates_a_private_random_topic_once(self):
        notify.init()
        first = notify.load_env()["NTFY_TOPIC"]
        notify.init()
        self.assertEqual(first, notify.load_env()["NTFY_TOPIC"])
        self.assertTrue(first.startswith("rosa-exam-") and len(first) > 20)
        self.assertEqual(oct(notify.ENV_FILE.stat().st_mode & 0o777), "0o600")


class MonitorTests(unittest.TestCase):
    THR = dict(monitor.THRESHOLDS, stale_heartbeat_seconds=None)

    def status(self, **kw):
        base = dict(machine="laptop", state="running", heartbeat_at=1000.0, last_progress_at=1000.0, done=3, total=8, skipped=0, disk_free_gb=500.0)
        return dict(base, **kw)

    def kinds(self, status, now, state=None, ollama=True):
        return [k for k, _ in monitor.evaluate(status, now, state if state is not None else {}, self.THR, ollama)]

    def test_finished(self):
        self.assertEqual(self.kinds(self.status(state="finished"), 1010), ["finished"])
        state = {}
        self.assertEqual(self.kinds(self.status(state="finished"), 1010, state), ["finished"])
        self.assertEqual(self.kinds(self.status(state="finished"), 1020, state), [])           # sent once

    def test_crash_by_state_and_by_stale_heartbeat(self):
        self.assertEqual(self.kinds(self.status(state="crashed"), 1010), ["crash"])
        self.assertEqual(self.kinds(self.status(heartbeat_at=1000.0, last_progress_at=1100.0), 1200), ["crash"])   # heartbeat 200 s old
        self.assertEqual(self.kinds(self.status(heartbeat_at=1190.0, last_progress_at=1190.0), 1200), [])

    def test_no_progress_threshold_is_15_minutes(self):
        self.assertEqual(self.kinds(self.status(heartbeat_at=1899.0, last_progress_at=1000.0), 1900), [])           # 900 s: not over
        self.assertEqual(self.kinds(self.status(heartbeat_at=1901.0, last_progress_at=1000.0), 1902), ["no_progress"])

    def test_ollama_down_needs_two_minutes_and_resets(self):
        state = {}
        s = self.status(heartbeat_at=1000.0)
        self.assertEqual(self.kinds(s, 1000, state, ollama=False), [])
        self.assertEqual(self.kinds(dict(s, heartbeat_at=1130.0, last_progress_at=1130.0), 1130, state, ollama=False), ["ollama_down"])
        self.assertEqual(self.kinds(dict(s, heartbeat_at=1140.0, last_progress_at=1140.0), 1140, state, ollama=True), [])
        self.assertNotIn("ollama_down_since", state)

    def test_low_disk_and_cooldown(self):
        state = {}
        s = self.status(disk_free_gb=12.0)
        self.assertEqual(self.kinds(s, 1010, state), ["low_disk"])
        self.assertEqual(self.kinds(dict(s, heartbeat_at=1100.0, last_progress_at=1100.0), 1100, state), [])
        self.assertEqual(self.kinds(dict(s, heartbeat_at=5000.0, last_progress_at=5000.0), 5000, state), ["low_disk"])   # cool-down (1 h) over

    def test_daily_summary_once_per_day(self):
        state, thr = {}, dict(self.THR, daily_hour=0)
        self.assertTrue(monitor.daily_due(time.time(), state, thr, False))
        self.assertFalse(monitor.daily_due(time.time(), state, thr, False))
        self.assertTrue(monitor.daily_due(time.time(), state, thr, True))


class MonitorStartupTests(unittest.TestCase):
    def test_monitor_starts_when_the_run_folder_does_not_exist_yet(self):
        name = "test_monitor_race"
        shutil.rmtree(Q.ARTIFACTS / name, ignore_errors=True)
        RUNS.append(name)
        done = subprocess.run([sys.executable, str(HERE / "monitor.py"), "--run-name", name, "--machine", "all", "--once", "--commit-every-hours", "999"], capture_output=True, text=True, timeout=60,
                              env={**os.environ, "ROSA_EXAM_NOTIFY_DRY": str(Path(os.environ["ROSA_EXAM_CONFIG_DIR"]) / "dry_race.log")})
        self.assertEqual(done.returncode, 0, done.stderr[-300:])
        self.assertTrue((Q.ARTIFACTS / name / "monitor_state_all.json").exists())


class HealthTests(unittest.TestCase):
    def spawn(self, domain):
        env = dict(os.environ, ROS_DOMAIN_ID=domain)
        return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)", "ros2 param get dummy leftover"], env=env, start_new_session=True)

    def test_leftover_ros_cli_process_in_our_domain_is_found_and_killed_but_another_domain_is_not(self):
        ours, other = self.spawn("220"), self.spawn("77")
        try:
            time.sleep(0.5)
            patterns = ("ros2 param",)
            self.assertIn(ours.pid, health.ros_leftovers("220", patterns))
            self.assertNotIn(other.pid, health.ros_leftovers("220", patterns))
            killed, alive = health.kill_leftovers("220", patterns)
            self.assertIn(ours.pid, killed); self.assertEqual(alive, [])
            time.sleep(0.5)
            self.assertIsNotNone(ours.poll())
            self.assertIsNone(other.poll())
        finally:
            for p in (ours, other):
                p.kill()

    def test_disk_and_unreachable_ollama(self):
        self.assertGreater(health.disk_free_gb(HERE), 0)
        self.assertFalse(health.ollama_ok("http://127.0.0.1:9", timeout=1))
        self.assertEqual(health.ollama_loaded("http://127.0.0.1:9", timeout=1), [])


class RunTests(unittest.TestCase):
    def test_full_dummy_run_logs_every_cell_once_in_tier_order(self):
        code, output = run_queue("test_full")
        self.assertEqual(code, 0, output[-400:])
        data = rows("test_full")
        self.assertEqual(len(data), 30)
        self.assertEqual(len({r["cell_id"] for r in data}), 30)
        tiers = [r["tier"] for r in data]
        self.assertEqual(tiers, sorted(tiers, key=["tier1", "tier2", "tier4"].index))
        status = json.loads((Q.ARTIFACTS / "test_full" / "status_all.json").read_text())
        self.assertEqual((status["state"], status["done"], status["total"]), ("finished", 30, 30))
        compact = [json.loads(l) for l in (Q.COMPACT_ROOT / "test_full" / "compact_all.jsonl").read_text().splitlines()]
        self.assertEqual(len(compact), 30)
        for r in compact:                                                                  # redaction: no task id, no answer
            self.assertNotIn(r["task"], ("t1", "t2", "t3"))
            self.assertNotIn("answer", r)

    def test_a_second_start_after_completion_does_nothing(self):
        run_queue("test_idem")
        before = rows("test_idem")
        code, output = run_queue("test_idem")
        self.assertEqual(code, 0)
        self.assertEqual(rows("test_idem"), before)

    def test_kill_mid_episode_and_resume_loses_nothing_and_duplicates_nothing(self):
        name = "test_kill"
        process, env = run_queue(name, wait=False, extra_env={"DUMMY_DELAY_SECONDS": "2.5"})
        deadline = time.time() + 60
        while time.time() < deadline and len(rows(name)) < 3:                              # let a few episodes finish first
            time.sleep(0.3)
        while time.time() < deadline and not any(" episode " in (p / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace") and name in (p / "cmdline").read_bytes().decode(errors="replace")
                                                for p in Path("/proc").iterdir() if p.name.isdigit() and (p / "cmdline").exists()):
            time.sleep(0.1)
        done_before = len(rows(name))
        os.killpg(process.pid, signal.SIGKILL)                                              # hard kill of the runner while an episode is running
        process.wait()
        time.sleep(0.5)
        in_flight = [p for p in (Q.ARTIFACTS / name).glob("runs_all/*/*") if p.is_dir() and not (p / "trace.jsonl").read_text().count("episode_end")]
        self.assertTrue(in_flight, "the kill did not catch an episode in flight")
        self.assertLess(done_before, 30)
        code, output = run_queue(name, extra_env={"DUMMY_DELAY_SECONDS": "0.2"})
        self.assertEqual(code, 0, output[-400:])
        self.assertIn("killed_orphans", output)
        data = rows(name)
        self.assertEqual(len(data), 30)                                                     # nothing lost
        self.assertEqual(len({r["cell_id"] for r in data}), 30)                             # nothing twice
        self.assertGreaterEqual(len(data), done_before)
        survivors = [p for p in Path("/proc").iterdir() if p.name.isdigit() and name in (p / "cmdline").read_bytes().decode(errors="replace") and "episode" in (p / "cmdline").read_bytes().decode(errors="replace")]
        self.assertEqual(survivors, [])                                                     # no orphan worker left
        merged = subprocess.run([sys.executable, str(CORE), "merge-check", "--spec", str(SPEC), "--run-name", name], capture_output=True, text=True)
        self.assertEqual(merged.returncode, 0, merged.stdout)
        self.assertEqual(json.loads(merged.stdout)["missing"], 0)

    def test_two_machines_split_the_queue_without_duplicates(self):
        name = "test_split"
        for machine in ("laptop", "lab"):
            code, output = run_queue(name, machine=machine, machines="laptop:0.4,lab:0.6")
            self.assertEqual(code, 0, output[-300:])
        a, b = rows(name, "laptop"), rows(name, "lab")
        self.assertTrue(a and b)
        self.assertEqual({r["cell_id"] for r in a} & {r["cell_id"] for r in b}, set())
        self.assertEqual(len(a) + len(b), 30)
        merged = subprocess.run([sys.executable, str(CORE), "merge-check", "--spec", str(SPEC), "--run-name", name, "--machines", "laptop:0.4,lab:0.6"], capture_output=True, text=True)
        result = json.loads(merged.stdout)
        self.assertEqual((result["duplicates"], result["missing"], result["logged_on_the_wrong_machine"]), (0, 0, 0))

    def test_a_block_group_that_keeps_failing_is_skipped_and_reported(self):
        spec = json.loads(SPEC.read_text())
        spec["queue"]["retry_wait_seconds"] = 0
        path = Path(os.environ["ROSA_EXAM_CONFIG_DIR"]) / "fail_spec.json"
        path.write_text(json.dumps(spec))
        code, output = run_queue("test_fail", extra_env={"DUMMY_RAISE_MODEL": "m2"}, spec=path)
        self.assertEqual(code, 0, output[-300:])
        status = json.loads((Q.ARTIFACTS / "test_fail" / "status_all.json").read_text())
        self.assertEqual(status["state"], "finished_with_skips")
        self.assertTrue(status["skipped"] > 0)
        self.assertEqual({r["model"] for r in rows("test_fail")}, {"m1"})                   # the healthy model completed everything
        dry = (Path(os.environ["ROSA_EXAM_CONFIG_DIR"]) / "dry_test_fail.log").read_text()
        self.assertIn("study_failing", dry)
        self.assertNotIn("m2", dry)                                                         # the alert carries counts only

    def test_stop_file_ends_the_run_cleanly_and_resume_continues(self):
        name = "test_stop"
        (Q.ARTIFACTS / name).mkdir(parents=True, exist_ok=True)
        (Q.ARTIFACTS / name / "STOP").write_text("")
        code, output = run_queue(name)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((Q.ARTIFACTS / name / "status_all.json").read_text())["state"], "stopped")
        self.assertEqual(rows(name), [])
        (Q.ARTIFACTS / name / "STOP").unlink()
        code, output = run_queue(name)
        self.assertEqual(len(rows(name)), 30)


def sample(t, used=500, total=16000, apps=None, ours=(100,), loaded=None):
    """A fake GPU snapshot: `apps` = [(pid, mib)]; `ours` = our pids; `loaded` = [(name, size_mib, size_vram_mib)]."""
    apps = [dict(pid=p, name="x", mib=m) for p, m in (apps if apps is not None else [(100, 300), (999, 249)])]
    mine = sum(a["mib"] for a in apps if a["pid"] in ours)
    return dict(t=t, used_mib=used, total_mib=total, util_pct=0, apps=apps, our_pids=list(ours), ours_mib=mine, others_mib=sum(a["mib"] for a in apps) - mine,
                loaded=[dict(name=n, size_mib=s, size_vram_mib=v) for n, s, v in (loaded or [])], load1=1.0)


class GpuStateTests(unittest.TestCase):
    """The frozen contention rule (gpu_state.py) on hand-made samples."""
    def test_clean_episode_with_only_the_desktop_daemon_is_not_contended(self):
        out = gpu_state.summarize([sample(1, loaded=[("m", 9000, 9000)]), sample(5, loaded=[("m", 9000, 9000)])], "m")
        self.assertEqual((out["state"], out["contended"], out["reasons"], out["max_others_mib"]), ("ok", False, [], 249))

    def test_rule_a_another_process_with_1_gib(self):
        out = gpu_state.summarize([sample(1), sample(3, apps=[(100, 300), (555, 1024)])], "m")
        self.assertTrue(out["contended"]); self.assertTrue(out["reasons"][0].startswith("a:"))
        self.assertFalse(gpu_state.summarize([sample(1, apps=[(100, 300), (555, 1023)])], "m")["contended"])      # just below the threshold

    def test_rule_b_model_loses_full_residency(self):
        full, partial = [("m", 9000, 9000)], [("m", 9000, 7000)]
        self.assertTrue(gpu_state.summarize([sample(1, loaded=full), sample(9, loaded=partial)], "m")["contended"])
        self.assertTrue(gpu_state.summarize([sample(1, loaded=full), sample(9)], "m")["contended"])               # unloaded at the end
        self.assertFalse(gpu_state.summarize([sample(1, loaded=partial), sample(9, loaded=partial)], "m")["contended"])  # never fully resident (granite at 65k): not contention
        self.assertFalse(gpu_state.summarize([sample(1), sample(9, loaded=full)], "m")["contended"])               # loaded during the episode

    def test_rule_c_not_enough_vram_available_at_the_start(self):
        out = gpu_state.summarize([sample(1, apps=[(100, 300), (555, 900)], loaded=[("m", 15500, 15000)])], "m")  # 16000 - 900 = 15100 < 15500, others below 1 GiB
        self.assertTrue(out["contended"]); self.assertTrue(out["reasons"][0].startswith("c:"))

    def test_without_process_information_rules_a_and_c_do_not_fire(self):  # WSL: nvidia-smi lists no processes
        blind = dict(sample(1, loaded=[("m", 15500, 15500)]), apps=[], others_mib=None, ours_mib=None)
        out = gpu_state.summarize([blind, dict(blind, t=2)], "m")
        self.assertEqual((out["contended"], out["process_info"]), (False, False))

    def test_the_sampler_recomputes_our_pids_at_every_sample(self):  # regression: a cached pid list flagged our own new Ollama runner as another user's process
        calls, original = [], gpu_state.our_ollama_pids
        gpu_state.our_ollama_pids = lambda url: calls.append(url) or [len(calls)]
        try:
            path = Path(tempfile.mkdtemp()) / "s.jsonl"
            for _ in range(3):
                gpu_state.sample_once("http://127.0.0.1:9", path)
        finally:
            gpu_state.our_ollama_pids = original
        self.assertEqual([json.loads(l)["our_pids"] for l in path.read_text().splitlines()], [[1], [2], [3]])

    def test_no_samples_is_unknown_not_contention(self):
        self.assertEqual(gpu_state.summarize([], "m")["state"], "unknown")
        self.assertFalse(gpu_state.summarize([], "m")["contended"])

    def test_read_window_and_busy_reason(self):
        path = Path(tempfile.mkdtemp()) / "g.jsonl"
        path.write_text("\n".join(json.dumps(sample(t)) for t in (1, 5, 10, 20)) + "\n")
        self.assertEqual([s["t"] for s in gpu_state.read_window(4, 11, path)], [5, 10])
        self.assertIsNone(gpu_state.busy_reason(sample(1)))
        self.assertIn("2000", gpu_state.busy_reason(sample(1, apps=[(555, 2000)])))
        self.assertIsNone(gpu_state.busy_reason(dict(sample(1), others_mib=None)))


class GpuQueueTests(unittest.TestCase):
    """The dummy queue with a fake GPU snapshot: rows carry the gpu_state block; contended episodes are kept apart and run again."""
    def spec_with(self, **queue):
        spec = json.loads(SPEC.read_text())
        spec["queue"].update(queue)
        path = Path(os.environ["ROSA_EXAM_CONFIG_DIR"]) / f"gpu_spec_{len(queue)}_{abs(hash(json.dumps(queue)))}.json"
        path.write_text(json.dumps(spec))
        return path

    def fake(self, snap):
        path = Path(tempfile.mkdtemp()) / "fake.json"
        path.write_text(json.dumps(snap))
        return {"ROSA_GPU_FAKE_SNAPSHOT": str(path), "ROSA_GPU_STATE_LOG": str(path.parent / "none.jsonl")}

    def test_clean_gpu_every_row_has_samples_and_nothing_is_contended(self):
        code, output = run_queue("test_gpu_clean", extra_env=self.fake(sample(0)))
        self.assertEqual(code, 0, output[-300:])
        data = rows("test_gpu_clean")
        self.assertEqual(len(data), 30)
        self.assertTrue(all(r["gpu_state"]["state"] == "ok" and r["gpu_state"]["samples"] >= 2 and not r["gpu_state"]["contended"] for r in data))
        self.assertFalse((Q.ARTIFACTS / "test_gpu_clean" / "CONTENDED_LOG_all.jsonl").exists())
        compact = [json.loads(l) for l in (Q.COMPACT_ROOT / "test_gpu_clean" / "compact_all.jsonl").read_text().splitlines()]
        self.assertTrue(all(c["gpu_state"] == "ok" for c in compact))

    def test_contended_episodes_are_kept_apart_never_counted_and_the_cell_is_retried_then_skipped(self):
        busy = sample(0, apps=[(100, 300), (555, 2000)])
        code, output = run_queue("test_gpu_busy", extra_env=self.fake(busy), spec=self.spec_with(gpu_wait_seconds=0, retry_wait_seconds=0))
        self.assertEqual(code, 0, output[-300:])
        self.assertEqual(rows("test_gpu_busy"), [])                                                   # no contended episode is a result
        kept = [json.loads(l) for l in (Q.ARTIFACTS / "test_gpu_busy" / "CONTENDED_LOG_all.jsonl").read_text().splitlines()]
        self.assertEqual(len(kept), 90)                                                               # 30 cells x quarantine_after (3) tries, none deleted
        self.assertTrue(all(r["gpu_state"]["contended"] for r in kept))
        status = json.loads((Q.ARTIFACTS / "test_gpu_busy" / "status_all.json").read_text())
        self.assertEqual((status["state"], status["skipped"], status["contended_episodes"]), ("finished_with_skips", 30, 90))
        compact = [json.loads(l) for l in (Q.COMPACT_ROOT / "test_gpu_busy" / "compact_all_contended.jsonl").read_text().splitlines()]
        self.assertTrue(all(c["ending"] == "infrastructure_gpu_contended" for c in compact))
        table = subprocess.run([sys.executable, str(HERE / "exam_tables.py"), "--run-name", "test_gpu_busy"], capture_output=True, text=True)
        self.assertIn("6. GPU contention frequency", table.stdout)
        self.assertEqual(table.returncode, 0, table.stderr[-300:])
        self.assertIn("| all | m1 | 45 | 45 | 100.0% |", table.stdout)                                 # every episode of m1 (15 cells x 3 tries) was contended

    def test_the_runner_waits_for_a_clean_gpu_and_gives_up_loudly(self):
        busy = sample(0, apps=[(100, 300), (555, 2000)])
        spec = self.spec_with(gpu_wait_seconds=1, gpu_poll_seconds=0.3, retry_wait_seconds=0, quarantine_after=1)
        code, output = run_queue("test_gpu_wait", extra_env=self.fake(busy), spec=spec)
        self.assertEqual(code, 0, output[-300:])
        self.assertIn("GPU still busy", output)                                                       # the block failed with a clear reason
        self.assertEqual(rows("test_gpu_wait"), [])
        self.assertFalse((Q.ARTIFACTS / "test_gpu_wait" / "CONTENDED_LOG_all.jsonl").exists())        # never started an episode, so nothing was run under contention


class ZeroCellAndMergeCheckTests(unittest.TestCase):
    def test_a_machine_that_is_not_in_machines_stops_loudly_instead_of_finishing_with_zero_cells(self):
        name = "test_zero"
        code, output = run_queue(name, machine="lab", machines="all:1")
        self.assertNotEqual(code, 0)
        self.assertIn("would own no cell", output)
        self.assertFalse((Q.ARTIFACTS / name / "status_lab.json").exists())
        code, output = run_queue(name, machine="lab", machines="laptop:1,lab:0")
        self.assertNotEqual(code, 0)
        self.assertIn("owns 0 of the 30 cells", output)

    def test_the_exit_hook_writes_a_crashed_status_so_the_monitor_is_not_silent(self):
        name = "test_zero_exit"
        RUNS.append(name)
        subprocess.run([sys.executable, str(HERE / "notify_exit.py"), name, "lab", "1"], check=True, capture_output=True)
        status = json.loads((Q.ARTIFACTS / name / "status_lab.json").read_text())
        self.assertEqual(status["state"], "crashed")
        events = monitor.evaluate(status, time.time(), {}, monitor.THRESHOLDS, True)
        self.assertEqual([k for k, _ in events], ["crash"])

    def test_merge_check_all_1_does_not_call_every_row_wrong_machine(self):
        name = "test_merge_all"
        code, output = run_queue(name, machine="lab", machines="lab:1")
        self.assertEqual(code, 0, output[-300:])
        def check(machines):
            done = subprocess.run([sys.executable, str(CORE), "merge-check", "--spec", str(SPEC), "--run-name", name, "--machines", machines], capture_output=True, text=True)
            return done.returncode, json.loads(done.stdout)
        code, result = check("lab:1")
        self.assertEqual((code, result["logged_on_the_wrong_machine"], result["machines_in_logs_not_in_machines_arg"]), (0, 0, []))
        code, result = check("all:1")                                                                  # the lab dummy run's oddity: rows logged by "lab", checked without --machines lab:1
        self.assertEqual(code, 0)
        self.assertIn("not checked", str(result["logged_on_the_wrong_machine"]))
        code, result = check("laptop:1")                                                               # a real mismatch is still reported
        self.assertEqual((result["logged_on_the_wrong_machine"], result["machines_in_logs_not_in_machines_arg"]), (30, ["lab"]))


class CommitTests(unittest.TestCase):
    def test_commits_only_compact_files_to_a_temporary_repo_and_refuses_forbidden_paths(self):
        repo = Path(tempfile.mkdtemp(prefix="rosa-exam-test-repo-"))
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "t@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "t"], check=True)
        compact = repo / "research" / "exam_results" / "r1"
        compact.mkdir(parents=True)
        (compact / "compact_all.jsonl").write_text(json.dumps(dict(cell="a1", supported=True)) + "\n")
        first = commit_results.commit("r1", "all", repo=repo, compact_dir=compact)
        self.assertIn("Exam queue results", first)
        self.assertEqual(commit_results.commit("r1", "all", repo=repo, compact_dir=compact), "no change")
        log = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B"], capture_output=True, text=True).stdout
        self.assertIn("Co-Authored-By", log)
        bad = repo / "research" / "_artifacts" / "r1"
        bad.mkdir(parents=True)
        (bad / "compact_all.jsonl").write_text("{}\n")
        with self.assertRaises(RuntimeError):
            commit_results.commit("r1", "all", repo=repo, compact_dir=bad)
        shutil.rmtree(repo)


if __name__ == "__main__":
    unittest.main()
