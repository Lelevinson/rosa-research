"""Arms of the tool-description compaction test: FULL (the steady loop C1, ablation arm FULL, unchanged) and COMPACT (the same, with the rule of compaction.py applied to the
description of every tool schema that is offered to the model). Nothing else differs: same prompt, same tools offered, same `parameters`, same strict pre-check (it reads the original schema), same execution."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "steady_loop_ablation_20261117"))
import ablation_arms  # noqa: E402  (also puts the pilot study on sys.path)
import compaction  # noqa: E402

ARMS = ["FULL", "COMPACT"]


class CompactArm(ablation_arms.AblationArm):
    def __init__(self, recorder, context, prompt_messages):
        super().__init__("FULL", recorder, context, prompt_messages)  # exactly the ablation's FULL arm
        self.name = "COMPACT"
        self.sizes_logged = False

    def visible_schemas(self, schemas, messages):
        chosen = super().visible_schemas(schemas, messages)
        compacted = [compaction.compact_schema(s) for s in chosen]
        if not self.sizes_logged:
            self.sizes_logged = True
            self.log("description_chars", before=sum(len(s["function"]["description"]) for s in chosen), after=sum(len(s["function"]["description"]) for s in compacted),
                     parameters_identical=all(a["function"]["parameters"] == b["function"]["parameters"] and a["function"]["name"] == b["function"]["name"] for a, b in zip(chosen, compacted)))
        return compacted


def make_arm(name, recorder, context):
    prompt = ablation_arms.run_pilot.prompt_for("A1")
    if name == "FULL":
        return ablation_arms.AblationArm("FULL", recorder, context, prompt)
    assert name == "COMPACT", name
    return CompactArm(recorder, context, prompt)
