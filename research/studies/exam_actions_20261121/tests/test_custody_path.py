"""The custody path of the runner against a SYNTHETIC bridge with the shape of Codex's contract (no custodian file, no task content, no ROS, no model, no live episode).
Run: PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run --with pytest python -m pytest research/studies/exam_actions_20261121/tests -q -p no:cacheprovider"""
import contextlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "final_exam_draft_20261118" / "exam_queue"))
import action_arms  # noqa: E402  (puts the S1 tool folder on the path)
import run_actions as RA  # noqa: E402
import run_actions_queue  # noqa: F401,E402  (patches queue_core.ending_class)
import queue_core  # noqa: E402
from fake_backend import FakeBackend, FakeClock  # noqa: E402

SECRET = "SYNTHETIC-REQUEST-TEXT-do-not-leak"


class FixtureError(Exception):
    pass


class FakeRecorder(action_arms.run_pilot.Recorder):
    """Same shape as custodian.CustodyRecorder: refuses a non-private directory."""

    def __init__(self, path, episode):
        assert Path(path).parent.stat().st_mode & 0o077 == 0, "trace directory must be private"
        super().__init__(path)
        self.episode = episode


def make_bridge(log, ending_class="scored", supported=True, fail_entry=False):
    active = SimpleNamespace(request=SECRET, backend=FakeBackend(FakeClock()))

    @contextlib.contextmanager
    def episode(task_id, seed, ros_dir):
        assert Path(ros_dir).stat().st_mode & 0o077 == 0
        log.append("enter")
        if fail_entry:
            raise FixtureError("stable-start check failed")
        yield active
        log.append("exit")

    def recorder(path, episode_object):
        log.append("recorder")
        return FakeRecorder(path, episode_object)

    def judge(episode_object, answer, executor, requests_started, *, evidence_path):
        assert episode_object is active and "exit" not in log, "judge must run inside the context, before teardown"
        log.append(("judge", requests_started))
        Path(evidence_path).write_text("{}")
        return dict(ending_class=ending_class, supported_complete=supported, scored=ending_class != "post_start_oracle_loss", goals_sent=executor.goals_sent,
                    executor_final_state=executor.state.value, arrived=True, arrival_claim=True, claim_audit=dict(applicable=True, claimed_but_not_arrived=False),
                    success=supported, reasons=[], judge_version="synthetic")
    bridge = SimpleNamespace(name="synthetic", kind="custody", episode=episode, recorder=recorder, judge=judge, FixtureError=FixtureError)
    bridge.active = active
    return bridge


def args_for(queue_root, arm="XM"):
    return SimpleNamespace(output=str(queue_root / "000-s2_aaaaaaaaaaaaaaaaaaaaaaaa-XM-m-s1"), env="turtlesim", task="s2_aaaaaaaaaaaaaaaaaaaaaaaa", arm=arm, model="m", seed=1, temperature=0.7)


