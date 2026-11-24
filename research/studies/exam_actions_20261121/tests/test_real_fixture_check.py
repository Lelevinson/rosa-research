"""Real ROS (domain 231, localhost only, about 60 s, no model, no GPU): the runner's fixture check against a real turtlesim. Skipped if ros2 or turtlesim is missing."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).with_name("real_fixture_check_script.py")


@pytest.mark.skipif(shutil.which("ros2") is None or not Path("/opt/ros/jazzy/lib/turtlesim").exists(), reason="ros2 / turtlesim not installed")
def test_fixture_check_with_real_turtlesim():
    env = dict(os.environ, ROS_DOMAIN_ID="231", ROS_LOCALHOST_ONLY="1")
    done = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=240)
    line = next((l for l in done.stdout.splitlines() if l.startswith("RESULT ")), None)
    assert line, (done.stdout[-500:], done.stderr[-800:])
    out = json.loads(line[7:])
    assert out["clean"]["ok"], out
    assert out["echo_visible_before_check"], out                      # the premise: a live CLI command shows up in the graph
    assert out["right_after_echo_ends"]["ok"], out                    # waited for or ignored, never a failure
    assert not out["simulator_gone"]["ok"] and out["simulator_gone"]["missing"] == ["/turtlesim"], out
