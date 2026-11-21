# Stage 3c tables (offline replay of arm A1 excess requests; see PROTOCOL_STAGE3C.md)


## Qwen: 47 excess requests

| category | count | of which O | of which F | of which `sat` (P3 only by the requirements-satisfied clause) |
|---|---:|---:|---:|---:|
| P1 | 11 | 11 | 0 | 0 |
| P2 | 12 | 12 | 0 | 0 |
| P3 | 20 | 20 | 0 | 2 |
| P4 | 4 | - | - | 0 |
| P4 optional extra step (`p4_unneeded`) | 4 | | | |

### By template

| template | excess requests | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|
| upstream | 21 | 5 | 2 | 12 | 2 |
| pointer | 0 | 0 | 0 | 0 | 0 |
| hub | 12 | 6 | 0 | 4 | 2 |
| service | 14 | 0 | 10 | 4 | 0 |

### By task

| task | excess requests | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|
| h2 | 4 | 2 | 0 | 2 | 0 |
| h3 | 4 | 4 | 0 | 0 | 0 |
| h4 | 4 | 0 | 0 | 2 | 2 |
| u2 | 8 | 4 | 0 | 4 | 0 |
| u3 | 3 | 1 | 0 | 2 | 0 |
| u4 | 10 | 0 | 2 | 6 | 2 |
| v2 | 6 | 0 | 2 | 4 | 0 |
| v3 | 2 | 0 | 2 | 0 | 0 |
| v4 | 6 | 0 | 6 | 0 | 0 |

Largest episode by excess: 46-u4-ollama-r1 with 8 of 47 (17%); two largest: 46-u4-ollama-r1 + 22-u2-ollama-r0 = 12 (26%).
Largest episode by removable: 46-u4-ollama-r1 with 7 of 43 (16%); two largest: 46-u4-ollama-r1 + 38-u2-ollama-r1 = 11 (26%).

## Luna: 13 excess requests

| category | count | of which O | of which F | of which `sat` (P3 only by the requirements-satisfied clause) |
|---|---:|---:|---:|---:|
| P1 | 0 | 0 | 0 | 0 |
| P2 | 10 | 10 | 0 | 0 |
| P3 | 0 | 0 | 0 | 0 |
| P4 | 3 | - | - | 0 |
| P4 optional extra step (`p4_unneeded`) | 3 | | | |

### By template

| template | excess requests | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|
| upstream | 2 | 0 | 1 | 0 | 1 |
| pointer | 0 | 0 | 0 | 0 | 0 |
| hub | 5 | 0 | 3 | 0 | 2 |
| service | 6 | 0 | 6 | 0 | 0 |

### By task

| task | excess requests | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|
| h3 | 1 | 0 | 1 | 0 | 0 |
| h4 | 4 | 0 | 2 | 0 | 2 |
| u2 | 1 | 0 | 1 | 0 | 0 |
| u4 | 1 | 0 | 0 | 0 | 1 |
| v2 | 2 | 0 | 2 | 0 | 0 |
| v3 | 2 | 0 | 2 | 0 | 0 |
| v4 | 2 | 0 | 2 | 0 | 0 |

Largest episode by excess: 01-h4-openai-r0 with 2 of 13 (15%); two largest: 01-h4-openai-r0 + 41-h4-openai-r1 = 4 (31%).
Largest episode by removable: 43-v3-openai-r1 with 1 of 10 (10%); two largest: 43-v3-openai-r1 + 41-h4-openai-r1 = 2 (20%).

## Frozen decision rule (Qwen only)

- Removable (P1+P2+P3, capped per episode): **43 of 47** (91.5%); threshold 19. Cap bound in 0 episodes.
- O: **43**, F: **0** (O share 100.0%).
- Two largest episodes by removable: 11 of 43 = 25.6% (fragile if > 40%): **fragile: no**.
- Branch: **prompt control, not a method**.
- Luna (information only): removable 10 of 13, O 10, F 0.

