"""Opt-in remembered authorization using existing OAuth validation and renewal.

Default interactive_session remains memory-only and revoke-on-exit. This separate
context retains only a protected refresh credential after explicit opt-in.
No automatic consent, browser clicks, scope expansion or inference replay.
"""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import threading
import time

from .oauth import (Attempt, ISSUER, RESOURCE, SCOPES, TERMINAL_REFRESH_ERRORS,
                    LoginServer, MemorySession, SafeError, load_registration,
                    request_json, save_registration)
from .protected_store import WindowsCredentialStore

_INVALID_REPLACEMENT = frozenset(('oauth_scope_changed', 'unexpected_granted_scopes',
    'plan_usage_scope_not_granted', 'invalid_granted_scopes', 'invalid_refresh_response',
    'invalid_access_token_response', 'invalid_token_lifetime'))


class RememberedSession(MemorySession):
    """Same OAuth protocol, with serialized atomic persistence after rotation."""

    def __init__(self, discovery, store, registration):
        super().__init__(discovery)
        self._store, self._registration = store, dict(registration)
        self._subject_hash = None
        self._persistence_lock = threading.RLock()

    def remember(self, subject_hash):
        self.require_renewable()
        if not isinstance(subject_hash, str) or not subject_hash:
            raise SafeError('validated_identity_required_for_persistence')
        self._subject_hash = subject_hash
        self._persist()

    def _persist(self):
        self.require_renewable()
        record = {'version': 1, 'resource': RESOURCE,
            'host_id': self._registration['host_id'], 'client_id': self.client_id,
            'subject_hash': self._subject_hash, 'scope': self.tokens['scope'],
            'refresh_token': self.tokens['refresh_token']}
        try:
            self._store.save(record)
        except BaseException:
            # A rotation may already have happened. Never leave a stale credential
            # looking usable after persistence failed; revoke latest before clearing.
            try: super().revoke()
            finally: self._store.delete()
            raise SafeError('credential_persistence_failed') from None

    def restore(self, record):
        expected = {'version', 'resource', 'host_id', 'client_id', 'subject_hash', 'scope', 'refresh_token'}
        if not isinstance(record, dict) or set(record) != expected:
            raise SafeError('invalid_protected_credential_record')
        if (record['version'] != 1 or record['resource'] != RESOURCE or
                any(not isinstance(record[k], str) or not record[k] for k in expected - {'version'}) or
                record['host_id'] != self._registration.get('host_id') or
                record['client_id'] != self._registration.get('client_id') or
                record['subject_hash'] != self._registration.get('subject_hash')):
            raise SafeError('credential_account_or_client_mismatch')
        granted = set(record['scope'].split())
        if not {'offline_access', 'resource.invoke', 'chatgpt.tokens.use.direct'} <= granted <= set(SCOPES.split()):
            raise SafeError('invalid_saved_scope_grant')
        self.client_id, self._subject_hash = record['client_id'], record['subject_hash']
        self.tokens = {'access_token': 'REFRESH_REQUIRED_NOT_AN_ACCESS_TOKEN', 'token_type': 'Bearer',
                       'expires_in': 1, 'scope': record['scope'], 'refresh_token': record['refresh_token']}
        self._revoke_token = record['refresh_token']
        self._expires_at = 0  # Force provider renewal before any actual inference.

    def access_token(self):
        with self._persistence_lock:
            before = self.refresh_count
            try:
                token = super().access_token()
            except SafeError as error:
                if error.code in TERMINAL_REFRESH_ERRORS:
                    self._store.delete()
                elif error.code in _INVALID_REPLACEMENT:
                    self.revoke()
                raise
            if self.refresh_count != before:
                self._persist()
            return token

    def revoke(self):
        with self._persistence_lock:
            try:
                return super().revoke()
            finally:
                self._store.delete()

    def clear_memory(self):
        # Persisted refresh remains explicitly authorized until sign-out/revocation.
        with self._persistence_lock, self._refresh_lock:
            if self.tokens: self.tokens.clear()
            self.tokens, self._revoke_token = None, None
            self._failure = ('oauth_session_closed', None)


