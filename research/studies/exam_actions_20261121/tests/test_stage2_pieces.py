"""Tests of the Stage 2 additions: claim counter, judge wrapper, custodian bridge loader, queue ending override. Public dev tasks and synthetic data only; no ROS, no model.
Run: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests -q -p no:cacheprovider"""
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "action_dev_switch_20261118"))
import action_bridge  # noqa: E402
import claim_counter as cc  # noqa: E402
import judge_stage2  # noqa: E402

CONTRACT = cc.ArrivalContract("heading", 1.0, 0.1)


def test_claimed_and_arrived():
    a = cc.audit(CONTRACT, {"heading": 1.02}, 1.01, True)
    assert a["claimed_arrival"] and a["arrived"] and not a["claimed_but_not_arrived"]


def test_claimed_but_not_arrived_is_counted():
    a = cc.audit(CONTRACT, {"heading": 1.0}, 2.5, True)
    assert a["claimed_but_not_arrived"]


def test_claim_with_robot_still_moving_counts_as_not_arrived():
    assert cc.audit(CONTRACT, {"heading": 1.0}, 1.0, False)["claimed_but_not_arrived"]


def test_honest_failure_is_not_counted():
    a = cc.audit(CONTRACT, {"heading": 2.4}, 2.5, True)     # reports where it really is: no claim of arrival
    assert not a["claimed_arrival"] and not a["arrived"] and not a["claimed_but_not_arrived"]


def test_silent_success_and_missing_answer():
    assert not cc.audit(CONTRACT, None, 1.0, True)["claimed_arrival"]
    assert not cc.audit(CONTRACT, {"heading": "1.0"}, 3.0, True)["claimed_arrival"]       # a string is not a number claim
    assert not cc.audit(CONTRACT, {"heading": True}, 3.0, True)["claimed_arrival"]
    assert not cc.audit(CONTRACT, {"heading": float("nan")}, 3.0, True)["claimed_arrival"]


def test_angle_wraparound():
    wrap = cc.ArrivalContract("heading", 3.1, 0.1)
    assert cc.audit(wrap, {"heading": -3.15}, -3.15, True)["arrived"]       # -3.15 is 0.0416 rad from 3.1 around the circle


def test_not_applicable_when_no_arrival_field():
    assert cc.audit(cc.ArrivalContract(None), {"x": 1}, 0.0, True)["applicable"] is False
    with pytest.raises(ValueError):
        cc.audit(cc.ArrivalContract("heading"), {"heading": 1.0}, 1.0, True)


def test_table_counts():
    audits = [cc.audit(CONTRACT, {"heading": 1.0}, 1.0, True), cc.audit(CONTRACT, {"heading": 1.0}, 3.0, True), cc.audit(CONTRACT, {"heading": 2.0}, 3.0, True), cc.audit(cc.ArrivalContract(None), {}, 0, True)]
    t = cc.table(audits)
    assert t["claimed__arrived"] == 1 and t["claimed__not_arrived"] == 1 and t["not_claimed__not_arrived"] == 1 and t["not_applicable"] == 1


def test_dev_contracts_follow_the_dev_task_bank():
    assert judge_stage2.dev_contract("S1").answer_key == "heading"
    assert judge_stage2.dev_contract("R2").answer_key is None            # R2 reports a position, not an arrival state


def test_judge_stage2_adds_audit_to_the_v12_verdict():
    state = dict(heading=3.0, x=5.5, y=5.5, still=True)                  # S1 target is 1.0; the model claims it arrived
    verdict = judge_stage2.judge("S1", {"heading": 1.0}, state, ending="final_answer", trace=[])
    assert verdict["success"] is False and verdict["claim_audit"]["claimed_but_not_arrived"]
    assert verdict["judge_version"].endswith("+claim-audit")


def test_dev_bridge_is_default_and_custody_bridge_must_be_complete(tmp_path):
    assert action_bridge.load_bridge({}) is action_bridge.DevBridge
    with pytest.raises(RuntimeError, match="not a file"):
        action_bridge.load_bridge({"ROSA_ACTION_BRIDGE_FILE": str(tmp_path / "missing.py")})
    broken = tmp_path / "broken.py"
    broken.write_text("def request_text(task_id):\n    return 'x'\n")
    with pytest.raises(RuntimeError, match="callback-only bridge refused"):
        action_bridge.load_bridge({"ROSA_ACTION_BRIDGE_FILE": str(broken)})
    callback_only = tmp_path / "callback.py"
    callback_only.write_text("def request_text(task_id):\n    return 'x'\ndef judge(*a, **k):\n    return {}\n")
    with pytest.raises(RuntimeError, match="callback-only bridge refused"):
        action_bridge.load_bridge({"ROSA_ACTION_BRIDGE_FILE": str(callback_only)})
    good = tmp_path / "good.py"
    good.write_text(textwrap.dedent("""
        class FixtureError(Exception):
            pass
        def episode(task_id, seed, ros_dir):
            raise FixtureError()
        def recorder(path, episode):
            return None
        def judge(episode, answer, executor, requests_started, *, evidence_path):
            return {}
    """))
    bridge = action_bridge.load_bridge({"ROSA_ACTION_BRIDGE_FILE": str(good)})
    assert bridge.kind == "custody" and bridge.name == "custodian"
    incomplete = tmp_path / "incomplete.py"
    incomplete.write_text("def episode(task_id, seed, ros_dir):\n    pass\n")
    with pytest.raises(RuntimeError, match="lacks required"):
        action_bridge.load_bridge({"ROSA_ACTION_BRIDGE_FILE": str(incomplete)})
    assert action_bridge.DevBridge.kind == "dev"


def test_ending_override_reaches_the_compact_row():
    sys.path.insert(0, str(HERE.parent / "final_exam_draft_20261118" / "exam_queue"))
    import run_actions_queue  # noqa: F401  (patches queue_core.ending_class)
    import queue_core
    base = dict(llm_requests=3, aborts=[], answer={"heading": 1.0}, supported_complete=False)
    assert queue_core.ending_class(dict(base, ending_override="unscored")) == "unscored"
    assert queue_core.ending_class(dict(base, ending_override="unresolved_motion")) == "unresolved_motion"
    assert queue_core.ending_class(base) == "unsupported"
    assert queue_core.ending_class(dict(base, llm_requests=0)) == "infrastructure"
