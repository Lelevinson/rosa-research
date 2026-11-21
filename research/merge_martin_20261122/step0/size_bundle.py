"""Step 0 sizing, as pre-registered in STEP0_GATE_PREREG.md. Read-only on his RESULTS_LOG.jsonl; stdlib only."""
import json, sys, collections
SRC = "research/studies/action_dev_switch_20261118/RESULTS_LOG.jsonl"
T = 0.25
rows = [json.loads(l) for l in open(SRC)]

def size(sel, conservative=False):
    eps = [r for r in sel if not r.get("infrastructure")]
    req = sum(r["requests"] for r in eps)
    rem = 0
    for r in eps:
        x = min(r["verification_calls"], r["requests"] - 1)
        if conservative and r["task"] == "R2":
            x = 0
        rem += max(x, 0)
    return dict(n=len(eps), excluded=len(sel) - len(eps), requests=req, removable=rem,
                U=round(rem / req, 4) if req else None, with_removable=sum(1 for r in eps if min(r["verification_calls"], r["requests"]-1) > 0))

def pick(arm, model=None):
    return [r for r in rows if r["phase"] == "full" and r["arm"] == arm and (model is None or r["model"] == model)]

out = {"threshold": T, "source_rows": len(rows)}
out["control_OFF"] = {
    "qwen3.5:9b": size(pick("OFF", "qwen3.5:9b")),
    "pooled": size(pick("OFF")),
    "per_model": {m: size(pick("OFF", m)) for m in sorted({r["model"] for r in rows})},
    "conservative_R": {"qwen3.5:9b": size(pick("OFF", "qwen3.5:9b"), True), "pooled": size(pick("OFF"), True)},
    "per_task_pooled": {t: size([r for r in pick("OFF") if r["task"] == t]) for t in sorted({r["task"] for r in rows})},
}
out["sensitivity_ON"] = {"qwen3.5:9b": size(pick("ON", "qwen3.5:9b")), "pooled": size(pick("ON"))}
uq, up = out["control_OFF"]["qwen3.5:9b"]["U"], out["control_OFF"]["pooled"]["U"]
out["gate"] = {"U_qwen": uq, "U_pooled": up, "decision": "GO" if uq >= T and up >= T else "NO-GO"}
json.dump(out, open("research/merge_martin_20261122/step0/step0_results.json", "w"), indent=1)
print(json.dumps(out["gate"]))
for k in ("qwen3.5:9b", "pooled"):
    print("OFF", k, out["control_OFF"][k])
print("R", out["control_OFF"]["conservative_R"])
for m, v in out["control_OFF"]["per_model"].items(): print(" ", m, v["U"], v["requests"], v["removable"])
for t, v in out["control_OFF"]["per_task_pooled"].items(): print(" ", t, v["U"], v["requests"], v["removable"])
print("ON", out["sensitivity_ON"])
