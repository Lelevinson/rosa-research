"""LISTVAL: `ros2_param_list` for one node returns `name: value` per parameter (study protocol: PROTOCOL.md in this folder).

Executor option `inline_param_values` (default False). When True, a SUCCESSFUL `ros2_param_list` call with a `node_name` is rendered with the current value of each parameter, read at list
time through the same read-only path as `ros2_param_get` (`rosa.tools.ros2.ros2_param_get`, so every read is also a counted native operation in the trace). Rules:
  * the rendered result keeps the original shape {node: [entries]}; an entry is "<name>: <value>" (value = the text after "value is:" of the `ros2 param get` output, stripped);
  * a value that cannot be read is shown as "<unreadable>" (the parameter is never dropped);
  * if the JSON text of the rendered result is longer than INLINE_CAP_CHARS (2,000), the ORIGINAL result is returned unchanged (names only);
  * calls without `node_name` (whole-system listing), failed calls and results of any other tool are never touched;
  * nothing is cached: `ros2_param_get` stays live, and the values shown are those at list time;
  * switch off = the original result object, byte for byte.
The tool description the model sees is NOT changed in either arm (the model is not told that values may appear).

Two arms use this class: FULL (switch off, identical to the thinking study's FULL arm) and LISTVAL (switch on).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(STUDIES / "thinking_escalation_20261119"))
import think_arm  # noqa: E402  (also puts the pilot harness on sys.path)
harness = think_arm.harness
import run_pilot  # noqa: E402

INLINE_CAP_CHARS = 2000
UNREADABLE = "<unreadable>"
VALUE_RE = re.compile(r"value is:\s*(.*)", re.S)
ARMS = ["FULL", "LISTVAL"]


def value_text(read_result):
    """Inline text of one `ros2_param_get` result ({param: output} or {"error": ...}); None when the value could not be read."""
    if not isinstance(read_result, dict) or "error" in read_result or len(read_result) != 1:
        return None
    raw = str(next(iter(read_result.values())))
    match = VALUE_RE.search(raw)
    text = (match.group(1) if match else raw).strip()
    return text if text else None


def render_inline(output, read_param, cap=INLINE_CAP_CHARS):
    """(new output, info). `output` = the original `ros2_param_list` result for one node; `read_param(node, name)` returns a `ros2_param_get` result dict.
    Returns the original object when it is not a plain {node: [names]} success or when the rendering exceeds the cap."""
    if not isinstance(output, dict) or "error" in output or len(output) != 1:
        return output, dict(rendered=False, reason="not_a_single_node_success")
    node, names = next(iter(output.items()))
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        return output, dict(rendered=False, reason="unexpected_shape")
    entries, shown, unreadable = [], [], 0
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        try:
            value = value_text(read_param(node, name))
        except Exception:  # a failed read is shown, never dropped and never fatal
            value = None
        if value is None:
            unreadable += 1
            value = UNREADABLE
        entries.append(f"{name}: {value}")
        shown.append(name)
    rendered = {node: entries}
    chars = len(json.dumps(rendered))
    if chars > cap:
        return output, dict(rendered=False, reason="over_cap", chars=chars, node=node)
    return rendered, dict(rendered=True, node=node, params=shown, unreadable=unreadable, chars=chars, original_chars=len(json.dumps(output)))


class ListValArm(think_arm.ThinkArm):
    def __init__(self, variant, recorder, context, prompt_messages, inline_param_values=None):
        assert variant in ARMS, variant
        super().__init__("FULL", recorder, context, prompt_messages)  # exactly the thinking study's FULL arm
        self.name = self.variant = variant
        self.inline_param_values = (variant == "LISTVAL") if inline_param_values is None else inline_param_values

    def read_param(self, node, name):
        from rosa.tools import ros2
        return ros2.ros2_param_get.func(node_name=node, param_name=name)

    def call_inner(self, tool, arguments):
        output = super().call_inner(tool, arguments)
        if not self.inline_param_values or tool.name != "ros2_param_list" or not arguments.get("node_name"):
            return output
        rendered, info = render_inline(output, self.read_param)
        if info.get("rendered") or info.get("reason") == "over_cap":
            self.log("listval_inline", request=self.request_count, **info)
        return rendered


def make_arm(variant, recorder, context):
    return ListValArm(variant, recorder, context, run_pilot.prompt_for("A1"))
