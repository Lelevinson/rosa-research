# Competing mechanisms and final offline rule

Status: implemented shadow diagnostic; live contribution BLOCKED / NOT YET
JUSTIFIED. No ROSA runtime hook or executor is installed.

H1 asks whether public outcomes and STOP competition predict useful continuation.
State contains last one/two grouped tool-name decisions, explicit native failure,
registry fingerprint, structured receipt shape and current request text. The
implemented count model does not interpret request meaning. Therefore the
names-only/details counterexample concerns its selected cheap features, not an
impossibility theorem about available natural language or richer models.

H2 asks whether historical argument association supplies a reliable source slot.
For each training target argument, learn every equal, exactly typed structured
value path in the preceding decision's receipts. A template records receipt index,
tool, actual source arguments, output shape and path. This is an association
hypothesis, never a causal permission. Instantiation requires one origin both in
training and the current receipt set, matching source identity/shape/type. Text
outputs are not silently parsed. Historical literals are never copied into a new
task's arguments. Unmatched real receipts cannot supply certified origins.
This deliberately restricted implementation uses the immediately preceding
group's receipts, not a general all-history provenance engine. Exact source-argument
matching and registry hashing can over-abstain; relaxing them is not automatically safe.

Let c(s,a) count training successor group a, including STOP. H1 estimates
P_behavior(a|s)=c(s,a)/sum_b c(s,b). Candidate uses supported k2 then k1 backoff;
support>=3 and empirical threshold0.90 are fixed design constants. Strong C_backoff
uses precisely the same states/backoff, counts, templates and gates. There is no
additional learned semantic input. Constrained parent score is
P_behavior(a|s)*(1-1.1**(-N)); threshold strictly>0.4, alpha=1. It uses recent-k2
first-contiguous-match path counts with one-group fallback when history is shorter.
This and grouping/STOP differ from full parent activation policy and are disclosed.

Development-only exact complete-action outcomes populate separate calibration
cells. Wilson z1.645 lower bounds describe behavioral agreement, not
P(tool AND args AND needed). The necessary label is missing. Zero development
complete-action hits do not justify a high-reliability continuation estimate.
No held-out observation updates counts or thresholds.

```text
freeze state at model_start using only previous completed events
predict successor group/STOP from training counts
instantiate current-origin argument template; retain each rejection
if STOP: hand off to normal LLM
require registered, explicitly authorized read-only interface
require unique typed current origins AND permitted flow/freshness evidence
require independently supported action-need label
require development complete-action lower bound >= .95
require positive charged net benefit
otherwise ABSTAIN; never force final or execute a write
compare frozen proposal with following actual action afterward
```

In this corpus, necessity, flow authority/freshness and net counterfactual benefit
are unavailable. Logs explicitly record those failed prerequisites. The program
computes policy admission from gate failures, separately from `execute=False`:
shadow mode has no dispatcher regardless of eligibility. Zero admission is a
fail-closed outcome, not a measured zero safety-error rate.

Compare: ngram k1/k2; same-feature fixed k1 C; ordinary C_backoff; constrained parent;
combined candidate; single removals of outcome conditioning, provenance/complete-action
risk calibration, and net-cost gate. Hard safety/uniqueness gates remain in every
ablation. H1-only and H2-only conceptual/learner revision tests are preserved.
No learned request-to-endpoint/extraction mapping or evaluator input enters runtime.

A strong ROSA and B's list/composite dispatcher remain unexecuted live comparators.
For a model-authorized discovery→inspection path, a helper that discovers once
and invokes the existing list reader covers the same work; history must establish
a different justified branch to beat it. This policy does not. Complete answer
and ordering quality, saved model decisions, tokens and wall time remain unknown.
