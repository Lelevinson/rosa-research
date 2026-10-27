"""Reusable interactive sign-in scope with memory-only tokens and cleanup."""
from contextlib import contextmanager
from pathlib import Path
import time

from .oauth import (Attempt, ISSUER, LoginServer, MemorySession, SafeError,
                    load_registration, request_json, save_registration)


@contextmanager
def interactive_session(*, request_budget=6, timeout=900, port=1455, status=None,
                        require_renewal=False):
    status = status if status is not None else {}
    session = None
    try:
        discovery = request_json(ISSUER + '/.well-known/openid-configuration')
        session = MemorySession(discovery)
        path = Path.home() / '.local/share/rosa-siwc/registration.json'
        registration = load_registration(path)
        attempt = Attempt(registration['host_id'], registration.get('client_id'))
        try:
            server = LoginServer(attempt, discovery['authorization_endpoint'], port,
                                 request_budget=request_budget)
        except OSError:
            if port == 0:
                raise
            server = LoginServer(attempt, discovery['authorization_endpoint'], 0,
                                 request_budget=request_budget)
        print(f'Continue with ChatGPT: {server.base_url}/', flush=True)
        print(f'Complete browser consent. At most {request_budget} requests; tokens are not saved.', flush=True)
        deadline = time.monotonic() + timeout
        with server:
            while attempt.callback is None and time.monotonic() < deadline:
                server.handle_request()
        if attempt.callback is None:
            raise SafeError('browser_consent_timeout')
        subject = session.exchange(attempt, registration.get('subject_hash'))
        save_registration(path, {'host_id': registration['host_id'],
                                 'client_id': session.client_id, 'subject_hash': subject})
        if not session.has_plan_scope():
            raise SafeError('plan_usage_scope_not_granted')
        if require_renewal:
            session.require_renewable()
        status['validated_sign_in'] = 'PASS'
        yield session
    finally:
        status['token_refreshes'] = session.refresh_count if session else 0
        status['session_cleanup'] = session.revoke() if session else 'NO_TOKEN_SESSION'
        print(f'Session cleanup: {status["session_cleanup"]}', flush=True)
