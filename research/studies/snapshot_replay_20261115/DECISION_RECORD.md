# Decision record (context section 14.2), 2026-11-15, before computing

Status: PROCEEDS as a narrow offline diagnostic with a frozen bar (protocol hash in FREEZE.json). No implementation, live run or model call is authorized by it.
1. **Opportunity (F).** Pilot C1 episodes still make serial discovery requests (node_list, node_info, topic_list) that a one-time structure read could replace; the unmeasured part is how many whole requests and what token cost. Denominator: 80 C1 episodes in RESULTS_LOG.jsonl.
2. **Mechanism (P).** Pre-inject one structure snapshot at episode start (framework-observable read tools only, no per-task map).
3. **Closest prior / negative:** Stage 2a learned speculative expansion (stopped by its kill bar), Stage 3d prompt sentences, stock ROSA's own discovery-first messages (removed in A1); ordinary baseline: a fixed one-line enrichment (node_info after node_list), listed as open in ACTIVE_STATE. Delta tested: a full static snapshot instead of a prediction.
4. **Fair evaluation:** counts only; whole requests; token cost of the snapshot charged to every remaining request.
5. **Decision-changing action:** whether a snapshot arm is worth a separate authorization; stop rule = the frozen bar.
Known weakness: snapshot size scales with graph size (19 and 14 nodes here); a large graph would only make the token side worse.
