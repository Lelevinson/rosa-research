# Optional remembered ChatGPT authorization

The existing adapter already renews access during a live session. Repeated
between-batch sign-ins came from deliberate memory-only revoke-on-exit cleanup.
Official Sign in with ChatGPT supports protected credential storage and rotating
refresh tokens. There is no need for an automatic consent-clicking mechanism.

This optional implementation reuses `MemorySession`, the existing authorization
flow, ID-token/identity checks, granted-scope validation and renewal. Default
`interactive_session` and every frozen experiment remain unchanged.

Official guidance checked 2026-10-27:

- [Accounts, refresh, protected storage and sign-out](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [Registration, returning sign-in and scope validation](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Consent, revocation and refresh failures](https://developers.openai.com/siwc/token-sharing-open-source/errors-and-recovery)

## First opt-in and explicit sign-out

In the existing WSL research environment (or supported Windows environment):

```bash
python -m rosa_auth.remembered login
python -m rosa_auth.remembered status
python -m rosa_auth.remembered logout
```

The initial `login` prints the local Continue with ChatGPT page; complete it
manually once. It makes no model requests. Later uses refresh the authorized
grant without a browser while it remains valid. Expiration, revocation or
additional provider-required consent can still require manual sign-in.
The implementation never auto-clicks approval, forces reconsent, adds scopes,
uses a new billing path or retries inference. After a terminal refresh error it
clears unusable credentials and stops; it does not pop open another login in
the middle of a batch. A new explicit login may then be needed.

`status` only checks whether a local protected record exists; it does not claim
the provider still accepts it. Stop an active batch before `logout`: a profile
is exclusively leased while in use to prevent racing refresh-token rotation.
Sign-out attempts remote revocation and deletes the local record. Unconfirmed
remote revocation is reported honestly; disconnect the app in ChatGPT settings
if revocation could not be confirmed.

No real login was performed during M1. The feature has offline protocol tests
and an actual Windows DPAPI synthetic-record test; live provider resume is
NOT YET TESTED. Old revoked tokens cannot be recovered.

## Use in NEW runners only

```python
from rosa_auth.remembered import remembered_session
from rosa_auth.responses import SiwcBackend

status = {}
with remembered_session(request_budget=REQUEST_CAP, status=status) as auth:
    backend = SiwcBackend(request_budget=REQUEST_CAP, token_provider=auth.access_token)
    try:
        # Existing trial/model/tool/token/time limits and checkpointed_trial
        # remain mandatory. Persist progress atomically before/after requests.
        run_bounded_jobs(backend)
    finally:
        backend.close()
```

The example names are caller-owned, not a ready-made benchmark. Authorization
renewal does not reset any budget or supply quota. The context's request_budget
is authorization UI metadata; SiwcBackend and the runner enforce actual usage.
Save credential-free experiment progress when authorization becomes unavailable.
New runners must explicitly import this opt-in context and record its use;
do not retrofit frozen experiments or silently change their cleanup semantics.

## Protection and cleanup

Only the renewable refresh token, original scopes, issued client ID, resource,
host ID and validated subject hash are persisted. Access/ID tokens are not saved.
On resume, metadata must match the existing registered account/host/client and
the provider must renew the token before it can be used for inference. Scope
changes fail closed. Successful rotation is saved immediately and atomically.
A persistence failure after rotation revokes the latest credential and removes
the unusable stored record instead of silently falling back to stale tokens.

Windows DPAPI encrypts records for the current Windows user under
`%LOCALAPPDATA%\ROSAResearch\OAuth\<profile>.dpapi`. The directory ACL allows only
that user and SYSTEM. WSL uses an owned, hidden PowerShell helper with private
pipes; secrets never enter command-line arguments, environment variables, Git,
trace attributes, `.env`, or diagnostic error messages. A Windows named mutex
leases the profile across processes/distros during refresh and use. There is
no plaintext-file fallback or custom encryption key to manage. This protection
does not defend against malicious software already running as the same user.

Normal opt-in context exit clears memory and closes the storage helper while
retaining the protected refresh credential as requested. Explicit sign-out
revokes/deletes it. For memory-only operation, continue to use the unchanged
`interactive_session`, which still revokes on exit. Persistence remains optional.
This implementation requires Windows DPAPI (Windows or WSL interoperability);
it fails closed on other hosts instead of weakening storage security.

Synthetic storage/lease test, no real credentials:

```bash
python -m rosa_auth.remembered storage-self-test
```
