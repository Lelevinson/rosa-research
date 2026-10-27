"""Synthetic credentials only; no provider, browser or Windows store contacted."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from rosa_auth.oauth import ISSUER, RESOURCE, SCOPES, SafeError
from rosa_auth.remembered import RememberedSession, remembered_session, sign_out
from rosa_auth.protected_store import WindowsCredentialStore

DISCOVERY = {'issuer': ISSUER, **{key: ISSUER + '/' + key for key in
    ('authorization_endpoint', 'token_endpoint', 'revocation_endpoint', 'jwks_uri')}}
REGISTRATION = {'host_id': 'SYNTHETIC_HOST', 'client_id': 'oaiapp_synthetic', 'subject_hash': 'SYNTHETIC_SUBJECT'}


class FakeStore:
    def __init__(self, record=None): self.record, self.saves, self.deletes = deepcopy(record), 0, 0
    def load(self): return deepcopy(self.record)
    def save(self, record): self.record, self.saves = deepcopy(record), self.saves + 1
    def delete(self): self.record, self.deletes = None, self.deletes + 1
    def close(self): pass


def initial(store=None):
    store = store or FakeStore()
    auth = RememberedSession(DISCOVERY, store, REGISTRATION)
    auth.client_id = REGISTRATION['client_id']
    auth.tokens = {'access_token': 'SYNTHETIC_OLD_ACCESS', 'refresh_token': 'SYNTHETIC_OLD_REFRESH',
                   'token_type': 'Bearer', 'scope': SCOPES, 'expires_in': 3600}
    auth.remember(REGISTRATION['subject_hash'])
    return auth, store


def replacement(**changes):
    return {'access_token': 'SYNTHETIC_NEW_ACCESS', 'refresh_token': 'SYNTHETIC_NEW_REFRESH',
            'token_type': 'Bearer', 'expires_in': 3600, **changes}


class RememberedAuthTests(unittest.TestCase):
    def test_only_refresh_and_validated_registration_metadata_are_stored(self):
        auth, store = initial()
        self.assertNotIn('access_token', store.record)
        self.assertNotIn('id_token', store.record)
        self.assertEqual(store.record['refresh_token'], 'SYNTHETIC_OLD_REFRESH')
        self.assertEqual(store.record['resource'], RESOURCE)
        self.assertNotIn('SYNTHETIC_OLD_ACCESS', json.dumps(store.record))

    def test_resume_forces_refresh_preserves_grant_and_saves_rotated_token(self):
        _, store = initial()
        auth = RememberedSession(DISCOVERY, store, REGISTRATION)
        auth.restore(store.load())
        with patch('rosa_auth.oauth.request_json', return_value=replacement()) as request:
            self.assertEqual(auth.access_token(), 'SYNTHETIC_NEW_ACCESS')
        form = request.call_args.kwargs['form']
        self.assertEqual(form['client_id'], REGISTRATION['client_id'])
        self.assertEqual(form['resource'], RESOURCE)
        self.assertNotIn('scope', form)
        self.assertEqual(store.record['scope'], SCOPES)
        self.assertEqual(store.record['refresh_token'], 'SYNTHETIC_NEW_REFRESH')

    def test_concurrent_access_serializes_refresh_and_persistence(self):
        auth, store = initial()
        auth._expires_at = 0
        with patch('rosa_auth.oauth.request_json', return_value=replacement()) as request:
            with ThreadPoolExecutor(max_workers=8) as pool:
                tokens = list(pool.map(lambda _: auth.access_token(), range(16)))
        self.assertEqual(tokens, ['SYNTHETIC_NEW_ACCESS'] * 16)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(store.saves, 2)

    def test_terminal_refresh_deletes_credentials_without_new_consent(self):
        auth, store = initial()
        with patch('rosa_auth.oauth.request_json', side_effect=SafeError('invalid_grant')):
            with self.assertRaises(SafeError): auth.access_token()
        self.assertIsNone(store.record)
        self.assertIsNone(auth.tokens)

    def test_scope_change_revokes_latest_rotated_token_and_deletes_record(self):
        auth, store = initial()
        with patch('rosa_auth.oauth.request_json', side_effect=[replacement(scope=SCOPES + ' extra'), {}]) as request:
            with self.assertRaises(SafeError): auth.access_token()
        self.assertEqual(request.call_args.kwargs['form']['token'], 'SYNTHETIC_NEW_REFRESH')
        self.assertIsNone(store.record)

    def test_persistence_failure_revokes_rotation_instead_of_leaving_stale_record(self):
        auth, store = initial()
        with patch.object(store, 'save', side_effect=RuntimeError('synthetic storage failure')), \
             patch('rosa_auth.oauth.request_json', side_effect=[replacement(), {}]) as request:
            with self.assertRaisesRegex(SafeError, 'credential_persistence_failed'):
                auth.access_token()
        self.assertEqual(request.call_args.kwargs['form']['token'], 'SYNTHETIC_NEW_REFRESH')
        self.assertIsNone(store.record)

    def test_corrupt_mismatched_or_expanded_records_fail_before_network(self):
        _, store = initial()
        for field, value in [('client_id', 'other'), ('host_id', 'other'), ('subject_hash', 'other'),
                             ('scope', SCOPES + ' other'), ('version', 2), ('access_token', 'unexpected')]:
            record = store.load()
            record[field] = value
            auth = RememberedSession(DISCOVERY, store, REGISTRATION)
            with patch('rosa_auth.oauth.request_json') as request:
                with self.assertRaises(SafeError): auth.restore(record)
                request.assert_not_called()

    def test_opt_in_context_resumes_without_login_and_clears_memory_only(self):
        _, store = initial()
        status = {}
        with patch('rosa_auth.remembered.load_registration', return_value=REGISTRATION), \
             patch('rosa_auth.remembered.request_json', return_value=DISCOVERY), \
             patch('rosa_auth.remembered.LoginServer', side_effect=AssertionError('No browser')), \
             patch('rosa_auth.oauth.request_json', return_value=replacement()):
            with remembered_session(store=store, status=status) as auth:
                self.assertTrue(auth.has_plan_scope())
            self.assertIsNone(auth.tokens)
        self.assertTrue(status['credential_retained'])
        self.assertEqual(status['authorization_source'], 'PROTECTED_REFRESH')
        self.assertEqual(store.record['refresh_token'], 'SYNTHETIC_NEW_REFRESH')
        self.assertNotIn('SYNTHETIC_NEW_REFRESH', json.dumps(status))

    def test_transient_failure_preserves_protected_grant_but_stops_without_browser(self):
        _, store = initial()
        status = {}
        with patch('rosa_auth.remembered.load_registration', return_value=REGISTRATION), \
             patch('rosa_auth.remembered.request_json', return_value=DISCOVERY), \
             patch('rosa_auth.remembered.LoginServer', side_effect=AssertionError('No browser')), \
             patch('rosa_auth.oauth.request_json', side_effect=SafeError('temporary_network_failure')):
            with self.assertRaises(SafeError):
                with remembered_session(store=store, status=status): self.fail('Must stop')
        self.assertTrue(status['authorization_unavailable'])
        self.assertTrue(status['credential_retained'])
        self.assertEqual(store.record['refresh_token'], 'SYNTHETIC_OLD_REFRESH')

    def test_signout_revokes_and_clears_without_refresh_or_inference(self):
        _, store = initial()
        with patch('rosa_auth.remembered.load_registration', return_value=REGISTRATION), \
             patch('rosa_auth.remembered.request_json', return_value=DISCOVERY), \
             patch('rosa_auth.oauth.request_json', return_value={}) as request:
            self.assertEqual(sign_out(store=store), 'REVOKED')
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.kwargs['form']['token_type_hint'], 'refresh_token')
        self.assertIsNone(store.record)

    def test_unconfirmed_remote_signout_is_reported_and_local_credentials_cleared(self):
        _, store = initial()
        with patch('rosa_auth.remembered.load_registration', return_value=REGISTRATION), \
             patch('rosa_auth.remembered.request_json', side_effect=SafeError('network_failure')):
            self.assertEqual(sign_out(store=store), 'LOCAL_CLEARED_REMOTE_REVOCATION_NOT_CONFIRMED')
        self.assertIsNone(store.record)

    def test_profile_names_cannot_inject_shell_or_paths(self):
        for profile in ('../research', 'a;whoami', 'a/b', '', 'a' * 49):
            with patch('rosa_auth.protected_store.subprocess.Popen') as process:
                with self.assertRaises(ValueError): WindowsCredentialStore(profile)
                process.assert_not_called()


if __name__ == '__main__': unittest.main()