## Sensitivities (not part of the frozen rule; they show how much the branch depends on judgments)

| reading | removable | O | F | O share | two largest share | branch |
|---|---:|---:|---:|---:|---:|---|
| headline (manual O/F as labelled, sat items count) | 43 | 43 | 0 | 100% | 26% | prompt control, not a method |
| without `sat` items (requirements-satisfied clause not counted) | 41 | 41 | 0 | 100% | 24% | prompt control, not a method |
| all P3 treated as F | 43 | 23 | 20 | 53% | 26% | prompt control, not a method |
| all P1 treated as F | 43 | 32 | 11 | 74% | 26% | prompt control, not a method |
| all P1 and P3 treated as F (only P2 is O) | 43 | 12 | 31 | 28% | 26% | a target exists |
| all P2 treated as F (A1 already permits batching and Qwen did not) | 43 | 31 | 12 | 72% | 26% | prompt control, not a method |
| all P1, P2 and P3 treated as F | 43 | 0 | 43 | 0% | 26% | a target exists |

## Agreement

- Blind relabel (15, first pass and Stage 3 labels hidden) vs final manual: category 15/15 (100%); category and O/F 15/15 (100%).
- Rule-based first pass vs final manual (all 60): category 38/60 (63%); category and O/F 35/60 (58%).
  - first-pass category changes (first -> final: count): P1->P4: 1; P2->P3: 1; P2->P4: 1; P4->P1: 4; P4->P2: 14; P4->P3: 1
  - note: the same analyst (Claude) made the blind and the final labels, so the blind check measures consistency over time and with the sheet alone, not independent human agreement.

## Every item (trace line is the `model_end` line of the request; trace = `stage3b_20261113T155721Z/<episode>/trace.jsonl`)

