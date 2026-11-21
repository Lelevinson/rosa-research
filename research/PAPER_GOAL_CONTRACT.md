# Paper goal contract (owner's stated goal, written down so drift is visible)

Source: the owner (Levinson), recorded 2026-11-14, updated 2026-11-15. Every collaborator checks future decisions against it.

## The goal
A real research paper, the kind people mean by "paper". Not a research log, not a diagnostic-only report. The method need not be scientifically unprecedented; adapting and combining published ideas is acceptable if it is not an exact copy and is shown to work better in our setting (small models, NASA/JPL ROSA). Training-free and plug-and-play. Wall-clock time is not a goal metric.

## A "real paper" here must have all of these
1. One clear research question and a claim that can be wrong.
2. A built method/system, described precisely enough to reimplement (rules, inputs, outputs).
3. Related work that positions it honestly against the closest papers (MetaTool 2609.13335, Forge CAIS 2026, StateFlow, SCA, CMTF, Less-is-More, plan-then-execute, ToolScan/AgentErrorTaxonomy).
4. Evaluation strong enough for a reviewer:
   - published baselines (MetaTool as released, Forge as released)
   - the strongest simple control (deconflicted prompt, batching allowed and shown to be used)
   - several models (1.7B–20B)
   - frozen held-out tasks, run once
   - multiple runs per task
   - confidence intervals
   - at least one simulated robot environment (virtual robot testing is required; real robots later)
     - Owner clarification, Nov 17: this means tasks where the ROBOT ACTS in the simulation (e.g., move it, command it), not only questions asked about a simulated robot. Intended progression: small question/inspection tasks first, then action tasks in a virtual robot. The earlier AI reading ("same question tasks on a simulated robot") was never checked with the owner and is superseded. Scope for this paper (small guarded turtlesim action pool vs. future work) pending a Codex check of original ROSA's action-capable tools and a group decision before the Sat Nov 21 freeze. If action tasks are in, the menu rule must allow certified, guarded action tools (method change, decide before the freeze).
5. Ablation: each part switched off to show what it contributes.
6. Honest limitations section.
7. Every result recorded in one results log from the first run on.

## Novelty and "not new" judgments (applies to EVERY AI collaborator: Claude, Claude Code, Codex, ChatGPT)
- Never call our work "the same as" or "not novel versus" a paper on the basis of an abstract, summary or shared general idea.
- Such a judgment requires a side-by-side comparison of the actual mechanisms, from source code or the full method section. Ideally it also requires running both on our tasks.
- State which parts are shared, which differ, and what evidence the comparison used.
- Likewise, never declare a failure class "unfixable" without hand-checked traces and an attempted generic fix.
- An unverified similarity or limitation is a hypothesis and must be labeled as one.

## Stay open
Keep watching for new problems and new ideas during the work. Use every collaborator (Claude, Claude Code, Codex, ChatGPT, the owner) as much as useful. Future options to keep in view: adding more local models, and the lab computer to run them (adding models, not training them).

## Taboos (stop if any is about to happen)
From the owner:
- Hand-written per-application or per-task answer/source maps ("adapters" that pre-solve tasks).
- A diagnostic-only or "here is what we tried" paper.
- Changing the goal step by step without the owner explicitly deciding.
- Endless testing that does not lead to a built method.
- Dismissing our own adapted methods as "not novel" without a mechanism-level comparison.

From the research context (§0, §2, §7 no-go list, §12, §14, RESEARCH_RULES):
- Presenting a simple tool-loop wrapper or cache as an original contribution without a meaningfully different policy. Claim integration plus evidence, never invention of the parts.
- Comparing against a weak baseline. The original ROSA prompt forbids batching; the strong control must replace it and show batching is actually used.
- Assuming the model will produce valid syntax or plans without measuring adoption.
- Optimizing one metric while correctness or complete, source-supported answers drop; conflating new prompt text with a mechanism advantage.
- Endless "choose paper -> prototype -> fail -> next paper" without a written cross-round learning update.
- Repeating an old study (R1–28, JTVR, $ref planner, CodeAct subset, tool-menu retrieval, CPAW, AutoTool...) without a substantive new distinction.
- Claims from dev tasks only, or from tasks used for design; treating agreement between AIs as proof; presenting reports or predictions as measured results.
- Side-effectful ROS tools without guards.
- Over-correcting into endless audits instead of a bounded build-and-test.

## Environment hygiene
- The project uses uv, not pip.
- Never install third-party packages into the project environment for comparison work.
- Read reference code from a pinned source checkout kept outside the repository.
- If a reference must run, give it its own separate uv environment outside the project.

## Allowed without asking
- Local git commits.
- Paid GPT models through the team's custom package, when really needed.
- Simulated/virtual robot environments.

Still need the owner's go: pushes/merges to shared remotes, baseline edits, real robots.

## Check before each decision
"Does this keep us on track for items 1–7, and does it touch a taboo?" If unsure, say so to the owner.

## Anti-loop rule (owner, Nov 15; applies to EVERY AI collaborator)
We keep falling into: find problem → test → pick idea → "might be the same as paper X" → drop it → repeat. Stop this.
- A similarity that has not been proven by a mechanism-level comparison is NOT a finding. It must not stop, redirect or shrink the work. Until it is proven, say nothing about novelty: no "probably not new", "likely borrowed", "at best an adopted part".
- If you want to flag a possibly related paper, write one line: "Related paper to compare later: X (unverified)". Then carry on.
- Novelty is judged once, at the positioning stage, by side-by-side mechanism comparison (and ideally running both on our tasks), not every time an idea comes up.
- Bad results caused by our own design are normal. They are a reason to improve the design, not to abandon the direction.
