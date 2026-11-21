"""Registry entries of the Stage 2 action systems for the exam queue. The queue's own `systems.py` is part of the frozen file list, so it is NOT edited: `run_actions_queue.py` adds these entries
to `systems.SYSTEMS` at run time. When the owner approves integration (and a new freeze), the same three lines go into `systems.py`.
system id -> (runner file relative to research/studies, arm name, description)"""
ACTION_SYSTEMS = {
    "XM": ("exam_actions_20261121/run_actions.py", "XM", "Stage 2 method M with the guarded action tool (dev action tasks)"),
    "XS0": ("exam_actions_20261121/run_actions.py", "XS0", "Stage 2 extended baseline S0x: stock ROSA + the same typed action tool"),
    "XE1": ("exam_actions_20261121/run_actions.py", "XE1", "Stage 2 extended baseline E1x: E1 + the same typed action tool"),
}
