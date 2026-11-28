"""Arm (b) prompt lines. LABEL: merged-method demo, arm (b) "M + primitives", demonstration only, not evaluated, not for the paper.
Arm (a) = his A1 messages + MACRO_RULES + SKILL_LINE (merged_demo/prompts.py, frozen). Arm (b) = the SAME his A1 messages + the SAME rule sentences, with only the words that name
`run_skill` replaced by the names of the four primitive tools. Every other sentence of MACRO_RULES is kept word for word. This is the minimum change needed because
`run_skill` does not exist in arm (b); it is not per-model tuning and is the same for every model."""
from .prompts import MACRO_RULES, SKILL_LINE, FALLBACK_BASE, FALLBACK_FINISH, load_prompt  # noqa: F401

OLD_FIRST = 'use run_skill only for registered inspection skills and movements.'
NEW_FIRST = 'use read_readiness, read_pose, write_pose and verify_pose only for the arm: readiness checks and registered movements.'
assert OLD_FIRST in MACRO_RULES
PRIMITIVE_RULES = MACRO_RULES.replace(OLD_FIRST, NEW_FIRST)
PRIMITIVE_LINE = ('The arm tools are single steps: read_pose and read_readiness only read; write_pose moves to a registered skill target (once per task, only after read_pose) '
                  'and does not verify; verify_pose checks the result. Call one arm tool per response; do not repeat completed steps.')
