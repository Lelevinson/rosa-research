# Teammates' work, read 2026-11-21 (read-only; reported evidence, not independently checked)

Read by Claude Code on 2026-11-21 with `git fetch`, `git log`, `git show` and `git ls-tree` only: no checkout over our work, no merge, no push, nothing run from a teammate branch. No judgment of novelty (see the anti-loop rule in [PAPER_GOAL_CONTRACT.md](../PAPER_GOAL_CONTRACT.md)).

Two remotes were read: the shared context repository `rosa-contexts` (`/home/levinsonchen/project/rosa-contexts`, fetched with `--prune`) and the research repository's own remote `origin` (`https://github.com/Lelevinson/rosa-research.git`, fetched with `--prune`), where a `member/martin` branch exists.

| Branch | Remote | Last commit (Asia/Taipei) | Author | One line |
|---|---|---|---|---|
| [`member/krln`](krln.md) | `rosa-contexts` | 2026-11-14 16:13 | levii831 (the owner's account; initial setup) | **Identical to `main` (same commit 26ac7bd); no teammate content published.** |
| [`member/martin`](martin.md) | `origin` (research repo) | 2026-11-20 18:33 | martin | Bounded-macro reliability module for ROSA on a modified fork: application-registered skills, bundled read / conditional write / verify by Python, accepted-report gate; UR5e Gazebo demo; native-schema Ollama profile for Llama/Granite. Built and unit-tested per its docs; live results are not in the branch. |
| `member/levinson` | `rosa-contexts` | 2026-11-19 22:14 | levii831 | Mirror of our context (not summarized). Its head (70e61ae) is older than today's local work; not published in this task, no push. |

Other branches of `origin` (`main` = 2026-10-20 snapshot) are ours or upstream.

## Work on the final exam or the lab that affects Sunday 2026-11-22
- **No teammate branch contains exam, lab, queue or task-pool material.** Neither `member/krln` nor `member/martin` touches `final_exam_draft_20261118`, the exam queue or any task pool.
- `member/martin`'s native-schema Ollama profile (`src/rosa_backends/tool_contract_ollama.py`) only supports the `llama3.1` and `granite3.3` families and raises `native_schema_v1_unsupported_model_family` for others, so it does not apply to our four exam models (lfm3, qwen3.5, gpt-oss, bonsai-2); it is opt-in.
- Lab facts from our own records (not teammate work, but they bear on Sunday): another container (`<OTHER_CONTAINER>`) and another Ollama (port 11439) run on the same lab GPU; the 2026-11-20 mini exam saw one false GPU-contention flag from the sampler's pid cache (fixed) and 0 of 8 contended in the rerun ([lab report B](../studies/final_exam_draft_20261118/lab_results_20261120/REPORT_B.md)). The exam-validity flag on lfm3's empty errors is in [ACTIVE_STATE](../ACTIVE_STATE.md).
