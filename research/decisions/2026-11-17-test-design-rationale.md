# Held-out test design rationale and firing audit

2026-11-17. Custodian summary: aggregate counts only. These are fixed, purpose-built cases, not random samples or a power calculation. No held-out model results are asserted. The source protocols and verification records remain access-controlled evaluation material; do not supply their task-level content to method designers.

| Pool | Size and selection rationale | What it can and cannot show | Future change |
|---|---|---|---|
| Graph v2 | 24: eight structural categories, three cases each. A new seed reused the existing 22-node generator; the third cases used other existing structures or paired branches. Size was a balanced, manageable coverage choice, not an estimated sufficient sample. | Tests read-only dependency and breadth patterns under a synthetic static graph. Shared fixture and paired variants limit independence and generalization to other graphs or robots. | Add independently generated graphs and predeclared sampled cases; estimate uncertainty by graph as well as task. |
| Turtlesim | 24: eight categories, three cases each, with reset and controlled external changes. Turtlesim was the authorized available fallback when TurtleBot3/Nav2 installation was unavailable. | Covers a real ROS simulator and standard demo nodes, but not navigation or a physical robot. 18/24 need one targeted observation stage; three need two and three need three. Consequently most cases have little room for a multi-stage intervention. Changes settle before observation, so this is not a stale-read test. | Add separately frozen multi-stage tasks and other robot environments, with a prespecified complexity distribution and independent construction. |
| Graph original | 16: eight structural categories, two cases each, on a seeded 22-node synthetic graph. A compact balanced coverage set, not a power-derived size. | Exercises structural diversity, but shares the generator and categories with graph v2 and is not an independent family of environments. | Include independent fixture generators and seeds; report this pool separately, not as 16 independent environments. |
| Stale-value | 12: three targets crossed with four checkpoint types. The factorial count provides a compact check of temporal triggering and instrumentation. | Tests answer-time truth and trigger coverage under an externally controlled change. Shared target mechanism and small number of targets limit breadth; not evidence of general dynamic-world performance. | Add independent change mechanisms and targets in a new frozen pool, including missed-trigger tests and fixed scoring. |

All graph/turtlesim reference floors count targeted observation stages plus an answer, not unrestricted optimal requests; ordinary enumeration can beat that conditional reference at greater native cost. Both v2 pools had 24/24 model-free reference verifications; the original had 16/16 under its revised conditional floor, and stale-value r2 had 12/12 normal instrumentation cases plus three scored missed-trigger checks. These are fixture and scoring checks, not model performance. Report correctness and all costs, including failures, by pool and condition. The preflight caused a disclosed partial exposure to method summaries during construction; the pools were not perfectly blind.

## Firing opportunity audit

| Pool | Tasks | Sweep opportunity | Name-fix opportunity |
|---|---:|---:|---:|
| Graph v2 | 24 | 2 | 13 |
| Turtlesim | 24 | 0 | 9 |
| Graph original | 16 | 2 | 9 |
| Stale-value r2 | 12 | 0 | 0 |

Sweep: count a task once if a single stage in its saved targeted verification witness has at least three sibling reads using the same tool. Original-graph tool IDs were joined to the saved observation records; v2 uses the recorded stage calls. Stale-value's ordered reference has no such stage. This is a witness-based lower bound on structural opportunity, not an exhaustive search of all legal routes. It does not assert that a prior list was observed, that two calls share a request and arguments, that an unread sibling remains, or that Round 2's live rule fires. Other routes could change the count.

Name fix: count a task once if its declared answer includes a slash-qualified ROS entity name in a value or nested key, excluding type identifiers. Such a name can be shortened syntactically; the count does not establish an actual model shortening, a unique ledger match, a safe rewrite, or an improvement. Both columns are independent and can overlap. The frozen sets are not changed in response to this audit.
