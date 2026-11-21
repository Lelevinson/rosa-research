# Stage 1c step 1: relabel of the 12 Stage 1a Qwen A0 episodes

Codebook: `CODEBOOK.md`. Labels are the rule first pass plus the manual overrides in `manual_labels_1c.json` (5 overrides). 'Avoidable' = RED, REC, or DEP whose arguments were available at least one request earlier (batchable). 'Needed' = DEP that depends on the preceding result, or JUDG.

## Per request (trace line = `model_end` line)

| episode | task | req | line | label | batchable | calls |
|---|---|---:|---:|---|---|---|
| 03-d1-A0-r0 | d1 | 2 | 10 | DEP (own error) | False | param_get({"node_name": "source", "param_name": "use_sim_time"}); param_get({"node_name": "listener", "param_n |
| 03-d1-A0-r0 | d1 | 3 | 20 | REC | True | node_list({}) |
| 03-d1-A0-r0 | d1 | 4 | 26 | REC | True | param_get({"node_name": "/source", "param_name": "use_sim_time"}); param_get({"node_name": "/listener", "param |
| 03-d1-A0-r0 | d1 | 5 | 36 | RED | True | topic_info({"topics": ["/chatter"]}) |
| 03-d1-A0-r0 | d1 | 6 | 42 | FIN | False |  |
| 23-d1-A0-r1 | d1 | 2 | 10 | DEP (own error) | False | param_get({"node_name": "source", "param_name": "use_sim_time"}); param_get({"node_name": "listener", "param_n |
| 23-d1-A0-r1 | d1 | 3 | 20 | REC | True | node_list({}) |
| 23-d1-A0-r1 | d1 | 4 | 26 | REC | True | param_get({"node_name": "/source", "param_name": "use_sim_time"}); param_get({"node_name": "/listener", "param |
| 23-d1-A0-r1 | d1 | 5 | 36 | RED | True | topic_info({"topics": ["/chatter"]}) |
| 23-d1-A0-r1 | d1 | 6 | 42 | FIN | False |  |
| 07-d2-A0-r0 | d2 | 2 | 10 | JUDG | False | node_info({"nodes": ["/calculator", "/listener", "/source"]}) |
| 07-d2-A0-r0 | d2 | 3 | 20 | JUDG | True | param_get({"node_name": "/calculator", "param_name": "use_sim_time"}) |
| 07-d2-A0-r0 | d2 | 4 | 26 | JUDG | True | service_info({"services": ["/add_two_ints"]}) |
| 07-d2-A0-r0 | d2 | 5 | 32 | FIN | False |  |
| 20-d2-A0-r1 | d2 | 2 | 10 | JUDG | False | node_info({"nodes": ["/calculator", "/listener", "/source"]}) |
| 20-d2-A0-r1 | d2 | 3 | 20 | JUDG | False | service_info({"services": ["/add_two_ints"]}) |
| 20-d2-A0-r1 | d2 | 4 | 26 | RED | True | param_list({"node_name": "/calculator"}) |
| 20-d2-A0-r1 | d2 | 5 | 32 | JUDG | True | param_get({"node_name": "/calculator", "param_name": "use_sim_time"}) |
| 20-d2-A0-r1 | d2 | 6 | 38 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 20-d2-A0-r1 | d2 | 7 | 42 | FIN | False |  |
| 04-t1-A0-r0 | t1 | 2 | 14 | JUDG | False | node_info({"nodes": ["/palette"]}); topic_info({"topics": ["/turtle1/pose", "/turtle1/color_sensor", "/diag_tu |
| 04-t1-A0-r0 | t1 | 3 | 28 | DEP | True | param_list({"node_name": "/palette"}) |
| 04-t1-A0-r0 | t1 | 4 | 34 | DEP | False | param_get({"node_name": "/palette", "param_name": "background_r"}); param_get({"node_name": "/palette", "param |
| 04-t1-A0-r0 | t1 | 5 | 48 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 04-t1-A0-r0 | t1 | 6 | 52 | FIN | False |  |
| 12-t1-A0-r1 | t1 | 2 | 14 | JUDG | False | node_info({"nodes": ["/palette"]}); topic_info({"topics": ["/turtle1/pose", "/turtle1/color_sensor", "/diag_tu |
| 12-t1-A0-r1 | t1 | 3 | 28 | DEP | True | param_list({"node_name": "/palette"}) |
| 12-t1-A0-r1 | t1 | 4 | 34 | DEP | False | param_get({"node_name": "/palette", "param_name": "background_r"}); param_get({"node_name": "/palette", "param |
| 12-t1-A0-r1 | t1 | 5 | 48 | FIN | False |  |
| 11-t2-A0-r0 | t2 | 2 | 10 | JUDG | False | node_info({"nodes": ["/palette"]}) |
| 11-t2-A0-r0 | t2 | 3 | 16 | RED | True | param_list({"node_name": "/palette"}) |
| 11-t2-A0-r0 | t2 | 4 | 22 | DEP | True | param_get({"node_name": "/palette", "param_name": "use_sim_time"}) |
| 11-t2-A0-r0 | t2 | 5 | 28 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 11-t2-A0-r0 | t2 | 6 | 32 | FIN | False |  |
| 21-t2-A0-r1 | t2 | 2 | 10 | JUDG | False | node_info({"nodes": ["/palette"]}) |
| 21-t2-A0-r1 | t2 | 3 | 16 | RED | True | param_list({"node_name": "/palette"}) |
| 21-t2-A0-r1 | t2 | 4 | 22 | DEP | True | param_get({"node_name": "/palette", "param_name": "use_sim_time"}) |
| 21-t2-A0-r1 | t2 | 5 | 28 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 21-t2-A0-r1 | t2 | 6 | 32 | FIN | False |  |
| 01-t3-A0-r0 | t3 | 2 | 14 | JUDG | False | node_info({"nodes": ["/palette"]}) |
| 01-t3-A0-r0 | t3 | 3 | 20 | FIN | False |  |
| 13-t3-A0-r1 | t3 | 2 | 14 | JUDG | False | node_info({"nodes": ["/palette"]}) |
| 13-t3-A0-r1 | t3 | 3 | 20 | FIN | False |  |
| 09-x1-A0-r0 | x1 | 2 | 14 | JUDG | False | node_info({"nodes": ["/calculator", "/listener", "/source", "/diag_tur); topic_info({"topics": ["/chatter", "/ |
| 09-x1-A0-r0 | x1 | 3 | 32 | DEP | True | param_get({"node_name": "/calculator", "param_name": "use_sim_time"}); param_get({"node_name": "/listener", "p |
| 09-x1-A0-r0 | x1 | 4 | 50 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 09-x1-A0-r0 | x1 | 5 | 54 | FIN | False |  |
| 19-x1-A0-r1 | x1 | 2 | 14 | JUDG | False | node_info({"nodes": ["/calculator", "/listener", "/source", "/diag_tur); topic_info({"topics": ["/chatter", "/ |
| 19-x1-A0-r1 | x1 | 3 | 32 | DEP | True | param_get({"node_name": "/calculator", "param_name": "use_sim_time"}); param_get({"node_name": "/listener", "p |
| 19-x1-A0-r1 | x1 | 4 | 50 | RED | True | set_debugging({"enable_debug_messages": false}) |
| 19-x1-A0-r1 | x1 | 5 | 54 | FIN | False |  |

## Excess decomposition per task (both repeats)

Excess = requests - strict floor. Avoidable requests = RED + REC + batchable DEP. If avoidable equals the excess, none of the excess is dependency-driven.

| task | episodes | floor | requests (each) | excess (each) | RED | REC | DEP batchable | DEP not batchable | JUDG | avoidable (each episode) |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---|
| d1 | 2 | 3 | [6, 6] | [3, 3] | 2 | 4 | 0 | 2 | 0 | [3, 3] |
| d2 | 2 | 4 | [5, 7] | [1, 3] | 2 | 0 | 0 | 0 | 6 | [0, 2] |
| t1 | 2 | 4 | [6, 5] | [2, 1] | 1 | 0 | 2 | 2 | 2 | [2, 1] |
| t2 | 2 | 3 | [6, 6] | [3, 3] | 4 | 0 | 2 | 0 | 2 | [3, 3] |
| t3 | 2 | 3 | [3, 3] | [0, 0] | 0 | 0 | 0 | 0 | 2 | [0, 0] |
| x1 | 2 | 3 | [5, 5] | [2, 2] | 2 | 0 | 2 | 0 | 2 | [2, 2] |
