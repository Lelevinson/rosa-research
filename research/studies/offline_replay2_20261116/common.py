"""Shared loading for the three offline jobs (protocol: PROTOCOL.md). Reads recorded traces only; no model, no ROS."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "offline_replay_20261116"))
import episodes as E  # noqa: E402

ag = E.ag
PER_ENTITY_TOOLS = ["ros2_node_info", "ros2_param_list", "ros2_topic_info", "ros2_service_info", "ros2_param_get"]
KIND_OF_TOOL = {"ros2_node_info": "node", "ros2_param_list": "node", "ros2_param_get": "node", "ros2_topic_info": "topic", "ros2_service_info": "service"}
LIST_TOOLS = {"ros2_node_list": ("nodes", "node"), "ros2_topic_list": ("topics", "topic"), "ros2_service_list": ("services", "service")}


def environment_of(task_id):
    e1h = {t["id"] for t in json.loads((STUDIES / "small_model_harness_20261115/e1h_tasks.json").read_text())}
    return "e1h" if task_id in e1h else "stage3"


def load_episodes():
    tasks = E.load_tasks()
    episodes = [E.parse(group, row, tasks) for group, row in E.run_rows()]
    for ep in episodes:
        ep["env"] = environment_of(ep["task"])
        ep["control_type"] = ep["arm"] == "C1"
    return episodes


def rtokens(request):
    return request["input_tokens"] + request["output_tokens"]


def table(rows, keys):
    """Group dict rows by the tuple of `keys` -> list."""
    out = {}
    for row in rows:
        out.setdefault(tuple(row[k] for k in keys), []).append(row)
    return out