@pytest.fixture
def custody(tmp_path, monkeypatch):
    root = tmp_path / "custody"
    root.mkdir(mode=0o700)
    os.chmod(root, 0o700)
    monkeypatch.setenv(RA.CUSTODY_DIR_ENV, str(root))
    monkeypatch.setenv("ROS_DOMAIN_ID", "220")
    monkeypatch.setenv("ROS_LOCALHOST_ONLY", "1")
    monkeypatch.setenv("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
    queue_root = tmp_path / "queue"
    queue_root.mkdir()
    return SimpleNamespace(root=root, queue=queue_root)


def stub_agent(monkeypatch, log, error=None, answer={"status": "SUCCEEDED"}):
    seen = {}

    def run_agent(args, arm, recorder, request):
        log.append("agent")
        seen.update(recorder=recorder, request=request)
        recorder.add("model_start")
        recorder.add("model_end", usage=dict(input_tokens=10, output_tokens=5))
        return (None, "no_answer", error) if error else (answer, "final_answer", None)
    monkeypatch.setattr(RA, "run_agent", run_agent)
    spy = {}
    real_kit = action_arms.ActionToolKit

    def kit(policy, executor, backend, recorder):
        spy.update(backend=backend, recorder=recorder)
        return real_kit(policy, executor, backend, recorder)
    monkeypatch.setattr(action_arms, "ActionToolKit", kit)
    return seen, spy


def row_of(custody_dir, queue_dir):
    return RA.episode_row("exam", "session", queue_dir, dict(cell=dict(temperature=0.7), seconds=3.0, error=None))


def test_order_request_backend_recorder_and_scoring_inside_the_context(custody, monkeypatch):
    log = []
    bridge = make_bridge(log)
    seen, spy = stub_agent(monkeypatch, log)
    args = args_for(custody.queue)
    RA.episode_custody(args, bridge)
    assert log == ["enter", "recorder", "agent", ("judge", 1), "exit"]                 # episode opened before the model; judge before teardown
    assert seen["request"] == SECRET and spy["backend"] is bridge.active.backend      # request and backend come from the custody episode
    assert spy["recorder"] is seen["recorder"] and isinstance(seen["recorder"], FakeRecorder)   # one custody recorder for kit and model


def test_nothing_of_the_request_reaches_the_queue_folder_and_custody_files_are_private(custody, monkeypatch):
    log = []
    stub_agent(monkeypatch, log)
    args = args_for(custody.queue)
    RA.episode_custody(args, make_bridge(log))
    queue_dir = Path(args.output)
    assert [p.name for p in queue_dir.iterdir()] == ["custody_result.json"]
    assert SECRET not in (queue_dir / "custody_result.json").read_text()
    episode_dir = next(custody.root.iterdir())
    assert episode_dir.stat().st_mode & 0o077 == 0 and (episode_dir / "ros").stat().st_mode & 0o077 == 0
    assert {p.name for p in episode_dir.iterdir()} == {"ros", "trace.jsonl", "evidence.json"}


def test_row_from_a_scored_episode_uses_custody_fields(custody, monkeypatch):
    log = []
    stub_agent(monkeypatch, log)
    args = args_for(custody.queue)
    RA.episode_custody(args, make_bridge(log))
    row = row_of(custody, Path(args.output))
    assert row["supported_complete"] is True and row["llm_requests"] == 1 and row["input_tokens"] == 10 and row["answer"] == "in_custody"
    assert queue_core.ending_class(row) == "supported" and row["exposure"]["goals_sent"] == 0


@pytest.mark.parametrize("custody_class, expected", [("post_start_oracle_loss", "unscored"), ("agent_unresolved_motion", "unresolved_motion"), ("scored", "unsupported")])
def test_custody_ending_classes_map_to_queue_endings(custody, monkeypatch, custody_class, expected):
    log = []
    stub_agent(monkeypatch, log)
    args = args_for(custody.queue)
    RA.episode_custody(args, make_bridge(log, ending_class=custody_class, supported=False))
    assert queue_core.ending_class(row_of(custody, Path(args.output))) == expected


def test_pre_start_fixture_failure_makes_no_model_request_and_is_infrastructure(custody, monkeypatch):
    log = []
    stub_agent(monkeypatch, log)
    args = args_for(custody.queue)
    RA.episode_custody(args, make_bridge(log, fail_entry=True))
    assert log == ["enter"]                                                           # no recorder, no agent, no judge
    row = row_of(custody, Path(args.output))
    assert row["llm_requests"] == 0 and queue_core.ending_class(row) == "infrastructure"


def test_model_failure_is_still_scored_before_teardown(custody, monkeypatch):
    log = []
    stub_agent(monkeypatch, log, error="ReadTimeout('boom')")
    args = args_for(custody.queue)
    RA.episode_custody(args, make_bridge(log, supported=False))
    assert ("judge", 1) in log and log[-1] == "exit"
    row = row_of(custody, Path(args.output))
    assert row["aborts"] == ["ReadTimeout('boom')"] and queue_core.ending_class(row) == "backend_error"


def test_custody_directory_must_exist_and_be_private_before_any_episode(tmp_path, monkeypatch):
    log = []
    bridge = make_bridge(log)
    monkeypatch.delenv(RA.CUSTODY_DIR_ENV, raising=False)
    monkeypatch.setenv("ROS_DOMAIN_ID", "220")
    monkeypatch.setenv("ROS_LOCALHOST_ONLY", "1")
    monkeypatch.setenv("ROS_AUTOMATIC_DISCOVERY_RANGE", "LOCALHOST")
    with pytest.raises(RuntimeError, match="mode-0700"):
        RA.episode_custody(args_for(tmp_path), bridge)
    open_dir = tmp_path / "open"
    open_dir.mkdir()
    os.chmod(open_dir, 0o755)
    monkeypatch.setenv(RA.CUSTODY_DIR_ENV, str(open_dir))
    with pytest.raises(RuntimeError, match="mode-0700"):
        RA.episode_custody(args_for(tmp_path), bridge)
    assert log == []                                                                   # the bridge was never entered


@pytest.mark.parametrize("domain, localhost, range_", [("219", "1", "LOCALHOST"), ("", "1", "LOCALHOST"), ("220", "0", "LOCALHOST"), ("220", "1", "SUBNET"), ("220", "1", "")])
def test_custody_episode_refuses_an_unisolated_ros_environment(custody, monkeypatch, domain, localhost, range_):
    log = []
    monkeypatch.setenv("ROS_DOMAIN_ID", domain)
    monkeypatch.setenv("ROS_LOCALHOST_ONLY", localhost)
    monkeypatch.setenv("ROS_AUTOMATIC_DISCOVERY_RANGE", range_)
    with pytest.raises(RuntimeError, match="isolated ROS domain"):
        RA.episode_custody(args_for(custody.queue), make_bridge(log))
    assert log == []
