# Blind relabel agreement

Sample: 54 of 269 labeled requests (seeded random 20%).

- Exact agreement: 46/54 = 85%; Cohen's kappa = 0.81
- Excluding FIN (trivial): 35/43 = 81%
- Agreement on the coarse question 'avoidable (DEP or RED) vs not', excluding FIN: 39/43 = 91%

Confusion (primary -> blind):

| primary | blind | n |
|---|---|---:|
| DEP | DEP | 15 |
| DEP | JUDG | 2 |
| FIN | FIN | 11 |
| JUDG | DEP | 2 |
| JUDG | JUDG | 9 |
| JUDG | UNCLEAR | 3 |
| REC | REC | 3 |
| RED | RED | 8 |
| UNCLEAR | JUDG | 1 |

Disagreements:

| request | primary | blind | blind reason |
|---|---|---|---|
| 23-x1-A-r1#2 | JUDG | DEP | node_info over the four names just listed. |
| 07-x1-C#2 | JUDG | UNCLEAR | node_info over listed nodes (DEP) plus choosing pose and chatter topics (JUDG); DEP vs JUDG. |
| 00-x1-B-r0#4 | DEP | JUDG | Selected pose and chatter topics from node info by task meaning. |
| 00-openai-x1-A#2 | JUDG | UNCLEAR | Per-node param_gets (DEP) plus choosing pose and chatter topic_info (JUDG); DEP vs JUDG. |
| 03-x1-C-r0#2 | JUDG | DEP | node_info over the four names just listed. |
| 00-t1-B#3 | DEP | JUDG | Chose to list params to find the source of background RGB. |
| 11-t2-B-r0#2 | UNCLEAR | JUDG | Interpreted task namespace as a node name; call failed. |
| 09-openai-x1-B#3 | JUDG | UNCLEAR | Per-node param_gets (DEP) plus choosing pose and chatter topic_info (JUDG); DEP vs JUDG. |
