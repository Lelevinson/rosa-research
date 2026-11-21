# Codex proposals for the ROSA idea freeze

2026-11-21, Asia/Taipei. Prompt 2 with the 19:30 update. Development traces, seeds 5–8, FULL only. **No candidate is ready to freeze as the paper method.** The clearest issue is a missing direct service-provider operation on the current menu. A bounded exact lookup is worth distinguishing from ordinary batching, but the opportunity is concentrated in one task. The empty-blacklist conversion belongs in a matched executor control.

I replayed 288 saved episodes at checkout `245e72c159f99fb5f0ad48e5ba4f3eca161d588d` with 1,655 requests, 828 above the task floors and 45 unsupported answers. The numbers below are retrospective opportunity ceilings. Failure exposure counts an unsupported episode once when the filter hits, with recovery unknown. Ceilings overlap. The [offline counting script](#offline-counting-script) is embedded in this file. [Loss-map report](../loss_map_20261120/REPORT.md) · [Raw traces](../../_artifacts/exam/lossmap/runs_all/) · [Frozen labels](../loss_map_20261120/labelled_lossmap.jsonl)

**Independence and source limits.** My initial full-file read displayed the restricted Prompt 3, and an early search surfaced one excerpt from the Claude-lane protocol before I narrowed the paths. The proposal review cannot claim full blinding. I used the two 19:30-authorized reports as comparison evidence. Their reported findings rule out adopting the tested input rebinding, reverse lookups, inline list values and no-progress stopping. The latter live list-value run was frozen C, with a post-hoc B interpretation after evidence-credit correction, and native operations still rose 11%. A read-only `git ls-remote` retry outside the network sandbox verified that the two remote member branch heads matched the cached refs. The verified teammate ref `origin/member/krln` at `26ac7bd` contained shared protocol files and no member snapshot, so there was no published teammate study to check for overlap. [Offline candidate report](claude_lane/REPORT.md) · [LISTVAL live report](../listval_live_20261120/REPORT.md)

## Trace measurements

**Q1 · Answer-name rewrite.** Applying the existing `namefix_rule.rewrite_answer` with the `answer_gate.allowed_names` ledger changed 11 final answers. **9 of the 26** frozen wrong-conclusion cases became supported, with zero supported-to-unsupported changes across all 288. Flips by model: lfm3 **1**, Qwen **1**, gpt-oss **0**, bonsai **7**. All nine used `final_answer`, so restricting the replay to calls eligible for the live finish hook gives the same result. The code replays the answer with the same saved evidence rows and frozen scorer. [Rewrite rule and finish hook](../name_fix_applied_20261117/) · [Counting script](#offline-counting-script)

**Q2 · Parameter discovery.** **107/107** paired list calls had the first subsequently read parameter name in the task text as a whole name before the list. Zero relied on an earlier result alone. Per model, paired calls out of successful lists: lfm3 **21/24**, Qwen **37/37**, gpt-oss **1/1**, bonsai **48/49**. The list was unnecessary to obtain the parameter *name* in those pairs. Node identity, applicability and scripted observation timing are separate conditions. Counts are per list call with a successful same-node get in a later request. [Counting script](#offline-counting-script)

**Q3 · Service provider.** The saved v2 task supplies the **absolute** service name and asks for its providing node **and** service type. In the 12-tool menu, `ros2_service_info` invokes `ros2 service type`. `ros2_service_list` gives names. `ros2_node_info` supplies the indirect witness under **Service Servers**, indexed by node. The original ROSA ROS 2 registry has no direct service-to-provider wrapper. Original ROSA's **ROS 1** `rosservice_info` probes the named service and returns TCPROS headers including the responding node's `callerid` on the checked upstream server implementation. The ROS 2 menu rule excludes that ROS 1 tool. The ROS 1 CLI's separate `rosservice info` command explicitly looks up and prints `Node:`. The installed Jazzy `ros2 service info` source prints type and counts. Newer upstream verbose endpoint support is a distinct deployment capability. [v2 task](../headroom_diagnostic_20261112/stage3_tasks.json) · [Menu rule](../../decisions/2026-11-17-menu-coverage-and-rule.md) · [ROSA ROS 2 tools](../../../src/rosa/tools/ros2.py) · [ROSA ROS 1 tools](../../../src/rosa/tools/ros1.py) · [ROS 1 probe and CLI](https://raw.githubusercontent.com/ros/ros_comm/noetic-devel/tools/rosservice/src/rosservice/__init__.py) · [TCPROS server header](https://github.com/ros/ros_comm/blob/noetic-devel/clients/rospy/src/rospy/impl/tcpros_service.py#L263-L270) · [ROS 2 verbose service info](https://github.com/ros2/ros2_documentation/blob/rolling/source/Releases/Release-Lyrical-Luth.rst#verbose-service-information-ros2-service-info---verbose)

The exact `Service Servers` relation was present in **7/7 supported v2 episodes and 0/9 unsupported episodes**. Five of those nine had the frozen “facts present” label. The scorer accepts the provider name and service type as separate text witnesses even when they occur in unrelated results. Keep the frozen labels for comparison. At least five of the 26 nominal wrong conclusions lacked this required relation. This also explains why a name rewrite alone cannot fix v2. [Task support definition](../headroom_diagnostic_20261112/stage3_tasks.json) · [Scorer `support_missing`](../residual_failures_20261115/scorer_v2.py) · [Counting script](#offline-counting-script)

**Q4 · Exact argument values.** All 28 gpt-oss **blacklist type rejections** were JSON strings: `""` ×25, `"$"` ×1, `"None"` ×1, `"none"` ×1. The loss-map report's illustrative `{}` does not appear among them. K3 can read the empty string as no filter, using `[]`. The trace shows **23** immediately following successful single-call retries with the same remaining arguments and an omitted or empty blacklist. K2 can wrap the other three strings as singleton regex arrays, but intent is ambiguous. `"$"` as a blacklist matches every entity under the current wrapper, and the two spellings of “None” can filter actual names. Treating any of these three as “no filter” requires new semantics. [Prior conversion `convert`](../arg_type_retry_offline_20261119/arg_type_retry.py) · [ROSA `get_entities`](../../../src/rosa/tools/ros2.py)

| Model | Rejected regex values by tool call |
|---|---|
| lfm3 | `*` ×3, `*c*`, `*cedar*`, `*kestrel*` ×2 |
| gpt-oss | `*` ×1, with `blacklist: null` |
| bonsai | `*cedar*` ×2, `*cedar_reset$`, `*chisel_t`, `*e1h*`, `*e1h*/*`, `*e1h*/flow*`, `*ember/mistral*`, `*reef_t`, `*reset` ×2, `*reset$` ×7, `*thistle*` |
| Qwen | 0 |

These were **28 calls across 27 requests**. They already pass the string type check. ROSA adds `.*` around the raw pattern, so the leading `*` yields a regex parsing error. Fixing a string by stripping or escaping stars, or translating it as a glob, chooses a meaning the trace does not establish. [Tool code](../../../src/rosa/tools/ros2.py) · [Counting script](#offline-counting-script)

## Proposals and decision record

1. **Expose an exact service-provider operation when the deployment can supply it.** **Ceiling:** **166/828 requests and 9/45 failures** in the v2 stratum. Per model in lfm3/Qwen/gpt-oss/bonsai order, requests **35/7/12/112** and failures **4/0/1/4**. This deliberately broad route ceiling includes a backend abort and downstream cap tails. The five false “facts present” cases give direct evidence of a missing witness. The known `/plant32/cedar_reset` in lfm3 v2 seed 6 could have been queried on request 1. A tool for that lookup gives the model a direct way to acquire the relation.

   **Rule and feasibility (6–8 hours for a study adapter).** Add a read-only `service_providers(service: absolute_name)` schema beside the existing tools. For a valid name, use the deployment's certified endpoint query when available. Otherwise use a fresh bounded ROS graph node enumeration and `get_service_names_and_types_by_node` on each in-scope node. Compare the requested service by exact full name. Return its observed provider FQNs and service types as paired records, with query time and coverage status. Return all matches. Timeout, graph instability, exhausted budget and unsupported introspection yield `incomplete` with any observed positives, so zero rows in a partial read cannot certify absence. The model still selects the operation and answers. In the study harness, change `Arm.base_menu` and `Arm.wrap_tools`, route an adapter through `Arm.execute`, and register it alongside the current ROS 2 readers in `src/rosa/tools/ros2.py` only if later integration is approved. The adapter uses deployment graph primitives and no task catalogue. Installed Jazzy exposes the per-node query. Its direct by-service endpoint API is unavailable in the inspected Python source.

   **Closest comparisons and stop rule.** The dead-end and authorized offline reverse-lookup studies used name clues or lists of observed paths around failed/serial probes. Their look-alike and size problems remain. Here the action is an explicit, exact typed edge query for a registered service, independent of earlier errors or a guess based on the service's spelling. In published tool use, Paranjape et al.'s ART (2023, arXiv:2303.09014, §§3.2–3.3) selects demonstration-conditioned tool steps and runs matched tools. ROS's own service endpoint introspection is the closer engineering precedent. First compare a bounded typed scan with the existing ordinary batched `node_info` sweep using the same exact predicate and exposed evidence. Freeze the relational witness before any live comparison, and include absent services, multiple providers and a graph-change case. Stop on a falsely asserted provider or absence, any lost supported answer due to the mechanism, or a tie against the batched sweep on supported completion and whole-episode requests/tokens with native work charged. **BLOCKED / NOT YET JUSTIFIED as a paper mechanism:** real query cost, parity with the bounded sweep and independent exposure beyond v2 are unknown. A stock-capability extension is a valid integration result if the ordinary control ties. [Dead-end lookup](../dead_end_lookup_offline_20261118/REPORT.md) · [Offline reverse lookup](claude_lane/REPORT.md) · [ART](https://arxiv.org/pdf/2303.09014#page=5)

2. **Put independent, heterogeneous reads in one typed tool call.** **Ceiling:** **116/828** requests, **20/45** unsupported episodes exposed, by model **37/17/24/38** requests and **9/0/2/9** episodes. The script screens adjacent successful pairs with at most four calls total, at least two tool names, and the frozen independence label. It skips scripted-change tasks and rejected predecessors and caps by each episode's attributed serial bucket. There are 129 raw subsequent requests under this screen. Some operations could simply be skipped, and the classifier can mistake semantic dependencies for independence. One plausible grouping in gpt-oss h4 seed 8 is the `node_info` read on oasis followed by the `param_get` for zephyr's already named gain.

   **Rule and feasibility (6–8 hours).** Expose an optional `read_many(calls)` with a discriminated argument schema derived from the certified read registry, two to four fully bound items. Keep normal singleton tools. Validate the whole container and admission before dispatch, then execute through the existing read handlers in submitted order within the ordinary budget. Return each typed result or soft error with its item index. Empty, unauthorized, over-budget and forward-reference calls fail before dispatch. Use the ordinary single call for dependent, timing-sensitive or side-effectful operations. Record separate result rows for each observation. The model selects group members. The executor provides one submission and one observation boundary for the group. Change `harness.py` `Arm.wrap_tools`, `Arm.execute_extra` and schema validation, and provide a scorer adapter for per-item receipts. The cost includes any duplicated schema, grouping syntax and speculative reads.

   **Closest comparisons and stop rule.** Build Round 1 list arguments shared a tool and most arguments across entities, with adoption in only 4/80 episodes and no attributable request gain. This design also groups different read operations with separately bound arguments. Kim et al. (2024, arXiv:2312.04511, §§3.1–3.3) dispatch a model-generated DAG and substitute prior results into dependent tasks. Here the contents of one group are fully bound at submission, with no planner request or result substitution. FULL already batched in 169 requests. The strong control gets the same operations and permissions, a deconflicted batching prompt, and verified native multi-tool adoption. For a later bounded comparison, freeze eligible independent pairs, check that the new schema reaches each backend, then test whether group submissions remove model boundaries beyond native multi-tool calls. Stop on missed support/timing, insufficient actual group adoption to beat the control, or no whole-episode net request/token gain. **BLOCKED / NOT YET JUSTIFIED:** only an interface adoption difference is plausible. The strongest ordinary control already dispatches the same fully bound reads once emitted together. [Build Round 1](../build_round1_20261115/REPORT.md) · [LLMCompiler](https://arxiv.org/html/2312.04511#S3)

3. **Let list callers specify literal matching explicitly.** **Ceiling:** **27/828** format requests and **7/45** failures exposed, by model **7/0/1/19** requests and **2/0/0/5** failures. Separately the K3 empty-blacklist replay covers **23/828**, all gpt-oss, with one unsupported episode exposed. Count K3 as shared plumbing and charge it equally. `*reset$` in bonsai v2 seed 7 is an example where we know the failure but cannot recover the intended filter by type conversion.

   **Rule and feasibility (4–6 hours).** Add a discriminated optional filter to the graph-list schemas: `all`, `contains(text)`, `suffix(text)`, or `regex(pattern)`. Return the ordinary names with the mode applied. Retain the legacy valid regex path and its exclude semantics for existing callers. Reject requests that send both forms or that carry an invalid explicit regex before executing a list. Literal matching uses case-sensitive string operations and does not strip any characters. Configure this per list-tool interface using its filter contract, with no knowledge of graph names or task types. Add this in a study-local wrapper wired by `Arm.wrap_tools`, reusing the list functions and their post-fetch filter behavior at `get_entities`. This changes the input accepted by the executor rather than relying on a reminder about regex.

   **Closest comparisons and stop rule.** The 19 November argument-type study found sparse savings in its frozen retry measure. It checks value/schema representation. Explicit literal modes give callers a way to express the intended predicate using a valid input in the first place. Willard and Louf (2023, arXiv:2307.09702, §§2–4) enforce formal sequence validity by masking generated tokens. A valid JSON string alone does not encode the intended ROS filter predicate. Use a shared K3 control with ordinary regex and the same soft errors. Freeze filter equivalence tests for existing valid calls, then stop if a predicate changes meaning, supported completion falls, or the rate of rejected filter plus corrective retry requests fails to drop without shifting cost into broad lists. **Conditionally retained as interface engineering.** Its ceiling and unknown model adoption do not justify adding it to the paper method before the freeze. [Type-retry report](../arg_type_retry_offline_20261119/REPORT.md) · [Guided generation](https://arxiv.org/html/2307.09702)

### Evaluation boundaries

The proposals act on tool inputs and actual observations. Keep the model, tasks, fixture revisions, permissions, query budgets and scorer fixed within a comparison, with a prospectively frozen evidence adapter if a new representation needs one. Report supported-complete first, then whole-episode requests, input/output tokens, attempted native dispatches and successful observations, time, setup and wire/schema cost. Preserve original traces and event-level adoption in a dated study bundle and matching raw run location. A later paper comparison still needs the released baselines and custodian-held evaluation specified by the contract. [Paper goal](../../PAPER_GOAL_CONTRACT.md) · [Research gates](../../ROSA_RESEARCH_CONTEXT.md#12-research-governance-prior-art-firewall-and-anti-loop-rules-added-2026-11-10)

**Skip before freeze.** The 157 repeats include calls whose value can change between requests. Fewer dispatches from memoization would not imply fewer requests, and the repeat nudge and forced-stop evidence supplies concrete early-stop harm. The 218 name-guess/recovery requests also do not justify reusing the failed rebinding rules. Keep the replay-supported output rewrite separate from a claim about recovering facts or reducing requests. Leave the 130 unexplained requests unassigned. The 36 rejected-call retries are counted across all 325 requests labelled serial-batchable; subtracting all 36 from the attributed 248 would mix populations. The study's 828 is an episode-wise positive excess, so it also differs from the net subtraction `1655 - 832 = 823`. [Classifier notes](../loss_map_20261120/CLASSIFIER_NOTES.md) · [Repeat-finish study](../repeat_finish_nudge_20261118/REPORT.md) · [19:30-authorized offline report](claude_lane/REPORT.md)

### FULL path checked

`run_lossmap.py` delegates the worker to `run_think.py:episode`. `ThinkArm` starts from C1 and keeps FULL thinking options off. Its `visible_schemas` uses the 12 domain readers plus the synthetic finish tool. `PilotTool._parse_input` runs `strict_error` before Pydantic, and the soft exception path passes validation/execution errors as observations. `Arm.execute` checks offered tools and blocks writes before native dispatch through `call_inner`. FULL inherits the finish behavior in `Arm.final_answer_tool` and `PilotExecutor._get_tool_return`. It accepts a nonempty answer object and ends without another model request; the answer gate and output rewrite are separate arms. [Loss-map adapter](../loss_map_20261120/run_lossmap.py) · [Thinking runner](../thinking_escalation_20261119/run_think.py) · [ThinkArm](../thinking_escalation_20261119/think_arm.py) · [C1 harness](../small_model_harness_20261115/harness.py)

## Offline counting script

Run from the repository root. This extracts the embedded script and executes it with bytecode writes disabled. It imports the existing parser and frozen scorer, reads the development traces and prints only counts.

```sh
sed -n '/^```python$/,/^```$/{ /^```/d; p; }' \
  research/studies/idea_search_20261120/CODEX_PROPOSALS.md | python3 -B
```

```python
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

studies = Path("research/studies")
sys.path[:0] = [str(studies / "loss_map_20261120"),
                str(studies / "name_fix_applied_20261117")]
import classify as C
import namefix_rule as N

labels = [json.loads(line) for line in
          (C.HERE / "labelled_lossmap.jsonl").read_text().splitlines()]
rows = {r["trace_path"]: r for r in C.load_rows("lossmap")}
tasks = C.all_tasks()
counts = Counter()
batch_tools = {
    "ros2_node_list", "ros2_topic_list", "ros2_service_list", "ros2_node_info",
    "ros2_topic_info", "ros2_service_info", "ros2_param_list", "ros2_param_get",
}

def is_regex_error(unit):
    return "failed: error:" in unit["text"] and "pattern" in unit["args"]

def empty_filter(unit):
    return (unit["harness_error"] and unit["args"].get("blacklist") == ""
            and "field 'blacklist'" in unit["text"])

def ignore_empty_blacklist(args):
    return {k: v for k, v in args.items() if k != "blacklist" or v not in (None, "", [])}

def clean(units):
    return bool(units) and all(
        u["tool"] in batch_tools and u["ok"] and u["items"]
        and all(c["ok"] for c in u["items"]) for u in units
    )

assert len(labels) == len(rows) == 288
assert sum(e["excess"] for e in labels) == 828
assert sum(not e["supported"] for e in labels) == 45

for e in labels:
    m, path = e["model"], e["trace_path"]
    ep = C.E.parse("lossmap", rows[path], tasks)
    assert ep["supported"] == e["supported"], path
    events = [json.loads(line) for line in Path(path).read_text().splitlines()]
    requests = ep["requests"]
    prior, outputs = [], []
    hits = defaultdict(set)
    provider_witness = False

    for i, request in enumerate(requests):
        units = request["units"]
        kind = e["request_types"][i]
        for u in units:
            args, output = u["args"], u["output"]
            if u["harness_error"] and "field 'blacklist'" in u["text"] and "blacklist" in args:
                counts["blacklist_call", m, json.dumps(args["blacklist"])] += 1
            if is_regex_error(u):
                counts["regex_call", m, args["pattern"]] += 1
            if u["tool"] == "ros2_node_info" and isinstance(output, dict):
                for text in output.values():
                    if isinstance(text, str) and "  Service Servers:\n" in text:
                        section = text.split("  Service Servers:\n", 1)[1].split("  Service Clients:", 1)[0]
                        provider_witness |= any(
                            line.strip().startswith("/plant32/cedar_reset:")
                            for line in section.splitlines()
                        )

        if units and kind == "format" and all(is_regex_error(u) for u in units):
            hits["selector"].add(i)
        if len(units) == 1 and empty_filter(units[0]) and i + 1 < len(requests):
            later = requests[i + 1]["units"]
            if len(later) == 1:
                u, v = units[0], later[0]
                if (v["ok"] and u["tool"] == v["tool"]
                    and ignore_empty_blacklist(u["args"]) == ignore_empty_blacklist(v["args"])):
                    hits["empty_retry"].add(i)
        if i and kind == "serial_batchable" and "chg" not in e["task"]:
            prev = requests[i - 1]["units"]
            if (clean(prev) and clean(units) and len(prev) + len(units) <= 4
                and len({u["tool"] for u in prev + units}) > 1
                and e["request_types"][i - 1] not in {"repeat", "name_guess", "name_recovery"}):
                hits["batch"].add(i)

        for call in request["calls"]:
            if call["tool"] != "ros2_param_list" or not call["ok"]:
                continue
            counts["Q2", m, "successful_lists"] += 1
            first = next((c for r in requests[i + 1:] for c in r["calls"]
                          if c["tool"] == "ros2_param_get" and c["ok"]
                          and c["entity"] == call["entity"]), None)
            if first is None:
                continue
            name = first["args"]["param_name"]
            # A trailing period at the end of a sentence is punctuation.
            token = re.compile(r"(?<![\w.])" + re.escape(name) + r"(?!\w|\.\w)")
            source = ("task" if token.search(ep["task_text"]) else
                      "earlier_result" if any(token.search(t) for t in prior) else "neither")
            counts["Q2", m, source] += 1
        for u in units:
            if u["tool"] != "final_answer" and not u["harness_error"] and u["output"] is not None:
                outputs.append(u["output"])
                prior.extend(C.ag.successful_text_parts(u["output"]))

    answer, source = C.E.v2.episode_answer(events)
    after = (N.rewrite_answer(answer, C.ag.allowed_names(ep["task_text"], outputs), [])
             if isinstance(answer, dict) and answer else answer)
    supported = C.E.v2.score_task(ep["task_def"], after, ep["rows"])["supported_complete"]
    counts["Q1_changed", m, source] += after != answer
    counts["Q1_down", m, source] += e["supported"] and not supported
    if supported and not e["supported"]:
        counts["Q1_up", m, str(e["failure"])] += 1

    if e["task"] == "v2":
        counts["provider_excess", m, "v2"] += e["excess"]
        counts["provider_witness", m, str(e["supported"])] += provider_witness
        counts["provider_episodes", m, str(e["supported"])] += 1
        if not provider_witness and e["failure"] == "wrong_conclusion_facts_present":
            counts["provider_misclassified", m, "v2"] += 1
    for tag, indices in hits.items():
        bucket = "serial_batchable" if tag == "batch" else "format"
        counts[tag, m, "all_hit_requests"] += len(indices)
        counts[tag, m, "attributed_ceiling"] += min(len(indices), e["attributed"][bucket])
        counts[tag, m, "unsupported_exposure"] += not e["supported"]

for key, value in sorted(counts.items()):
    if value:
        print(*key, value, sep="\t")
```
