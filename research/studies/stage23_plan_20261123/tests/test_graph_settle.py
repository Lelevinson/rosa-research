"""Unit tests (no ROS) plus one real-ROS test in an isolated domain (skipped without `ros2`). Run: uv run pytest tests -q"""
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import graph_settle as g


def test_pattern_separates_cli_from_fixture_nodes():
    assert g.is_transient_cli_node("/_ros2cli_48213")
    assert g.is_transient_cli_node("/_ros2cli_daemon_0_ab12cd")
    assert not g.is_transient_cli_node("/turtlesim")
    assert not g.is_transient_cli_node("/my_ros2cli_tool")      # name merely contains the text
    assert not g.is_transient_cli_node("/ns/controller_server")


def test_compare_ignores_cli_but_never_a_real_extra_node():
    ok = g.compare_endpoints(["/a", "/b"], ["/a", "/b", "/_ros2cli_77"])
    assert ok["match"] and ok["ignored"] == ["/_ros2cli_77"]
    bad = g.compare_endpoints(["/a", "/b"], ["/a", "/b", "/intruder", "/_ros2cli_77"])
    assert not bad["match"] and bad["unexpected"] == ["/intruder"]
    gone = g.compare_endpoints(["/a", "/b"], ["/a"])
    assert not gone["match"] and gone["missing"] == ["/b"]


def test_wait_returns_when_transient_node_disappears():
    lists = iter(["/a\n/_ros2cli_9\n", "/a\n/_ros2cli_9\n", "/a\n", "/a\n"])
    now = [0.0]
    result = g.wait_until_no_transient_nodes(lambda args, t: (next(lists), 1), 20, 1, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s))
    assert result["settled"] and result["transient_seen"] == ["/_ros2cli_9"] and result["waited_s"] == 3.0


def test_wait_times_out_and_reports_it():
    now = [0.0]
    result = g.wait_until_no_transient_nodes(lambda args, t: ("/a\n/_ros2cli_9\n", 1), 5, 1, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s))
    assert not result["settled"] and result["waited_s"] >= 5


ros_available = shutil.which("ros2") is not None


@pytest.mark.skipif(not ros_available, reason="ros2 not installed")
def test_real_ros_transient_cli_node_is_waited_for_and_ignored():
    """Isolated domain 231 and localhost only (Stage 1 uses 220); --no-daemon everywhere so no discovery daemon is touched."""
    env = dict(os.environ, ROS_DOMAIN_ID="231", ROS_LOCALHOST_ONLY="1")
    publisher = subprocess.Popen([sys.executable, str(Path(__file__).with_name("fixture_node.py"))], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    echo = None
    try:
        def run(args, timeout_s):
            return g.real_run_command(args, timeout_s, env=env)
        time.sleep(5)
        echo = subprocess.Popen(["ros2", "topic", "echo", "--no-daemon", "--spin-time", "3", "/settle_test"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        time.sleep(6)
        # 1. while the echo command is alive, its helper node is visible: the raw comparison WOULD fail.
        info, _ = run(["ros2", "topic", "info", "/settle_test", "--verbose", "--no-daemon", "--spin-time", "3"], 20)
        assert "_ros2cli_" in info, "test premise: a live CLI command should appear as an endpoint"
        for _ in range(3):  # a discovery miss is possible on a busy machine; the premise only needs one sighting
            listed = g.visible_nodes(run)
            if any(g.is_transient_cli_node(n) for n in listed):
                break
        else:
            raise AssertionError(("echo helper node never listed", listed, echo.poll()))
        # 2. end the echo command; the wait must return settled=True, and the final list has no transient node.
        os.killpg(echo.pid, signal.SIGINT)
        result = g.wait_until_no_transient_nodes(run, settle_timeout_s=30, poll_interval_s=1)
        assert result["settled"], result
        kept, ignored = g.drop_transient(g.visible_nodes(run))
        assert ignored == [] and all(n.startswith("/") for n in kept)
    finally:
        for proc in (echo, publisher):
            if proc is not None and proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)


def test_listing_command_own_node_is_not_counted():
    names = g.visible_nodes(lambda args, t: ("/a\n/_ros2cli_4242\n/_ros2cli_77\n", 4242))
    assert names == ["/a", "/_ros2cli_77"]


def _fake(listings):
    items = iter(listings)
    now = [0.0]
    return (lambda args, t: (next(items), 1)), dict(clock=lambda: now[0], sleep=lambda x: now.__setitem__(0, now[0] + x))


def test_empty_discovery_is_a_miss_not_a_clean_listing():
    run, timing = _fake(["", "", "/turtlesim\n"])   # two empty listings (discovery miss), then the fixture appears
    result = g.wait_until_no_transient_nodes(run, 30, 1, expected_nodes=["/turtlesim"], **timing)
    assert result["settled"] and result["discovery_misses"] == 2


def test_without_expected_nodes_one_empty_listing_is_not_trusted_alone():
    run, timing = _fake(["", "/a\n", "/a\n"])      # first listing empty: still needs two clean in a row
    result = g.wait_until_no_transient_nodes(run, 30, 1, **timing)
    assert result["settled"] and result["waited_s"] == 2.0


def test_fixture_check_reports_missing_unexpected_and_ignored():
    run, timing = _fake(["/turtlesim\n/_ros2cli_5\n", "/turtlesim\n", "/turtlesim\n/rogue\n/backend\n", "/turtlesim\n/rogue\n/backend\n"])
    result = g.check_fixture_graph(run, ["/turtlesim"], allowed_extra_nodes=["/backend"], **timing)
    assert result["unexpected"] == ["/rogue"] and not result["ok"] and result["settle"]["transient_seen"] == ["/_ros2cli_5"]


def test_fixture_check_ok_and_missing():
    run, timing = _fake(["/turtlesim\n", "/turtlesim\n"])
    assert g.check_fixture_graph(run, ["/turtlesim"], **timing)["ok"]
    run, timing = _fake(["/other\n"] * 40)
    result = g.check_fixture_graph(run, ["/turtlesim"], settle_timeout_s=3, **timing)
    assert result["missing"] == ["/turtlesim"] and not result["ok"] and not result["settle"]["settled"]
