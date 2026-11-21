# Stage 3d residual labels (A2 Qwen; Stage 3c definitions; one analyst, first pass visible; no blind check, none required by the protocol)

| category | A1 Qwen (Stage 3c, 47) | A2 Qwen (30) |
|---|---:|---:|
| P1 | 11 | 0 |
| P2 | 12 | 6 |
| P3 | 20 | 20 |
| P4 | 4 | 4 |

P3 includes 2 items that qualify only by the 'requirements satisfied' clause (`sat`). The 4 P4 items are optional extra steps (`p4_unneeded`).

**O/F under the Stage 3c definitions.** Stage 3c labelled all P1 to P3 items O on the untested judgment that a one-line sentence would prevent them. In A2 each remaining P2/P3 item occurred with the matching sentence already in the prompt (P2: sentences 3, 4, 6; P3: sentence 2, and sentence 5 for `sat`). A sentence at this wording therefore did not prevent them for Qwen, so by the weakest-sufficient-control rule they cannot be labelled O on evidence; they are labelled **F (tested: the A2 sentence did not suffice)**: 26 of 26 P2/P3 items. This is an interpretation of one run (one prompt, temperature 0); a stronger wording was not tried and the protocol forbids trying it in this stage.

| model | episode | task | request / line | Stage 3 label | first pass | final | note |
|---|---|---|---|---|---|---|---|
| Qwen | 00-h3-ollama-r0 | h3 | R4 / 26 | RED | P3 | P3 | exact repeat of R3 topic_info |
| Qwen | 01-v3-ollama-r0 | v3 | R2 / 10 | LATE | P4 | P2 | node_list takes no arguments; could join R1 |
| Qwen | 04-u3-ollama-r0 | u3 | R4 / 22 | RED | P3 | P3 | exact repeat of R1 |
| Qwen | 04-u3-ollama-r0 | u3 | R5 / 28 | RED | P3 | P3 | exact repeat of R2 |
| Qwen | 05-h2-ollama-r0 | h2 | R3 / 16 | RED | P3 | P3 | exact repeat of R2 |
| Qwen | 06-v4-ollama-r0 | v4 | R2 / 10 | LATE | P4 | P2 | node_list takes no arguments; could join R1 |
| Qwen | 06-v4-ollama-r0 | v4 | R6 / 70 | RED | P3 | P3 | exact repeat of R5 |
| Qwen | 07-h4-ollama-r0 | h4 | R4 / 26 | RED | P4 | P4 | param_list on publishers found in R3's result; optional step (parameter name is in the task); depends on preceding result |
| Qwen | 07-h4-ollama-r0 | h4 | R6 / 54 | RED | P3 | P3 | exact repeat of the R5 param_get batch |
| Qwen | 10-u2-ollama-r0 | u2 | R3 / 16 | RED | P3 | P3 | exact repeat of R2 |
| Qwen | 11-u4-ollama-r0 | u4 | R4 / 22 | EXPLORE | P4 | P4 | node_info on the upstream node; optional step; name first appears in R3's result |
| Qwen | 11-u4-ollama-r0 | u4 | R5 / 28 | RED | P4 | P2 | param_list on a node known from R3's result; could join R4 |
| Qwen | 11-u4-ollama-r0 | u4 | R7 / 40 | EXPLORE | P2 | P3 (sat) | after R6 every requested field incl. upstream_gain is held; yarrow's gain is not requested; P3 by the 'requirements satisfied' clause |
| Qwen | 11-u4-ollama-r0 | u4 | R8 / 46 | RED | P3 | P3 | exact repeat of R6 |
| Qwen | 11-u4-ollama-r0 | u4 | R9 / 52 | RED | P3 | P3 | exact repeat of R6 |
| Qwen | 12-u4-ollama-r1 | u4 | R4 / 22 | EXPLORE | P4 | P4 | node_info on the upstream node; optional step; name first appears in R3's result |
| Qwen | 12-u4-ollama-r1 | u4 | R5 / 28 | RED | P4 | P2 | param_list on a node known from R3's result; could join R4 |
| Qwen | 12-u4-ollama-r1 | u4 | R7 / 40 | EXPLORE | P2 | P3 (sat) | after R6 every requested field incl. upstream_gain is held; yarrow's gain is not requested; P3 by the 'requirements satisfied' clause |
| Qwen | 12-u4-ollama-r1 | u4 | R8 / 46 | RED | P3 | P3 | exact repeat of R6 |
| Qwen | 12-u4-ollama-r1 | u4 | R9 / 52 | RED | P3 | P3 | exact repeat of R6 |
| Qwen | 13-h2-ollama-r1 | h2 | R3 / 16 | RED | P3 | P3 | exact repeat of R2 |
| Qwen | 14-u3-ollama-r1 | u3 | R4 / 22 | RED | P3 | P3 | exact repeat of R1 |
| Qwen | 14-u3-ollama-r1 | u3 | R5 / 28 | RED | P3 | P3 | exact repeat of R2 |
| Qwen | 16-h4-ollama-r1 | h4 | R4 / 26 | RED | P4 | P4 | param_list on publishers found in R3's result; optional step; depends on preceding result |
| Qwen | 16-h4-ollama-r1 | h4 | R6 / 54 | RED | P3 | P3 | exact repeat of the R5 param_get batch |
| Qwen | 17-v4-ollama-r1 | v4 | R2 / 10 | LATE | P4 | P2 | node_list takes no arguments; could join R1 |
| Qwen | 17-v4-ollama-r1 | v4 | R6 / 70 | RED | P3 | P3 | exact repeat of R5 |
| Qwen | 18-v3-ollama-r1 | v3 | R2 / 10 | LATE | P4 | P2 | node_list takes no arguments; could join R1 |
| Qwen | 19-h3-ollama-r1 | h3 | R4 / 26 | RED | P3 | P3 | exact repeat of R3 |
| Qwen | 23-u2-ollama-r1 | u2 | R3 / 16 | RED | P3 | P3 | exact repeat of R2 |

First pass vs final: category 22/30. Trace = `stage3d_20261114T005613Z/<episode>/trace.jsonl`; line = `model_end` line of the request.
