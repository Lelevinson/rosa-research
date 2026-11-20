# Unattended OAuth batches — inspection and hardening, 2026-10-22

## Finding before changes

**Automatic renewal already existed. One continuously running overnight batch
does not need a replacement OAuth implementation or a credential store.**

`ChatSiwc` delegates authentication to `SiwcBackend`; existing benchmark runners
pass `token_provider=auth.access_token`. `MemorySession.access_token()` already
refreshed within 60 seconds of expiry, using the issued client ID, resource and
authorized refresh token; omitted `scope`; serialized refreshes; and used rotating
replacements. All 23 existing offline OAuth tests passed before this work.
`interactive_session(timeout=...)` limits browser sign-in waiting, not batch life.

Repeated prompts between batches are intentional: each context exit revokes
its refresh token and clears credentials. Only host/client identifiers and a hash
of the validated subject are saved. Old revoked sessions cannot be reused. Keep
all trials of a bounded batch inside one session.

## Official support

The official open-source ChatGPT-plan flow supports renewal with granted
`offline_access`. Access tokens last one hour; refresh tokens last 30 days and
rotate on successful refresh. Renewal uses the issued client ID and resource,
without requesting additional scopes. It grants neither new consent nor quota.

- [Token fields and lifetimes](https://developers.openai.com/siwc/token-sharing-open-source/token-reference)
- [Renewal, security and revocation](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [Refresh errors, disconnection and usage limits](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)

These are the open-source plan-usage instructions, distinct from the identity-only
website flow. Documentation was checked on 2026-10-22.

## Limited changes for future runtime use

- Validate initial access-token fields, positive finite numeric lifetime, granted
  plan/resource permission, and scopes within the original requested set.
- On refresh, accept omitted scope as the previous grant; reject explicit scope
  expansion or reduction. Validate replacement fields before committing them
  together. Keep the latest returned refresh token for cleanup even when its
  replacement response is rejected.
- Recognize documented terminal refresh errors and clear unusable tokens. A failed
  refresh stops further renewal attempts in that session. Transient failures retain
  credentials until normal cleanup, rather than marking them revoked. No automatic
  OAuth restart, inference replay or retry loop.
- Serialize revocation with refresh. Preserve revoke-and-clear cleanup and explicit
  `NOT_CONFIRMED_...` status when remote revocation fails.
- Add optional `interactive_session(require_renewal=True)` to check for granted
  `offline_access` and a refresh token before a long batch. Requested permissions
  and consent behavior are unchanged. Status records the nonsecret refresh count.
- Latch transport failures, including refresh failure, authorization failure and
  quota exhaustion. Further requests fail locally with the original sanitized code
  and HTTP status. This deliberately stops on transient transport/stream failures
  too; a partial inference is never replayed.
- Add `checkpointed_trial(transport, save_progress)` for prospective runners. It
  invokes the caller's checkpoint on exit, then checks transport failure even if
  `ROSA.invoke()` caught the exception and returned an ordinary answer string.

Tokens remain memory-only; no dependencies or permissions are added. `ChatSiwc`'s
model/tool contract is unchanged. Credential persistence remains disabled and is
unnecessary for this use case. **Credential resume after process restart is not
implemented.** Do not put tokens in `.env`, command arguments, experiment JSON or Git.

## Integration into a new, prospectively versioned batch

Use one session for the batch and a live token callback, never a captured token
string. This is an integration pattern: `jobs`, `run_trial`, `save_progress`,
`status`, `request_cap` and `selected_catalog_slug` belong to the experiment.

```python
from rosa_auth.batch import checkpointed_trial
from rosa_auth.oauth import SafeError
from rosa_auth.responses import SiwcBackend
from rosa_auth.session import interactive_session
from rosa_backends import create_model

transport = llm = None
try:
    with interactive_session(request_budget=request_cap, require_renewal=True,
                             status=status) as auth:
        transport = SiwcBackend(request_budget=request_cap,
                                token_provider=auth.access_token)
        llm = create_model("siwc", model=selected_catalog_slug,
                           siwc_transport=transport)
        for job in jobs:
            # Keep existing model/tool/operation/time limit checks here.
            status["current_trial"] = {"id": job["id"], "status": "IN_PROGRESS"}
            save_progress()  # Atomic credential-free write before dispatch.
            with checkpointed_trial(transport, save_progress):
                result = run_trial(job, llm)
                if transport.availability_error is None:
                    status["trials"].append(result)
                    status["current_trial"] = None
        status["status"] = "COMPLETE"
except SafeError:
    if transport is not None and transport.availability_error is not None:
        status["status"] = "STOPPED_SERVICE_UNAVAILABLE"
        status["availability_error"] = transport.availability_error
        if status.get("current_trial"):
            status["current_trial"]["status"] = "INTERRUPTED_OUTCOME_UNKNOWN"
    else:
        status["status"] = "STOPPED_PREFLIGHT_OR_LIMIT"
    raise
finally:
    if llm is not None:
        llm.close()
    elif transport is not None:
        transport.close()
    save_progress()  # Includes refresh count and cleanup after session exit.
```

The checkpoint should atomically replace its JSON file and include completed
trials, current trial, attempts spent, remaining limits, protocol/source hashes
and backend configuration. Do not save the session, transport, HTTP request or
token response. An interrupted robot command has unknown outcome until independently
observed; never replay it automatically. Fresh authorization must not reset budgets.

The helper supplies no accounting, scoring, schema or automatic resume. The runner
retains those responsibilities and must explicitly use this boundary; it is not
implicitly installed around all ROSA calls. Frozen completed runners are unchanged.

## Reproducibility and limits

Baseline v1, Stage 4 and reliability v1 protocols, runners, archived sources,
results and evidence packages remain unchanged. Current runtime auth source has
changed; future experiments need new source hashes and run identity. Do not edit
frozen manifests to pass source checks: use archived sources to reproduce old runs.

Request, tool, operation and time caps are unchanged. Refresh never resets the
inference counter; a dispatch attempt failing authorization uses its attempt
allowance. Token-endpoint requests are separate serialized control-plane requests,
not extra LLM calls. No live campaign was launched by this maintenance work.

Unattended execution requires a live process, awake laptop and connectivity.
Process termination, exhausted plan/app quota, revocation or newly required consent
can stop a batch. Save progress and stop; any new authorization remains a user action.

## Offline validation

Result: **36 OAuth tests plus 9 shared-adapter tests passed (45 total)**, including
13 new overnight/failure tests. Live model requests: **0**. The Stage 4 evidence,
reliability v1 evidence and complete reliability review ZIPs still match their
previously recorded SHA-256 checksums.

In the prepared research environment, with no browser or live inference:

```bash
python -m unittest discover -s tests -p 'test_siwc*.py' -v
python -m unittest discover -s tests -p test_shared_backends.py -v
```

Coverage: ten simulated hours of rotation, concurrent access, scope preservation
and rejection, malformed lifetimes without secret-bearing errors, terminal and
transient failures, cleanup, renewable-session preflight, unchanged budgets,
quota stopping, and an actual ROSA executor swallowing a simulated 401 followed
by an atomic checkpoint and stop before the next trial. This is fake-credential
protocol validation, not proof of ten real hours of provider availability.
