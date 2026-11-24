"""DEV stand-in for the custodian fixture runtime (`fixtures.py`) used by the dress rehearsal. NOT the held-out runtime (that folder is not opened here).
Same interface the frozen launcher `queue_bridge.py` calls: preflight(), session(entry, out, recorder) -> object with .namespace/.observe/.tool_result/.finish, score(entry, events, directory).
Per episode (like the custodian runtime's startup / reset / cleanup): check the domain is empty, start the public dev fixture nodes, wait until listed, read the oracle,
run the episode, reset a scripted change, read the oracle again (result stored in the episode folder), stop the nodes, check the domain is empty.
Scoring = scorer v2.0 through the bridge's own `score_v2` (scorer v2.0 + bridge costs)."""
import contextlib
import importlib
import json
import os
import sys
import time
from pathlib import Path

STUDIES = Path(os.environ["ROSA_REHEARSAL_STUDIES"])
for sub in ("headroom_diagnostic_20261112", "small_model_harness_20261115", "name_fix_applied_20261117", "build_round2_20261116", "residual_failures_20261115", "custodian_stage1_20261121"):
    sys.path.insert(0, str(STUDIES / sub))
import run_stage1 as S1  # noqa: E402  (start_processes, wait_for, verify_empty ... : the dev fixture helpers)
import change_hook  # noqa: E402  (the frozen read-trigger hook module, reused for e1h change tasks)
import bridge  # noqa: E402

MODULES = {"stage3": "stage3_fixture", "e1h": "e1h_fixture", "namefix": "namefix_fixture"}
OWN_NAMESPACES = ("/s3", "/e1h", "/nf")


def load_env(name):
    return importlib.import_module(MODULES[name])


def preflight():
    """The domain must hold no fixture node of any dev namespace; otherwise a previous run left something behind."""
    code, names, err = S1.node_list()
    if code != 0:
        raise RuntimeError("ros2 node list failed in the preflight: " + err[:200])
    leftovers = [n for n in names if n.startswith(tuple(OWN_NAMESPACES))]
    if leftovers and os.environ.get("ROSA_REHEARSAL_LAX_PREFLIGHT") != "1":  # variant B of the kill test: leave leftovers to the queue's own start-up cleanup
        raise RuntimeError(f"fixture nodes already in the domain: {leftovers[:3]}")


class Fixture:
    def __init__(self, env, task, recorder, out):
        self.namespace, self.env, self.task, self.recorder, self.out = env.NS, env, task, recorder, out
        change = task.get("change")
        self.hook = change_hook.ChangeHook({"node": change["node"], "parameter": change["param"]}, self._apply) if change else None
        self.change = change

    def _set(self, value):
        import subprocess
        for _ in range(3):
            p = subprocess.run(["ros2", "param", "set", self.change["node"], self.change["param"], str(value)], capture_output=True, text=True, timeout=30)
            if p.returncode == 0:
                return True
            time.sleep(1)
        return False

    def _apply(self):
        ok = self._set(self.change["new_value"])
        self.recorder.add("scripted_change", ok=ok, node=self.change["node"], param=self.change["param"], new_value=self.change["new_value"])
        if not ok:
            raise RuntimeError("scripted change failed")

    def observe(self, event):
        if self.hook:
            self.hook.observe(event)

    def tool_result(self, rows):
        pass

    def finish(self):
        if self.hook and self.hook.fired:
            ok = self._set(self.change["initial_value"])
            self.recorder.add("scripted_reset", ok=ok)


@contextlib.contextmanager
def session(entry, out, recorder):
    import run_round2
    env = run_round2.OracleWithRetry(load_env(entry["environment"]))
    task = entry["task"]
    out = Path(out)
    S1.assert_domain_empty((env.NS,), recorder)
    processes, handles = S1.start_processes(env.commands(), out, "fx", recorder)
    try:
        time.sleep(6)
        if not S1.wait_for([n["fqn"] for n in env.GRAPH["nodes"]], recorder, attempts=10):
            raise RuntimeError("fixture nodes not listed")
        (out / "oracle-before").mkdir()
        bad = env.oracle(out / "oracle-before", recorder)
        if bad:
            raise RuntimeError(f"oracle mismatch before the episode: {bad[:3]}")
        fixture = Fixture(env, task, recorder, out)
        try:
            yield fixture
        finally:
            fixture.finish()
        (out / "oracle-after").mkdir()
        bad = env.oracle(out / "oracle-after", recorder)
        (out / "oracle_after_mismatches.json").write_text(json.dumps(bad))
    finally:
        S1.stop_processes(processes, handles, recorder)
        clean = S1.verify_empty((env.NS,), recorder)
        S1.stop_daemon(recorder)
        (out / "cleanup_ok").write_text(str(clean))


def score(entry, events, directory):
    return bridge.score_v2(entry, events)
