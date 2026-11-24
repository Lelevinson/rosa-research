"""Dress rehearsal only. Loaded in every Python process whose PYTHONPATH contains this folder (the queue runner and each episode worker).
It re-binds two module-level names of the frozen custodian module `bridge` IN MEMORY so that the unchanged launcher reads a rehearsal folder instead of the protected custodian folder:
  bridge.CUSTODY  -> the rehearsal custody folder (used by bridge.protected())
  bridge.MANIFEST -> the rehearsal manifest
No file of the launcher is edited. Without ROSA_REHEARSAL_CUSTODY set, this module does nothing."""
import os
import sys
from pathlib import Path

if os.environ.get("ROSA_REHEARSAL_CUSTODY"):
    sys.path.insert(0, os.environ["ROSA_REHEARSAL_STUDIES"] + "/custodian_stage1_20261121")
    import bridge
    bridge.CUSTODY = Path(os.environ["ROSA_REHEARSAL_CUSTODY"]).resolve()
    bridge.MANIFEST = Path(os.environ["ROSA_REHEARSAL_MANIFEST"]).resolve()
    sys.path.remove(os.environ["ROSA_REHEARSAL_STUDIES"] + "/custodian_stage1_20261121")
