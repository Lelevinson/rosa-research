# Offline measurements on the fresh FULL arm: schema sizes and result reuse (2026-11-17; measured only)

Scripts `schema_sizes.py` and `result_reuse.py` (definitions in their docstrings, fixed before the numbers), data `schema_sizes.json`, `result_reuse.json`. CPU only, from the saved ablation traces. No interpretation beyond the notes marked so.

## (a) Size of each offered tool schema (12 domain tools + final_answer, as sent to the model)
Characters are exact (serialized schema from the `model_start` event: name+arguments = function name and the parameters JSON; description = the function description text). Tokens are **estimates**, given as a range per model: low = a ratio fitted to that model's own request-1 total (assuming 0.25 tokens per character for the prose of the system prompt and the task), high = the ratio measured exactly on the 35 extra schemas of the 48-tool menu (+3666 tokens for qwen3.5 and bonsai, +3338 lfm3, +2029 gpt-oss for 10681 characters). The two ratios differ because the 35 extra schemas are punctuation-heavy; an exact per-tool token count would need a prefill-only run through each model's tokenizer, which was not done (this part is offline).

| tool | name+arguments chars | description chars | total chars | est. tokens as a range fit-to-total to 35-tool ratio (lfm3 / qwen3.5 / gpt-oss / bonsai) | description share |
|---|---:|---:|---:|---|---:|
| read_log | 443 | 420 | 863 | 185-270 / 236-296 / 131-164 / 236-296 | 49% |
| ros2_doctor | 75 | 43 | 118 | 25-37 / 32-41 / 18-22 / 32-41 | 36% |
| ros2_node_info | 156 | 80 | 236 | 51-74 / 65-81 / 36-45 / 65-81 | 34% |
| ros2_node_list | 264 | 122 | 386 | 83-121 / 106-132 / 58-73 / 106-132 | 32% |
| ros2_param_get | 184 | 137 | 321 | 69-100 / 88-110 / 49-61 / 88-110 | 43% |
| ros2_param_list | 315 | 233 | 548 | 117-171 / 150-188 / 83-104 / 150-188 | 43% |
| ros2_service_info | 165 | 85 | 250 | 54-78 / 68-86 / 38-47 / 68-86 | 34% |
| ros2_service_list | 267 | 106 | 373 | 80-117 / 102-128 / 57-71 / 102-128 | 28% |
| ros2_topic_echo | 321 | 529 | 850 | 182-266 / 232-292 / 129-161 / 232-292 | 62% |
| ros2_topic_info | 159 | 83 | 242 | 52-76 / 66-83 / 37-46 / 66-83 | 34% |
| ros2_topic_list | 265 | 102 | 367 | 79-115 / 100-126 / 56-70 / 100-126 | 28% |
| roslog_list | 232 | 116 | 348 | 74-109 / 95-119 / 53-66 / 95-119 | 33% |
| final_answer | 243 | 61 | 304 | 65-95 / 83-104 / 46-58 / 83-104 | 20% |
| **all 13** | 3089 | 2117 | 5206 | 1114-1627 / 1424-1787 / 789-989 / 1424-1787 | 41% |

Totals: the 13 schemas are 5,206 characters, of which 2,117 (41%) are description text and 3,089 name and arguments. By size: `read_log` (863 chars) and `ros2_topic_echo` (850) are the two largest (together 33% of the characters; `ros2_topic_echo` is 62% description), then `ros2_param_list` (548) and `ros2_node_list` (386). Removing `final_answer` and its prompt line saved 87 to 125 tokens (exact, from the NO_FINISH arm), consistent with the range for `final_answer` (46 to 104).

## (b) Reuse of tool results after the trimming point (fresh FULL arm, 40 episodes, 211 requests, 185 results)
Definitions: a result issued in request r is part of every later prompt; a "keep the 2 newest requests' results" rule would drop it from request r+3 on. A use = an item of the result (full name, type string, parameter value in the final answer) appears in the arguments of a later request. Last-copy use = the item is in no task text and no newer result.

| measure | value |
|---|---:|
| results re-sent at age >= 3 (older than 2 requests at some later request) | 103 of 185 |
| of those: used again at age >= 3 (any use) | 66 (64%) |
| of those: last-copy use at age >= 3 | 31 (30%) |
| input tokens of the arm | 721,646 |
| tokens re-sent for results at age >= 3 (the most a trim rule could remove) | 94,919 (13.2%) |
| of which results never used again at age >= 3 | 46,342 (6.4% of input) |
| of which results never used as last copy at age >= 3 | 63,332 (8.8% of input) |

By model (re-sent tokens at age >= 3, share of that model's input): bonsai 61,828 (23.6%), lfm3 29,943 (11.1%), qwen3.5 1,825 (1.8%), gpt-oss 1,323 (1.5%). The pairs of (result, using request) by age: {"1": 93, "5": 40, "3": 48, "4": 18, "2": 47} (age 1 = next request, 5 = five or more).
Notes (measured): old results are often used again: 66 of 103 results that are old enough for trimming are used again later (64%), and 31 of them hold the last copy of an item the later request needs. Result tokens per result are estimated (the request's new content minus its output tokens, shared by characters); the totals per request are exact.
**Interpretation (hypothesis, not tested):** a plain age-based trim has a ceiling of 13% of input tokens in this arm and would cut results that are used again in about two of three cases; the ceiling is concentrated in the two models with long failing episodes (bonsai, lfm3), where it is 11 to 24% of their input; for qwen3.5 and gpt-oss it is under 2%. Dropping only results that carry no item that later requests need would remove at most about 6 to 9% of input.
