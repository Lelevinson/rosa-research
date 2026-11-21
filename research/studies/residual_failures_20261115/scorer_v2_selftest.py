"""Self-test of scorer v2: minimal routes pass, wrong answers fail, new rules behave as decided. Run: uv run python scorer_v2_selftest.py"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import scorer_v2 as s, view
PILOT = HERE.parent / "small_model_harness_20261115"
ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)
# minimal routes of the E1h fixture (floor-check logs) and wrong answers
base = HERE.parents[1] / "_artifacts/runs/small_model_harness_20261115/e1h_floorcheck"
for tid in ["e1h_amb_1", "e1h_amb_2", "e1h_abs_1", "e1h_abs_2", "e1h_chg_1", "e1h_chg_2"]:
    t = view.TASKS[tid]; d = json.loads((base / f"minimal_{tid}.json").read_text())
    rows = [dict(name=e["tool"], args=e["args"], given_args=e["args"], output=e["result"], text=json.dumps(e["result"]), ok=not s.s1.ERROR.search(json.dumps(e["result"]))) for e in d["log"]]
    check(f"{tid}: minimal route supported", s.score_task(t, d["answer"], rows)["supported_complete"])
    check(f"{tid}: no trace is not supported", not s.score_task(t, d["answer"], [])["supported_complete"])
# rule 1: relative param read supports; relative node_info failure does not show absence
t = view.TASKS["p3"]
mk = lambda name, args, out, ok=True: dict(name=name, args=args, given_args=args, output=out, text=json.dumps(out), ok=ok)
rows = [mk("ros2_param_get", {"node_name": "plant32/quartz", "param_name": "next_node"}, {"next_node": "String value is: /plant32/beacon\n"}),
        mk("ros2_param_get", {"node_name": "plant32/beacon", "param_name": "next_node"}, {"next_node": "String value is: /plant32/juniper\n"}),
        mk("ros2_param_get", {"node_name": "plant32/juniper", "param_name": "setpoint"}, {"setpoint": "Integer value is: 873\n"})]
check("rule 1: relative-name param reads support the task", s.score_task(t, t["answer"], rows)["supported_complete"])
a = view.TASKS["e1h_abs_2"]; name = a["answer"]["node"]
rel = name.lstrip("/")
check("rule 1: failed relative node_info is NOT absence evidence", not s.absence_shown(name, [mk("ros2_node_info", {"nodes": [rel]}, {rel: {"error": "Unable to find node"}}, ok=False)]))
check("rule 1: failed relative param read IS absence evidence", s.absence_shown(name, [mk("ros2_param_get", {"node_name": rel, "param_name": "rate"}, {"error": "Node not found\n"}, ok=False)]))
check("rule 1: failed exact node_info is absence evidence", s.absence_shown(name, [mk("ros2_node_info", {"nodes": [name]}, {name: {"error": "Unable to find node"}}, ok=False)]))
# rule 2
check("rule 2: wrapper alone is unwrapped", s.unwrap_answer(s.last_json_object('done {"answer": {"a": 1}}')) == {"a": 1})
check("rule 2: wrapper with another key is not unwrapped", s.unwrap_answer({"answer": {"a": 1}, "b": 2}) == {"answer": {"a": 1}, "b": 2})
check("rule 2: non-object answer value is not unwrapped", s.unwrap_answer({"answer": "x"}) == {"answer": "x"})
print("SELFTEST OK" if ok else "SELFTEST FAILED")
