Hand-read original matched Forge traces. Paths below are relative to
`research/_artifacts/runs/forge_baseline_20261115/full_20261115T091338Z/`.
Line numbers refer to the immutable JSONL traces, not a reconstructed transcript.
Control outcomes use the same task/model/seed under frozen scorer v2.

1. **lfm3 h4 seed 1: correct acquired facts, malformed final keys; C1 succeeds.**
   `lfm3_1.7b-stage3/002-h4-Forge-s1/trace.jsonl`: L38 gives anvil's three
   input topics; L51 names their publishers. Gains are actually read at
   L69 (zephyr 74), L78 (dune 65), and L87 (oasis 89). L96 reads an
   additional unrequested anvil gain. At L101 `respond.message` puts leading
   spaces in the oasis/anvil keys and includes the extra anvil field, followed
   by a promise to recompute. Forge returns that message at L103; the promise
   causes no further iteration after a successful terminal call. Support
   passes, exactness fails. Same-cell C1 is supported in 9 requests; Forge
   uses 11. The observed failure is final content, not a failed ROS read.

2. **lfm3 absent-target seed 2: decoy mistaken for requested node; C1 succeeds.**
   `lfm3_1.7b-e1h/013-e1h_abs_1-Forge-s2/trace.jsonl`: the exact requested
   `/ember/mistral` lookup fails at L11. An unanchored listing at L17–20
   returns the different `/e1h/ember/mistral`. Forge then reads that decoy
   (L26–29) and its limit 279 (L44–47), and at L52 submits `running:true`
   for the decoy plus an unrequested limit. The exact requested node is
   absent. Same-cell C1 is supported; Forge's six-request answer is wrong.
   A successful native read of a similarly named node did not establish the
   requested entity's presence.

3. **lfm3 ambiguous-node seed 2: repeated successful reads until the cap;
   C1 succeeds.** `lfm3_1.7b-e1h/014-e1h_amb_1-Forge-s2/trace.jsonl`:
   L40 and L49 deliver the two nodes' modes; L58 and L67 deliver both limits.
   The facts needed to select the fast node and its limit have arrived.
   From L73 through L361, calls alternate the same two `limit` reads instead
   of submitting a terminal answer. L366–367 record MaxIterationsError at
   40 requests, with no final answer. These are successful repeated reads,
   not an unavailable ROS source. The same-cell C1 control is supported.
   This illustrates a failure in this run; it does not establish that a
   particular countermeasure would preserve correctness or reduce total cost.

4. **Qwen service-provider seed 1: type acquired, provider guessed; C1 succeeds.**
   `qwen3.5_9b-stage3/023-v2-Forge-s1/trace.jsonl`: L8–11 obtains only
   `/plant32/cedar_reset`'s type. L17–20 lists node names, including both
   quill and the true provider wharf; it does not associate a node with the
   service. No `node_info` is called. At L25 `respond` names quill, which is
   wrong; the correct node is wharf. Forge uses three requests and returns
   an exactness failure, while same-cell C1 is supported. The frozen support
   screen's empty missing-evidence list is not proof the provider relation
   was read: listing the name passes its textual occurrence check, whereas
   the exact-answer check rejects the wrong relation. Scoring was not changed.

5. **gpt-oss h4 seed 2: facts present, malformed outer answer JSON; C1
   succeeds.** `gpt-oss_20b-stage3/045-h4-Forge-s2/trace.jsonl`: L101,
   L110 and L119 deliver gains 74, 65 and 89. L124 submits a string containing
   the correct node, publisher mapping and gains, but it ends with a stray
   quote after the gains object and lacks the outer closing brace. L126
   returns the same malformed string. The frozen last-JSON-object extractor
   selects the valid inner gains object, so the scored object lacks node,
   publishers and the enclosing gains key. This is a serialization/scoring
   interaction with factually correct content in the raw message, not a
   missing native read. Same-cell C1 is supported; Forge uses 14 requests.
   No JSON repair, label override or scorer revision was applied.
