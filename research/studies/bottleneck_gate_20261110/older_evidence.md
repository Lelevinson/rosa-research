# Older graph evidence audit — 2026-11-10

Read-only investigation; no experiment/model/ROS execution. The new parser `audit_older.py` reads ZIP bytes with Python's standard library and writes only diagnostic artifacts. It does not import or execute the historical auditor. `older_manifest.json` records SHA-256 for every selected original member, saved scorer, task manifest, and scoring source. `older_calls.jsonl` contains every dispatch, exact raw output/native record and request linkage from the selected 148 episodes; `older_models.jsonl` preserves all 426 recorded model completions with raw proposals and per-turn usage; `older_model_proposals.jsonl` indexes their 409 proposals separately from dispatches; `older_episodes.jsonl` retains requests, answers, score provenance and costs. Counts are exhaustive within these two held-out blocks, not within all historical ROSA runs.

## Inventory and boundary

Source archive: `/home/levinsonchen/project/rosa-research-archive/research/raw/rosa-round28-external-review.zip`, 22,343 ZIP members. It contains the earlier Round27 held-out episode corpus as well as Round28. Archive SHA-256 and member hashes are in the machine-readable manifest. Reading each selected member exercises that member's ZIP CRC; this audit does not claim full-archive CRC verification or manifest reconciliation. No malformed JSON was encountered in the 148 selected episodes or selected scorer files.

| Corpus | Original episode member prefix | Coverage | Frozen evaluation material |
|---|---|---|---|
| Round27 | `research/raw/round27-mission-v1/heldout-v1/episodes/` | 64/64 episodes; 260/260 dispatches | `research/experiments/round27/heldout_tasks.json`, `audit_study.py`, saved `research/results/round27_heldout_audit.json` |
| Round28 | `research/raw/round28-mission-v1/heldout-v1/episodes/` | 84/84 episodes; 292/292 dispatches | `research/experiments/round28/heldout_tasks.json`, `audit_study.py`, saved automatic and adjudicated heldout audits, `round28_answer_adjudication.json` |
| Strong tool-menu retrieval | Previous checkout `research/menu_retrieval/{protocol.json,audit.py,run_study.py,menu_policy.py}` | Source preserved; no original menu episode traces found | Auditor source inspected; its supported-completion definition requires factual target match, delivered native acquisition, and stable oracle |

Search for the menu corpus inspected the previous checkout, archived checkout, and all project ZIP central directories smaller than 150MB. No menu raw `trace.jsonl` corpus was found. This is a bounded absence finding, not proof that no other disk or remote copy exists. The quoted 10/12 versus7/12 cannot be independently replayed from menu traces found here. Menu source copied inside diagnostic/pilot snapshots is not the menu experiment's episode evidence.

## Dispatch ledger

| Measure | Round27 | Round28 |
|---|---:|---:|
| Episodes |64|84|
| Tool dispatches |260|292|
| `allowed=false` |0/260|0/292|
| Native wrapper `ok=false` |9/260|10/292|
| Endpoint-bearing calls |192|208|
| Endpoint name in earlier successful episode graph response |184/192|188/208|
| Exact same tool+arguments already dispatched this episode |11/260|9/292|
| Demonstrated stale-incarnation calls |0 identified; freshness not measured|0 identified; freshness not measured|

Membership means only that the prior response advertised an exact endpoint string. The ledger records its observation time. It does not establish current freshness, process incarnation, semantic suitability, or model consumption of that observation. Identical arguments at two times do not prove a redundant observation: all same-time equivalence fields remain unknown. Grounding counts above include successful node graph results, not inferred process identity.

The nine Round27 failures are eight reads of deliberately absent AMCL pose (one in each arm/repetition of h08) and one GetParameters request with `{}` instead of explicit names (`1-r27h04_two_parameter_owners-original_sync.json`). The ten Round28 failures are seven reads of deliberately absent AMCL pose (h05 across arms) and three unapproved `battery_charge` parameter guesses in original_sync h11. These are unsupported/absent sources and an ordinary argument error, not evidence of an endpoint disappearing after earlier discovery. The source-side `allowed=true` and backend `ok=false` are distinct validation boundaries. A failed wrapper does not prove an actual DDS request was sent.

