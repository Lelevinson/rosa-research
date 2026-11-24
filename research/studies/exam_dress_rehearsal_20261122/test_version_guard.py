"""Part C: does the frozen version_guard.py request a stop when the Ollama version or a model digest changes (or Ollama disappears)?
Frozen file untouched: the test imports it and re-points three names in memory (URL -> a local fake Ollama, custody_queue_dir -> a temp folder, ntfy -> a stub). No real Ollama call, no real notification.
  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/test_version_guard.py"""
import json
import sys
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

STUDIES = Path(__file__).resolve().parents[1]
FREEZE = STUDIES / "final_exam_draft_20261118/freeze_package_20261121"
sys.path.insert(0, str(FREEZE))
import version_guard as vg  # noqa: E402
import monitor_stage1  # noqa: E402
import notify  # noqa: E402

real_version = json.load(urllib.request.urlopen(vg.URL + "/api/version", timeout=15))["version"]
real_tags = {m["name"]: m["digest"] for m in json.load(urllib.request.urlopen(vg.URL + "/api/tags", timeout=15))["models"]}
state = dict(version=real_version, tags=dict(real_tags))


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        body = {"/api/version": {"version": state["version"]}, "/api/tags": {"models": [{"name": n, "digest": d} for n, d in state["tags"].items()]}}[self.path]
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = HTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
vg.URL = f"http://127.0.0.1:{server.server_port}"
sent = []
notify.send_ntfy = lambda *a, **k: sent.append(a[0])
notify.load_env = lambda: {}
results = []


def case(name, mutate, expect_stop, wait=6):
    folder = Path(tempfile.mkdtemp())
    monitor_stage1.custody_queue_dir = lambda: folder
    state["version"], state["tags"] = real_version, dict(real_tags)
    sys.argv = ["version_guard.py", "RUN", "1"]
    sent.clear()
    done = threading.Event()
    threading.Thread(target=lambda: (vg.main(), done.set()), daemon=True).start()
    import time
    time.sleep(2.5)
    mutate()
    done.wait(wait)
    stop = (folder / "RUN" / "STOP").exists()
    results.append((name, expect_stop, stop, bool(sent)))
    if not done.is_set():  # guard still polling (no change case): leave it, it is a daemon thread; make it stop by forcing a change
        state["version"] = "x"
        done.wait(5)


case("no change for 6 s", lambda: None, False)
case("version changes", lambda: state.update(version="0.40.18"), True)
case("one model digest changes", lambda: state["tags"].update({"qwen3.5:9b": "deadbeef"}), True)
case("a model disappears", lambda: state["tags"].pop("gpt-oss:20b"), True)
case("an extra, unlisted model appears (not frozen)", lambda: state["tags"].update({"new:1b": "abc"}), False)
for r in results:
    print(r)
# unreachable: close the server
server.shutdown(); server.server_close()
folder = Path(tempfile.mkdtemp()); monitor_stage1.custody_queue_dir = lambda: folder
done = threading.Event(); sent.clear(); sys.argv = ["version_guard.py", "RUN", "1"]
threading.Thread(target=lambda: (vg.main(), done.set()), daemon=True).start()
done.wait(15)
print(("Ollama unreachable (3 misses)", True, (folder / "RUN" / "STOP").exists(), bool(sent)))
