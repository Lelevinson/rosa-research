"""POST-HOC (not frozen, not the reported result): re-judge with one change, an answer wrapped as {"answer": {...}} (text ending) is unwrapped, as scorer v2.0's unwrap_answer does.
Uses the frozen judge.judge unchanged on the unwrapped object. Offline; writes posthoc_unwrap.json."""
import json, collections
from pathlib import Path
import judge as J
HERE = Path(__file__).resolve().parent
rows = [json.loads(l) for l in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
rows = [r for r in rows if r["phase"] == "full"]
def unwrap(a):
    o = J.parse_answer(a)
    return o["answer"] if o and isinstance(o.get("answer"), dict) and len(o) == 1 else a
out = collections.defaultdict(lambda: collections.Counter())
changed = 0
for r in rows:
    ok = J.judge(r["task"], unwrap(r["answer"]), r["true_heading"], r["true_x"], r["true_y"], r["turtle_still"])["success"]
    changed += ok != r["success"]
    out[(r["model"], r["arm"])]["success"] += ok
    out[("ALL", r["arm"])]["success"] += ok
res = {f"{k[0]}/{k[1]}": v["success"] for k, v in sorted(out.items())}
res["rows_changed_by_unwrapping"] = changed
(HERE / "posthoc_unwrap.json").write_text(json.dumps(res, indent=1)); print(res)
