"""Ollama version and digest guard for the Stage 1 run (revision 1, owner instruction 2026-11-21): polls Ollama every 30 s; a version or model-digest change = STOP and report. On a change it creates the
queue's STOP file in the custodian run folder (the runner finishes the current episode and exits), sends one status-only ntfy message and exits. It reads /api/version and /api/tags only.
  python3 version_guard.py RUN [INTERVAL_SECONDS]
Limit: this DETECTS a change; it cannot prevent the Windows Ollama updater from restarting the server, which would fail the episode in flight (see FREEZE_REV1.json, ollama_auto_update)."""
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUEUE = HERE.parents[0] / "exam_queue"
sys.path.insert(0, str(QUEUE))
URL = "http://172.30.80.1:11434"


def current():
    version = json.load(urllib.request.urlopen(URL + "/api/version", timeout=15))["version"]
    tags = {m["name"]: m["digest"] for m in json.load(urllib.request.urlopen(URL + "/api/tags", timeout=15))["models"]}
    return version, tags


def main():
    import monitor_stage1
    import notify
    run = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    record = json.loads((HERE / "FREEZE.json").read_text())
    revision = json.loads((HERE / "FREEZE_REV1.json").read_text())
    expected_version, expected_digests = revision["ollama_version"], record["model_digests"]
    misses = 0
    while True:
        try:
            version, tags = current()
            misses = 0
            changed = version != expected_version or any(tags.get(m) != d for m, d in expected_digests.items())
        except Exception:  # noqa: BLE001  an unreachable Ollama is the queue's own wait/stop logic; three misses in a row are reported here too
            misses += 1
            changed = misses >= 3
        if changed:
            stop = monitor_stage1.custody_queue_dir() / run / "STOP"
            stop.parent.mkdir(parents=True, exist_ok=True)
            stop.write_text("Ollama version or digest changed (or unreachable): stopped by version_guard.py\n")
            notify.send_ntfy("Ollama changed", "Ollama version or model digest changed or Ollama is unreachable during the Stage 1 run. A stop was requested: the run finishes its current episode and stops.", "urgent", notify.load_env())
            print("STOP requested")
            return
        time.sleep(interval)


if __name__ == "__main__":
    main()
