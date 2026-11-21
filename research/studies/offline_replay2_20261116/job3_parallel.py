"""Job 3: parallel calls per request, list arm vs control (PROTOCOL.md). uv run python job3_parallel.py"""
import json
import statistics
import common

episodes = [e for e in common.load_episodes() if e["group"] in ("round 1 control", "round 1 add-on arms") and e["arm"] in ("C1", "C1+LA", "C1+AG+LA")]


def calls_per_request(ep, count_items):
    out = []
    for request in ep["requests"]:
        if count_items:
            out.append(sum(c["tool"] != "final_answer" for c in request["calls"]))
        else:
            out.append(sum(u["tool"] != "final_answer" for u in request["units"]))
    return out


LIST_CALLS = {json.loads(l)["run_id"]: json.loads(l)["list_calls"] for l in (common.STUDIES / "build_round1_20261115/RESULTS_LOG.jsonl").read_text().splitlines()}


def has_list_call(ep):
    """Round 1's own count of calls that used the new list-argument type (the field `list_calls` of its results log; native list arguments of the old tools are not counted)."""
    return (LIST_CALLS.get(ep["run_id"]) or 0) > 0


def summarize(eps, count_items):
    per_request = [n for e in eps for n in calls_per_request(e, count_items)]
    if not per_request:
        return dict(episodes=0)
    return dict(episodes=len(eps), requests=len(per_request), calls=sum(per_request), mean_calls_per_request=sum(per_request) / len(per_request),
                share_two_or_more=sum(n >= 2 for n in per_request) / len(per_request),
                distribution={"0": sum(n == 0 for n in per_request), "1": sum(n == 1 for n in per_request), "2": sum(n == 2 for n in per_request), "3+": sum(n >= 3 for n in per_request)})


result = {}
models = sorted({e["model"] for e in episodes})
for count_items, label in ((False, "calls_as_responses_units"), (True, "calls_one_per_list_item")):
    block = {}
    for arm in ("C1", "C1+LA", "C1+AG+LA"):
        sub = [e for e in episodes if e["arm"] == arm]
        block[arm] = dict(total=summarize(sub, count_items), per_model={m: summarize([e for e in sub if e["model"] == m], count_items) for m in models},
                          with_list_call=summarize([e for e in sub if has_list_call(e)], count_items), without_list_call=summarize([e for e in sub if not has_list_call(e)], count_items))
    result[label] = block
# question 1 (frozen reading: pooled mean higher by >= 0.10 and in >= 3 of 4 models), using the per-response unit count
units = result["calls_as_responses_units"]
control, lists = units["C1"], units["C1+LA"]
higher = {m: lists["per_model"][m]["mean_calls_per_request"] - control["per_model"][m]["mean_calls_per_request"] for m in models}
pooled = lists["total"]["mean_calls_per_request"] - control["total"]["mean_calls_per_request"]
result["question1"] = dict(pooled_difference=pooled, per_model_difference=higher, answer_yes=pooled >= 0.10 and sum(d > 0 for d in higher.values()) >= 3)
# question 2: counterfactual requests for the list arm's calls at the control's calls per request
cr, lr = control["total"]["requests"], lists["total"]["requests"]
recorded_diff = cr - lr
expected_list_requests = lists["total"]["calls"] / (control["total"]["calls"] / cr)
counterfactual_diff = cr - expected_list_requests
# the same with the per-model control ratios
per_model_expected = sum(lists["per_model"][m]["calls"] / (control["per_model"][m]["calls"] / control["per_model"][m]["requests"]) for m in models)
result["question2"] = dict(control_requests=cr, list_arm_requests=lr, recorded_difference=recorded_diff, list_arm_calls=lists["total"]["calls"], control_calls=control["total"]["calls"],
                           expected_list_arm_requests_at_control_ratio=expected_list_requests, counterfactual_difference=counterfactual_diff,
                           share_recovered=counterfactual_diff / recorded_diff if recorded_diff else None,
                           expected_list_arm_requests_per_model_ratio=per_model_expected, share_recovered_per_model_ratio=(cr - per_model_expected) / recorded_diff if recorded_diff else None,
                           explains=(counterfactual_diff / recorded_diff >= 0.5) if recorded_diff else None)
json.dump(result, open("results_job3.json", "w"), indent=1)
print(json.dumps(dict(q1=result["question1"], q2=result["question2"]), indent=1))