@contextmanager
def remembered_session(*, request_budget=6, timeout=900, port=1455,
                       profile='research', status=None, store=None):
    """Explicit opt-in. Use one context/leased profile at a time; no silent fallback.

    Expired/revoked credentials stop and require a later manual login. They do not
    trigger a consent popup in the middle of a batch. Progress remains caller-owned.
    """
    status = status if status is not None else {}
    owned = store is None
    store = store or WindowsCredentialStore(profile)
    active, ready = None, False
    try:
        registration_path = Path.home() / '.local/share/rosa-siwc/registration.json'
        registration = load_registration(registration_path)
        discovery = request_json(ISSUER + '/.well-known/openid-configuration')
        active = RememberedSession(discovery, store, registration)
        record = store.load()
        if record is not None:
            active.restore(record)
            try:
                active.access_token()  # No browser and no inference request.
            except SafeError:
                status['authorization_unavailable'] = True
                raise
            status['authorization_source'] = 'PROTECTED_REFRESH'
        else:
            attempt = Attempt(registration['host_id'], registration.get('client_id'))
            try:
                server = LoginServer(attempt, discovery['authorization_endpoint'], port, request_budget=request_budget)
            except OSError:
                if port == 0: raise
                server = LoginServer(attempt, discovery['authorization_endpoint'], 0, request_budget=request_budget)
            print(f'Continue with ChatGPT: {server.base_url}/', flush=True)
            print('Complete initial sign-in manually. Remembered authorization is enabled.', flush=True)
            deadline = time.monotonic() + timeout
            with server:
                while attempt.callback is None and time.monotonic() < deadline:
                    server.handle_request()
            if attempt.callback is None: raise SafeError('browser_consent_timeout')
            subject = active.exchange(attempt, registration.get('subject_hash'))
            save_registration(registration_path, {'host_id': registration['host_id'],
                'client_id': active.client_id, 'subject_hash': subject})
            active.remember(subject)
            status['authorization_source'] = 'MANUAL_INITIAL_AUTHORIZATION'
        active.require_renewable()
        status['validated_sign_in'] = 'PASS'
        ready = True
        yield active
    finally:
        if active:
            status['token_refreshes'] = active.refresh_count
            if ready or status.get('authorization_source') == 'PROTECTED_REFRESH' or status.get('authorization_unavailable'):
                active.clear_memory()
                retained = store.load() is not None
                status['credential_retained'] = retained
                status['session_cleanup'] = ('MEMORY_CLEARED_OPTIONAL_PROTECTED_CREDENTIAL_RETAINED'
                    if retained else 'MEMORY_CLEARED_NO_STORED_AUTHORIZATION')
            else:
                status['session_cleanup'] = active.revoke()
        if owned: store.close()


def sign_out(*, profile='research', store=None):
    owned = store is None
    store = store or WindowsCredentialStore(profile)
    active = None
    try:
        record = store.load()
        if record is None: return 'NO_REMEMBERED_AUTHORIZATION'
        registration = load_registration(Path.home() / '.local/share/rosa-siwc/registration.json')
        discovery = request_json(ISSUER + '/.well-known/openid-configuration')
        active = RememberedSession(discovery, store, registration)
        active.restore(record)
        return active.revoke()
    except SafeError:
        store.delete()
        return 'LOCAL_CLEARED_REMOTE_REVOCATION_NOT_CONFIRMED'
    finally:
        if active: active.clear_memory()
        if owned: store.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('login', 'status', 'logout', 'storage-self-test'))
    parser.add_argument('--profile', default='research')
    args = parser.parse_args()
    if args.action == 'storage-self-test':
        # Dedicated dummy profile; never read/write/delete real saved credentials.
        with WindowsCredentialStore('storage_self_test') as store:
            if store.load() is not None: raise SafeError('self_test_profile_already_exists')
            record = {'synthetic': 'DPAPI_SELF_TEST_NO_REAL_CREDENTIAL'}
            try:
                store.save(record)
                if store.load() != record: raise SafeError('storage_roundtrip_failed')
                try:
                    concurrent = WindowsCredentialStore('storage_self_test')
                except SafeError as error:
                    if error.code != 'credential_profile_in_use': raise
                else:
                    concurrent.close()
                    raise SafeError('profile_lease_not_enforced')
            finally: store.delete()
        print(json.dumps({'protected_storage_roundtrip': 'PASS', 'concurrent_profile_lease': 'PASS', 'real_credentials_used': False}))
    elif args.action == 'logout':
        print(json.dumps({'sign_out': sign_out(profile=args.profile)}))
    elif args.action == 'status':
        with WindowsCredentialStore(args.profile) as store:
            print(json.dumps({'remembered_record_present': store.load() is not None,
                              'provider_validity_checked': False}))
    else:
        status = {}
        with remembered_session(profile=args.profile, request_budget=1, status=status):
            pass  # Zero inference; initial manual sign-in or protected refresh only.
        print(json.dumps(status))


if __name__ == '__main__': main()
