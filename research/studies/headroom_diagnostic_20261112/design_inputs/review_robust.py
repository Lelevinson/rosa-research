"""Runs the unchanged stage3_review.py with one guard added from outside (stage3_labels.py itself is not edited).
The Stage 3 labeller assumes every call argument is a string; a model that sends a null argument (seen with gpt-oss:20b) made it raise TypeError.
Guard: an element with a null name/argument is treated as outside the minimal plan (no stage), exactly like any other unmatched call.
usage: python3 review_robust.py <repo_root> <run_dir>   (writes labels_3.json like stage3_review.py)"""
import sys
from pathlib import Path
STUDY = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STUDY))
import stage3_labels as L

_original = L.stage_of

def guarded(c, elems):
    if any(part is None for el in L.call_elements(c) for part in el):
        return None, False, False
    return _original(c, elems)

L.stage_of = guarded
import stage3_review
stage3_review.main()
