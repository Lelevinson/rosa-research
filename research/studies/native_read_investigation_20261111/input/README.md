# ROSA independent research output — 2026-11-11

Research report/specification, decision ledger, a bounded Codex next-step protocol, and **offline synthetic** examples/tests.

**Read first:** `ROSA_Independent_Algorithm_Research_Report_2026-11-11.md`. The author **did not run the user's local ROSA/WSL, ROS 2 nodes, model inference, or any new real ROSA experiment**. Reported historical metrics are attributed to bundled Codex/Work reports and may not be independently reproducible from the curated ZIP alone. The few local tests prove arithmetic only.

Validation (Python standard library only):

```bash
python -m unittest -v test_offline_decision_examples.py
python offline_decision_examples.py > /tmp/illustrations.json
```

JSON `offline_illustrations.json` is already generated with explicit `SYNTHETIC` warnings. The `.py` files do not contact ROSA or any network.

The accompanying report's bibliography contains primary-source URLs and the names of actual supplied documents. The canonical ROSA context and historical evidence bundle are inputs, **not** repackaged into this output.
