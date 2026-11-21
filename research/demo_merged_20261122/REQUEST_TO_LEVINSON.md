# Request to Levinson (for Martin to send), 2026-11-22

Hi Levinson,

For the merged-method demo (your method M mapped onto Martin's UR5e Gazebo setup) we rebuild your pieces from your public files. Two small items would make them exact. Nothing from the held-out pools is needed.

1. **Two prompt strings only** (the text, not the files): the **pilot A1 system prompt** (`run_pilot.prompt_for("A1")`) and the **C1 finish line** (the "call final_answer" instruction). Plain text is fine.
2. **`build_round1_20261115/answer_gate.py`** (one small development file). Your public `namefix_rule.py` imports it (`ABSOLUTE_NAME`, `RELATIVE_NAME`, `trailing_matches`, `allowed_names`). We only need it for the name fix. We never see your private harness, scorer or arms.

If you would rather not share them, that is fine: we rebuild both from your public documents and label the demo "M as described in his public docs, reimplemented". We never call it your frozen M.

Everything else (the 12 read tools, the `final_answer` schema, the name-fix rule, errors-as-text) we take from your public branch or rebuild and label.

The merge code is "lab-ready": every internal read inside the macro is logged with its source, time and sequence position (your scorer requirement L4), and no required task step is skipped. We will not run anything on the lab before you have run your method.

Thanks,
Martin
