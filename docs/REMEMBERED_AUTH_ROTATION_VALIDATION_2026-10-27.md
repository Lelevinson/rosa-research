# Remembered authorization: live validation and storage fix

M1 committed the optional feature at cc4a170 with offline/synthetic checks only.
The original M1 document and evidence remain the record of that checkpoint.
After the M3 Gazebo demo, live cross-process renewal exposed an actual defect:
Windows PowerShell converted File.Replace's null backup argument to an empty
path. Initial DPAPI storage worked; replacement failed. The session then attempted
revocation as designed, and the old grant subsequently returned invalid_grant.
A BrokenPipeError during helper cleanup masked the original safe storage error.

The focused fix passes a true CLR null through reflection to the same atomic
File.Replace operation. It creates no token backup or plaintext fallback. Stream
closure no longer masks a prior storage failure. No OAuth endpoint, scope,
identity check, permission or default memory-only cleanup policy changed.
The sign-in page now describes retained encrypted credentials only when the
remembered context explicitly selects that mode; its default notice is unchanged.

Validation: a real Windows DPAPI synthetic-profile test now covers initial save,
replacement, load across helper restarts, concurrent profile denial and deletion.
The user completed a fresh manual authorization after the unusable grant was
removed. A subsequent separate process successfully refreshed the protected
grant once, retained its encrypted replacement and cleared memory. The check
disabled LoginServer creation and made ZERO model requests. Raw status-only
records and the earlier failures are in the evaluation M2/M3 archive. No provider
tokens or protected record contents are in the archive.

This establishes one actual provider renewal across processes on this host. It
does not establish an overnight endurance result or immunity to expiration,
revocation, provider outages, scope changes or quota exhaustion. Those still stop
the caller; save progress, and require manual consent when the grant is unavailable.
No experiment or failed Qwen task was rerun during this authentication check.

Usage remains `python -m rosa_auth.remembered login|status|logout`. The protected
grant is intentionally retained per user preference. Explicit logout attempts
remote revocation and deletes local credentials. Ordinary interactive_session
continues to revoke on exit. Provider guidance:
[accounts, refresh and protected storage](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions).

These are prospective fixes to three working OAuth files after all M3 trials
completed. Per-backend source freezes and the original M1 archive are untouched;
the combined report distinguishes the trial version from this validated fix.