`older_models.jsonl` preserves each recorded model completion's calls, content and usage (Round27:181 completions/184 proposals; Round28:245 completions/225 proposals). Compiler selections account for32 and56 proposals respectively; these are model proposals, not native reads. Exact name/argument/time matches to later dispatches are candidate links only and do not establish causal identity. The parser counts those records and their recorded total tokens; these counts do not certify attempted calls missing from completion arrays, provider pricing, or latency savings. No model-turn savings are estimated from native operation durations.

## Correctness and alternatives

Saved frozen Round27 scores, aggregated without rerunning the scorer:

| Arm | Episodes | Native complete | Factual complete | Exact scope |
|---|---:|---:|---:|---:|
| graph_dynamic |16|10|6|7|
| graph_sequential |16|10|6|7|
| original_sync |16|14|6|4|
| prompted_async |16|12|4|5|

Two episodes per arm ask for deliberately unavailable localization; all-episode factual counts should not be compared to a 14-feasible denominator without stating that distinction. Native completion and factual completion differ markedly. These are saved automatic score facts, not a new independent adjudication of every answer.

Saved Round28 post-closure adjudicated full factual+supported completion among eight feasible tasks: original_sync8/8, prompt_compiler8/8, old_graph7/8, selective6/8, no_gate8/8, no_coverage8/8, prompted_async3/8. Automatic scores remain a separate archive member. The field `strict_supported_answer` alone is not full completion: an answer can support its assertions while omitting requested fields. This audit requires factual completion as well when reporting full feasible success. Representation/adjudication corrections must not be called fresh runtime gains.

Direct original-event witnesses:

1. Round27 `0-r27h05_grid_shape_and_lifecycle-graph_dynamic.json` requests occupancy entry count, width, height, **and lifecycle label through the child's own state service**. Calls acquire graph and map service only. Final answer includes count/width/height and omits label. This is a missing acquisition/obligation, not malformed GetMap data or stale graph identity. The source response advertises the child's GetState endpoint.
2. Round28 `0-r28h04_child_and_supervisor-selective.json` correctly compiles three fields including child lifecycle label. Dispatches acquire map parameters, manager node_names, and manager.active but no child GetState. Final answer admits label unavailable and says it requires GetState, although that endpoint was in the graph. This is execution/fallback/acquisition incompleteness after correct compilation, not automatically compiler error or unavailable native data.
3. Round28 `0-r28h09_total_and_comparison-selective.json` correctly compiles `sum_rgb` and `red_above_green`. Its dispatch outputs include an earlier `sum_rg` and later **`sum_rgb`**, but final answer reports `sum_rg:155` and the Boolean. This is a model rendering/source-scope error despite eventual acquisition. Temporal graph admission does not address it.

These witnesses support prioritizing source-qualified obligation retention and final rendering correctness as a *measurement target*. They do not justify another task-to-field compiler: the older runs already supplied application-specific declared fields and typed projections, and the strong compiler control matched or beat selective admission. Transfer to unadapted ROSA remains unestablished. The exact ordinary comparator is the strongest prompt_compiler/no_gate control with identical typed tools, source-qualified field obligations, batching, budgets and independent scoring; improvements against original defaults alone are insufficient.

## Recommendation

No new temporal-admission algorithm is supported by this corpus. No stale-call savings can be estimated from absent AMCL failures, and naive duplicate caching would erase observation-time semantics. The most informative next measurement is a separately authorized, frozen diagnosis separating (a) requested evidence never acquired, (b) valid evidence acquired but omitted/misattributed, and (c) actual stale endpoint proposals, on unchanged strong ROSA across two stock applications. Preserve exact proposals, delivered tool outputs, native failures, observation timestamps, final answers and independently scored obligations. Keep deliberately injected churn as stress evidence separate from natural task frequency.
