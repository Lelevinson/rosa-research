# Finish-tool audit, unblinded and cross-tabulated with the scorer (2026-11-17)

Source: Codex's blind audit `AUDIT_ANSWERS.md` (SHA-256 `67360c5fef455851...`, verified by `unblind_audit.py`), unblinded with the private key written by `make_audit_packet.py` (outside the studies folder). 14 cells x 2 episodes = 28 episodes: 7 cells where FULL was supported and minus-finish was not (the 8 FULL-only cells minus the missed-hook cell) and 7 random both-supported cells. Codex saw task, calls, results cut at 350 characters and the final response only; it did not see the scorer. **Measured** = what Codex wrote and what the scorer says; **interpretation** is marked.

## 1. The 7 FULL-only cells: Codex's substantive verdict per episode (measured)
| cell | task | model | FULL answer (Codex) | minus-finish answer (Codex) | cause Codex gives for the minus-finish answer |
|---:|---|---|---|---|---|
| 2 | p3 | lfm3:1.7b | correct | **wrong** | other — wrong assignment of the observed chain positions to answer fields |
| 3 | p3 | bonsai-2:4b | correct | **wrong** | read chain not finished |
| 6 | e1h_chg_2 | bonsai-2:4b | correct | **wrong** | tool or backend error |
| 9 | e1h_abs_1 | gpt-oss:20b | correct | **wrong** | wrong entity chosen |
| 10 | e1h_abs_2 | lfm3:1.7b | correct | **wrong** | wrong entity chosen |
| 12 | v2 | qwen3.5:9b | uncertain | **wrong** | name not resolved or guessed |
| 14 | e1h_abs_1 | lfm3:1.7b | correct | **wrong** | wrong entity chosen |

Minus-finish answers: {'wrong': 7} (7 of 7 substantively wrong, 0 format-only, 0 uncertain). FULL answers: {'correct': 6, 'uncertain': 1} (6 correct, 1 uncertain: cell 12, the service-owner task, where the bulk node-info result was cut in the packet).

## 2. The 4 episodes Codex marked format-only (measured)
| cell | task | model | arm | scorer | Codex substance |
|---:|---|---|---|---|---|
| 7 | u3 | bonsai-2:4b | NO_FINISH | supported | correct |
| 11 | e1h_amb_1 | gpt-oss:20b | NO_FINISH | supported | correct |
| 11 | e1h_amb_1 | gpt-oss:20b | FULL | supported | correct |
| 13 | h4 | gpt-oss:20b | NO_FINISH | supported | correct |

All four are in both-supported cells (none among the 7 FULL-only cells): 3 minus-finish (prose plus fenced JSON in cells 7 and 13, fenced JSON in cell 11) and 1 FULL (cell 11, valid JSON wrapped in an extra `answer` key). **The scorer marked all four supported**: scorer v2.0's last-JSON and unwrap rules extracted them.

## 3. Agreement of Codex's substantive judgment with the scorer on all 28 episodes (measured)
| Codex | scorer supported | scorer unsupported |
|---|---:|---:|
| correct | 14 | 0 |
| incorrect | 0 | 7 |
| cannot tell | 7 | 0 |

On the 21 episodes Codex decided, agreement with the scorer is **21 of 21 (no disagreement)**: 14 correct = supported, 7 incorrect = unsupported. The 7 `cannot tell` episodes are all scorer-supported: 6 in both-supported cells (the minus-finish episodes of cells 1, 4, 5 and 8 and the FULL episodes of cells 5 and 8) and 1 in a FULL-only cell (the FULL episode of cell 12). The cause was result truncation in the packet, not Codex's view of the trace.

Verdicts by arm over all 28 (Codex): FULL {"correct": 10, "uncertain": 3, "format-only": 1}; minus-finish {"uncertain": 4, "wrong": 7, "format-only": 3}.

## 4. Reading
**One line: the finish tool's -7 is mainly a real answer-quality difference, not a format or extraction artifact; it stays unresolved only on the FULL side of one cell (cell 12) and on 7 truncation-uncertain episodes that all lie outside the 7 minus-finish answers in question.**

- **Measured:** all 7 minus-finish answers in the FULL-only cells are substantively wrong (Codex 7 of 7), 6 of the 7 FULL answers are correct and 1 is uncertain; no format-only episode lies in these cells; the 4 format-only episodes were scored supported; scorer and Codex agree on 21 of 21 decided episodes. If the one uncertain FULL answer (cell 12) were wrong, the gap would be 6 instead of 7; no uncertain episode could raise it above 7.
- **Interpretation (what the wrong answers are):** by Codex's per-cell causes, 3 of 7 are wrong-entity choices in the absent-node tasks (the model switched to the longer existing node: cells 9, 10, 14), 2 are unfinished or unresolved read chains (cells 3 and 12), 1 is a mis-assignment of observed values to answer fields (cell 2) and 1 ends with a backend response error without an answer (cell 6). Only the last two are close to the ending of the episode; five are choices earlier in the read chain. So the loss is real in the answers, but **whether the missing finish tool caused it is not established**: the earlier trace check showed that the paired runs diverge at request 1 or 2, so the entity and read-chain differences may be sampling differences that the prompt change set off rather than an effect of the finish tool at the end. The finish tool and its prompt line remain bundled.
- **Limits:** 14 cells, one seed, results cut at 350 characters (7 uncertain episodes), the audit sees 28 of the 80 relevant episodes, Codex's judgments were made without the scorer but with the task text only (no fixture truth), and the pairing of FULL and minus-finish episodes was visible to Codex (both arms of a cell shown side by side).
