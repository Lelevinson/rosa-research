# Blind audit form (finish-tool audit). Fill one block per episode, then one line per cell.

You are given `AUDIT_PACKET.md`: 14 cells, two episodes each (A and B), arm labels removed. Judge only from the packet: the task text, the tool calls and results shown (results are cut at 350 characters), and the final response. Do not look for or use any scorer output, run folder, or file other than the packet and this form. If a result is cut and you cannot decide, say "cannot tell".

## Per episode (cell NN, episode A or B)
1. **Correct?** Is the final response a correct answer to the task, given what the tool results show? `correct` / `incorrect` / `cannot tell`. Give the evidence in one sentence (which result shows it).
2. **Complete evidence?** Did the episode read what the answer needs? `yes` / `no` (name what is missing) / `cannot tell`.
3. **Stopped early?** Did the model give its final response before the evidence needed for a correct answer had been gathered? `yes` / `no`.
4. **Format of the final response:** does it have exactly the keys the task asks for (no extra keys, no missing keys, JSON valid)? `exact` / `extra keys` / `missing keys` / `not JSON / no answer` / `other`.
5. **Failure cause** (only if incorrect or incomplete), choose one: `wrong entity chosen` / `name not resolved or guessed` / `read chain not finished` / `value read wrongly or stale` / `answer format` / `no answer given` / `tool or backend error` / `other` (say what).
6. **One line** on anything in the trace that explains the outcome.

## Per cell
7. Which episode is better supported, A or B, or `same`? Name the trace differences that explain it (calls, order, stopping point, final response). Say whether the difference could be explained by **how the model ended the episode** (stopping, the form of the final response) or by **earlier choices in the read chain** (first calls, name guesses).

## Output
Write your answers as `AUDIT_ANSWERS.md` (one block per episode and one line per cell), or as JSON with the keys `cell`, `episode`, `correct`, `evidence`, `complete_evidence`, `stopped_early`, `format`, `failure_cause`, `note` and per cell `better`, `explanation`, `ending_vs_earlier_choices`. Do not guess which setting an episode used; if you think you can tell, say so in one separate line at the end, with the reason.
