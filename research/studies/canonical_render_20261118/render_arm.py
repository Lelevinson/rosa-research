"""Live arms for the canonical-rendering study (protocol: PROTOCOL_LIVE.md, hash in PROTOCOL_LIVE.sha256). Read the protocol first.

FULL   = pilot arm C1 unchanged.
RENDER = C1 unchanged, except that the successful result of each of the 12 menu tools is replaced by render_result(raw result) before it is returned to the model.
         Prompt, tool schemas and descriptions are identical to FULL. The harness bookkeeping (ledger, step record) is done by C1 on the RAW result before the rendering,
         and a `render_applied` handler event keeps the raw result whenever the rendering changed it.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import harness  # noqa: E402
import run_pilot  # noqa: E402
import render_core  # noqa: E402

ARMS = ["FULL", "RENDER"]
MENU_TOOLS = set(harness.DOMAIN_TOOLS)  # the 12 menu tools of the protocol


class RenderArm(harness.Arm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the base arm
        self.name, self.variant = variant, variant

    def execute(self, tool, arguments):
        output = super().execute(tool, arguments)  # raises for errors and blocked tools: those are never rendered
        if self.variant != "RENDER" or tool.name not in MENU_TOOLS:
            return output
        rendered = render_core.render_result(output)
        if rendered != output:
            self.log("render_applied", tool=tool.name, raw=output)
        return rendered


def make_arm(variant, recorder, context):
    return RenderArm(variant, recorder, context, run_pilot.prompt_for("A1"))