| model | episode | task | request / line | Stage 3 label | first pass | final | O/F | sat | note |
|---|---|---|---|---|---|---|---|---|---|
| Qwen | 03-h2-ollama-r0 | h2 | R3 / 16 | REC | P1/F | P1 | O |  | corrected call after short-name failure; namespace was in R1's result |
| Qwen | 03-h2-ollama-r0 | h2 | R4 / 22 | RED | P3/O | P3 | O |  | exact repeat of R3 |
| Qwen | 05-u4-ollama-r0 | u4 | R4 / 22 | EXPLORE | P4/- | P4 | - |  | node_info on the upstream node, optional step; name first appears in R3's result |
| Qwen | 05-u4-ollama-r0 | u4 | R5 / 28 | RED | P4/- | P2 | O |  | param_list on a node known from R3's result; could join R4 |
| Qwen | 11-v4-ollama-r0 | v4 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 11-v4-ollama-r0 | v4 | R4 / 30 | LATE | P2/O | P2 | O |  | names known from R2; second node_info batch could join R3 |
| Qwen | 11-v4-ollama-r0 | v4 | R5 / 44 | LATE | P2/O | P2 | O |  | names known from R2; third node_info batch could join R3 |
| Qwen | 13-v2-ollama-r0 | v2 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 13-v2-ollama-r0 | v2 | R4 / 58 | RED | P3/O | P3 | O |  | exact repeat of R1 service_info |
| Qwen | 13-v2-ollama-r0 | v2 | R5 / 64 | RED | P3/O | P3 | O |  | exact repeat |
| Qwen | 14-h4-ollama-r0 | h4 | R4 / 26 | RED | P4/- | P4 | - |  | param_list on publishers found in R3's result, optional step; depends on preceding result |
| Qwen | 14-h4-ollama-r0 | h4 | R6 / 54 | RED | P3/O | P3 | O |  | exact repeat of an R5 param_get |
| Qwen | 16-h3-ollama-r0 | h3 | R3 / 16 | REC | P1/O | P1 | O |  | node_list after short-name failure; namespace was in R1's result |
| Qwen | 16-h3-ollama-r0 | h3 | R4 / 22 | REC | P4/- | P1 | O |  | re-issue of the failed call with the full name; same failure chain |
| Qwen | 17-v3-ollama-r0 | v3 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 22-u2-ollama-r0 | u2 | R3 / 16 | REC | P1/O | P1 | O |  | node_list after 'Node not found' for a short name; namespace was in R1's result |
| Qwen | 22-u2-ollama-r0 | u2 | R4 / 22 | REC | P4/- | P1 | O |  | re-issue of the failed call with the full name; same failure chain |
| Qwen | 22-u2-ollama-r0 | u2 | R5 / 28 | RED | P3/O | P3 | O |  | exact repeat of R4 |
| Qwen | 22-u2-ollama-r0 | u2 | R6 / 34 | RED | P3/O | P3 | O |  | exact repeat |
| Qwen | 25-h2-ollama-r1 | h2 | R3 / 16 | REC | P1/F | P1 | O |  | corrected call after short-name failure; namespace was in R1's result |
| Qwen | 25-h2-ollama-r1 | h2 | R4 / 22 | RED | P3/O | P3 | O |  | exact repeat of R3 |
| Qwen | 27-h4-ollama-r1 | h4 | R4 / 26 | RED | P4/- | P4 | - |  | param_list on publishers found in R3's result, optional step; depends on preceding result |
| Qwen | 27-h4-ollama-r1 | h4 | R6 / 54 | RED | P3/O | P3 | O |  | exact repeat of an R5 param_get |
| Qwen | 28-v3-ollama-r1 | v3 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 29-u3-ollama-r1 | u3 | R3 / 16 | REC | P1/F | P1 | O |  | corrected call after short-name failure; namespace was in R1's result |
| Qwen | 29-u3-ollama-r1 | u3 | R5 / 28 | EXPLORE | P4/- | P3 | O | sat | after R4 every requested field (publisher, input topic, upstream) is already held; P3 by the 'requirements satisfied' clause |
| Qwen | 29-u3-ollama-r1 | u3 | R6 / 34 | RED | P3/O | P3 | O |  | exact repeat of R3 node_info |
| Qwen | 35-v4-ollama-r1 | v4 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 35-v4-ollama-r1 | v4 | R4 / 30 | LATE | P2/O | P2 | O |  | names known from R2; second node_info batch could join R3 |
| Qwen | 35-v4-ollama-r1 | v4 | R5 / 44 | LATE | P2/O | P2 | O |  | names known from R2; third node_info batch could join R3 |
| Qwen | 37-v2-ollama-r1 | v2 | R2 / 10 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Qwen | 37-v2-ollama-r1 | v2 | R4 / 58 | RED | P3/O | P3 | O |  | exact repeat of R1 service_info |
| Qwen | 37-v2-ollama-r1 | v2 | R5 / 64 | RED | P3/O | P3 | O |  | exact repeat |
| Qwen | 38-u2-ollama-r1 | u2 | R3 / 16 | REC | P1/O | P1 | O |  | node_list after 'Node not found' for a short name; namespace was in R1's result |
| Qwen | 38-u2-ollama-r1 | u2 | R4 / 22 | REC | P4/- | P1 | O |  | re-issue of the failed call with the full name; same failure chain |
| Qwen | 38-u2-ollama-r1 | u2 | R5 / 28 | RED | P3/O | P3 | O |  | exact repeat of R4 |
| Qwen | 38-u2-ollama-r1 | u2 | R6 / 34 | RED | P3/O | P3 | O |  | exact repeat |
| Qwen | 44-h3-ollama-r1 | h3 | R3 / 16 | REC | P1/O | P1 | O |  | node_list after short-name failure; namespace was in R1's result |
| Qwen | 44-h3-ollama-r1 | h3 | R4 / 22 | REC | P4/- | P1 | O |  | re-issue of the failed call with the full name; same failure chain |
| Qwen | 46-u4-ollama-r1 | u4 | R4 / 22 | EXPLORE | P4/- | P4 | - |  | node_info on the upstream node, optional step; name first appears in R3's result |
| Qwen | 46-u4-ollama-r1 | u4 | R5 / 28 | RED | P4/- | P2 | O |  | param_list on a node known from R3's result; could join R4 |
| Qwen | 46-u4-ollama-r1 | u4 | R7 / 40 | EXPLORE | P2/O | P3 | O | sat | after R6 every requested field incl. upstream_gain is held; yarrow's gain is not requested; P3 by the 'requirements satisfied' clause |
| Qwen | 46-u4-ollama-r1 | u4 | R8 / 46 | RED | P3/O | P3 | O |  | exact repeat of an earlier param_get |
| Qwen | 46-u4-ollama-r1 | u4 | R9 / 52 | RED | P3/O | P3 | O |  | exact repeat of an earlier param_get |
| Qwen | 46-u4-ollama-r1 | u4 | R10 / 58 | RED | P3/O | P3 | O |  | exact repeat of an earlier param_get |
| Qwen | 46-u4-ollama-r1 | u4 | R11 / 64 | RED | P3/O | P3 | O |  | exact repeat of an earlier param_get |
| Qwen | 46-u4-ollama-r1 | u4 | R12 / 70 | RED | P3/O | P3 | O |  | exact repeat of an earlier param_get |
| Luna | 00-v3-openai-r0 | v3 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 with service_info |
| Luna | 01-h4-openai-r0 | h4 | R2 / 12 | LATE | P2/O | P2 | O |  | topic name is in the task text; could join R1 with node_list |
| Luna | 01-h4-openai-r0 | h4 | R5 / 41 | RED | P2/O | P4 | - |  | param_list on publishers found in R4's result, optional step (parameter name is in the task); depends on preceding result |
| Luna | 07-v4-openai-r0 | v4 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Luna | 20-v2-openai-r0 | v2 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Luna | 21-h3-openai-r0 | h3 | R2 / 12 | LATE | P2/O | P2 | O |  | topic name is in the task text; could join R1 |
| Luna | 26-v2-openai-r1 | v2 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Luna | 32-v4-openai-r1 | v4 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |
| Luna | 40-u2-openai-r1 | u2 | R2 / 12 | LATE | P2/O | P2 | O |  | topic name is in the task text; could join R1 with node_list |
| Luna | 41-h4-openai-r1 | h4 | R2 / 12 | LATE | P2/O | P2 | O |  | topic name is in the task text; could join R1 |
| Luna | 41-h4-openai-r1 | h4 | R5 / 49 | REC | P1/O | P4 | - |  | param_list retry after guessed names failed in R4; the real names arrived in R4's own topic_info result; optional step; depends on preceding result |
| Luna | 42-u4-openai-r1 | u4 | R4 / 26 | RED | P4/- | P4 | - |  | param_list on a node found in R3's result, optional step; depends on preceding result |
| Luna | 43-v3-openai-r1 | v3 | R2 / 12 | LATE | P4/- | P2 | O |  | node_list takes no arguments; could join R1 |

## O sentences used (generic, no task names; each is untested)

- Build full node names as namespace plus name from earlier results; never pass a bare name.  (11 Qwen, 0 Luna)
- Do not repeat a call whose successful result is already in the conversation.  (18 Qwen, 0 Luna)
- Issue every call whose arguments you already know in the same response.  (2 Qwen, 4 Luna)
- Make lookups that need no arguments in the same response as your first lookup.  (6 Qwen, 6 Luna)
- Stop and answer as soon as every requested field has a value from a tool result.  (2 Qwen, 0 Luna)
- When you must inspect many known entities, request them all in one response.  (4 Qwen, 0 Luna)
