"""Offline renewal/failure checks. All token values are synthetic placeholders."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rosa_auth.batch import checkpointed_trial
from rosa_auth.oauth import ISSUER, MemorySession, SCOPES, SafeError, error_code
from rosa_auth.responses import SiwcBackend
from rosa_auth.session import interactive_session


def session():
    value = MemorySession({'issuer': ISSUER, **{key: ISSUER + '/' + key for key in (
        'authorization_endpoint', 'token_endpoint', 'revocation_endpoint', 'jwks_uri')}})
    value.client_id = 'oaiapp_offline'
    value.tokens = {'access_token': 'OLD_ACCESS', 'refresh_token': 'OLD_REFRESH',
                    'token_type': 'Bearer', 'scope': SCOPES, 'expires_in': 3600}
    return value


def replacement(**changes):
    return {'access_token': 'NEW_ACCESS', 'refresh_token': 'NEW_REFRESH',
            'token_type': 'Bearer', 'expires_in': 3600, **changes}


class OvernightTests(unittest.TestCase):
    def test_optional_renewal_preflight_keeps_default_revoke_cleanup(self):
        for require_renewal, has_refresh in ((False, True), (True, True), (True, False)):
            auth = session()
            if not has_refresh:
                auth.tokens.pop('refresh_token')
            status = {}
            ready = SimpleNamespace(callback={'code': 'FAKE_CODE'})
            with patch('rosa_auth.session.request_json', return_value=auth.discovery), \
                 patch('rosa_auth.session.MemorySession', return_value=auth), \
                 patch('rosa_auth.session.load_registration', return_value={'host_id': 'OFFLINE_HOST'}), \
                 patch('rosa_auth.session.save_registration'), \
                 patch('rosa_auth.session.Attempt', return_value=ready), \
                 patch('rosa_auth.session.LoginServer'), \
                 patch.object(auth, 'exchange', return_value='FAKE_SUBJECT_HASH'), \
                 patch('rosa_auth.oauth.request_json', return_value={}) as revoke, \
                 patch('builtins.print'):
                if require_renewal and not has_refresh:
                    with self.assertRaises(SafeError):
                        with interactive_session(require_renewal=True, status=status):
                            self.fail('Long batch must not start without renewable grant')
                else:
                    with interactive_session(require_renewal=require_renewal, status=status) as active:
                        self.assertIs(active, auth)
                    revoke.assert_called_once()
                    self.assertEqual(status['session_cleanup'], 'REVOKED')
            self.assertIsNone(auth.tokens)
            self.assertEqual(status['token_refreshes'], 0)

    def test_overnight_preflight_requires_granted_offline_scope_and_refresh_token(self):
        auth = session()
        auth.require_renewable()
        for changes in ({'scope': SCOPES.replace('offline_access', '')},
                        {'refresh_token': None}, {'refresh_token': ''}):
            auth = session()
            auth.tokens.update(changes)
            with self.assertRaises(SafeError) as caught:
                auth.require_renewable()
            self.assertEqual(caught.exception.code, 'renewable_authorization_unavailable')

    def test_ten_hour_simulated_batch_renews_without_browser_or_disk(self):
        auth = session()
        auth._expires_at = 3600
        clock = [0]
        def rotate(url, *, form):
            self.assertEqual(form['client_id'], 'oaiapp_offline')
            self.assertEqual(form['resource'], 'https://api.openai.com/v1')
            self.assertNotIn('scope', form)
            number = auth.refresh_count + 1
            return replacement(access_token=f'ACCESS_{number}', refresh_token=f'REFRESH_{number}')
        with patch('rosa_auth.oauth.time.monotonic', side_effect=lambda: clock[0]), \
             patch('rosa_auth.oauth.request_json', side_effect=rotate) as request, \
             patch('rosa_auth.oauth.LoginServer', side_effect=AssertionError('No browser')), \
             patch.object(Path, 'write_text', side_effect=AssertionError('No credential file')):
            self.assertEqual(auth.access_token(), 'OLD_ACCESS')
            for hour in range(1, 11):
                clock[0] = hour * 3600 - 30
                self.assertEqual(auth.access_token(), f'ACCESS_{hour}')
            self.assertEqual(request.call_count, 10)
        self.assertEqual(auth.refresh_count, 10)

    def test_concurrent_access_rotates_only_once(self):
        auth = session()
        with patch('rosa_auth.oauth.request_json', return_value=replacement()) as request:
            with ThreadPoolExecutor(max_workers=8) as executor:
                values = list(executor.map(lambda _: auth.access_token(), range(20)))
            self.assertEqual(set(values), {'NEW_ACCESS'})
            request.assert_called_once()

    def test_scope_changes_block_inference_but_revoke_latest_rotation(self):
        for scope in (SCOPES.replace('resource.invoke', ''), SCOPES + ' unrequested.permission', ''):
            with self.subTest(scope_kind='changed'):
                auth = session()
                with patch('rosa_auth.oauth.request_json', return_value=replacement(scope=scope)) as request:
                    with self.assertRaises(SafeError):
                        auth.access_token()
                    with self.assertRaises(SafeError):
                        auth.access_token()
                    request.assert_called_once()
                with patch('rosa_auth.oauth.request_json', return_value={}) as revoke:
                    self.assertEqual(auth.revoke(), 'REVOKED')
                    self.assertEqual(revoke.call_args.kwargs['form']['token'], 'NEW_REFRESH')

    def test_reordered_or_omitted_scopes_preserve_original_grant(self):
        for changes in ({}, {'scope': ' '.join(reversed(SCOPES.split()))}):
            auth = session()
            with patch('rosa_auth.oauth.request_json', return_value=replacement(**changes)):
                self.assertEqual(auth.access_token(), 'NEW_ACCESS')
            self.assertEqual(set(auth.tokens['scope'].split()), set(SCOPES.split()))

    def test_invalid_lifetimes_never_expose_provider_values_or_retry_rotation(self):
        for lifetime in (None, 'PRIVATE_BAD_EXPIRY', float('nan'), float('inf'), -1, 0, True):
            auth = session()
            old = deepcopy(auth.tokens)
            with patch('rosa_auth.oauth.request_json', return_value=replacement(expires_in=lifetime)) as request:
                with self.assertRaises(SafeError) as caught:
                    auth.access_token()
                self.assertEqual(str(caught.exception), 'invalid_token_lifetime')
                self.assertEqual(auth.tokens, old)
                with self.assertRaises(SafeError):
                    auth.access_token()
                request.assert_called_once()

    def test_terminal_refresh_errors_clear_credentials_without_consent_loop(self):
        for code in ('invalid_grant', 'invalid_refresh_token', 'token_expired',
                     'refresh_token_expired', 'refresh_token_invalidated', 'refresh_token_reused'):
            self.assertEqual(error_code(code), code)
            auth = session()
            with patch('rosa_auth.oauth.request_json', side_effect=SafeError(code, 400)) as request:
                for _ in range(2):
                    with self.assertRaises(SafeError) as caught:
                        auth.access_token()
                    self.assertEqual(caught.exception.code, code)
                request.assert_called_once()
            self.assertIsNone(auth.tokens)

    def test_temporary_refresh_failure_preserves_tokens_until_normal_cleanup(self):
        auth = session()
        old = deepcopy(auth.tokens)
        with patch('rosa_auth.oauth.request_json', side_effect=SafeError('transport_error')) as request:
            with self.assertRaises(SafeError):
                auth.access_token()
            self.assertEqual(auth.tokens, old)
            with self.assertRaises(SafeError):
                auth.access_token()
            request.assert_called_once()
        with patch('rosa_auth.oauth.request_json', side_effect=SafeError('transport_error')):
            self.assertEqual(auth.revoke(), 'NOT_CONFIRMED_NETWORK_OR_PROVIDER_ERROR')
        self.assertIsNone(auth.tokens)
        self.assertIsNone(auth._revoke_token)

    def test_budget_is_not_reset_by_refresh(self):
        auth = session()
        backend = SiwcBackend(token_provider=auth.access_token, request_budget=1)
        final = {'type': 'response.completed', 'response': {'status': 'completed', 'output': []}}
        stream = ('data: ' + json.dumps(final) + '\n\n').encode()
        with patch('rosa_auth.oauth.request_json', return_value=replacement()), \
             patch('rosa_auth.responses.open_request', return_value=io.BytesIO(stream)) as request:
            backend.respond('offline-model', [])
            with self.assertRaises(SafeError) as caught:
                backend.respond('offline-model', [])
            self.assertEqual(caught.exception.code, 'smoke_request_budget_exceeded')
            request.assert_called_once()
        self.assertEqual(backend.requests, 1)
        self.assertEqual(auth.refresh_count, 1)

    def test_checkpoint_stops_actual_rosa_after_it_swallows_401(self):
        from langchain_core.callbacks import BaseCallbackHandler
        from langchain_core.tools import tool
        from rosa_backends import create_mock_agent, create_model

        @tool
        def read_fixture() -> dict:
            """Read an offline test fixture."""
            raise AssertionError('No tool should run after failed inference')

        class Capture(BaseCallbackHandler):
            def __init__(self):
                self.values = []
            def on_llm_error(self, error, **kwargs):
                self.values.append(str(error))

        backend = SiwcBackend(token_provider=lambda: 'PRIVATE_TEST_ACCESS', request_budget=4)
        llm = create_model('siwc', model='offline-model', siwc_transport=backend)
        capture = Capture()
        llm.callbacks = [capture]
        state = {'trials': [{'id': 'completed-before-disconnection', 'status': 'COMPLETE'}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            def checkpoint():
                state.update(availability_error=backend.availability_error, requests=backend.requests)
                pending = path.with_suffix('.tmp')
                pending.write_text(json.dumps(state))
                pending.replace(path)
            with patch('rosa_auth.responses.open_request', side_effect=SafeError('invalid_token', 401)) as request:
                with self.assertRaises(SafeError):
                    for trial in ('interrupted', 'must-not-start'):
                        with checkpointed_trial(backend, checkpoint):
                            state['current_trial'] = trial
                            answer = create_mock_agent(llm, [read_fixture]).invoke('Read the fixture.')
                            self.assertTrue(answer.startswith('An error occurred:'))
                            state['current_status'] = 'INTERRUPTED'
                request.assert_called_once()
                saved = json.loads(path.read_text())
                self.assertEqual(saved['current_trial'], 'interrupted')
                self.assertEqual(saved['trials'][0]['status'], 'COMPLETE')
                self.assertEqual(saved['availability_error'], {'code': 'invalid_token', 'http_status': 401})
                self.assertNotIn('PRIVATE_TEST_ACCESS', path.read_text() + repr(capture.values) +
                                 json.dumps(llm.model_dump()) + json.dumps(llm.request_records))
        llm.close()

    def test_quota_failure_pauses_without_refresh_or_inference_replay(self):
        backend = SiwcBackend('PRIVATE_ACCESS', request_budget=4)
        with patch('rosa_auth.responses.open_request', side_effect=SafeError(
                'subscription_sharing_usage_limit_exceeded', 429)) as request:
            for _ in range(2):
                with self.assertRaises(SafeError):
                    backend.respond('offline-model', [])
            request.assert_called_once()
        self.assertEqual(backend.requests, 1)

    def test_checkpoint_on_other_exception_preserves_original_error(self):
        backend = SiwcBackend('PRIVATE_ACCESS')
        saved = []
        with self.assertRaisesRegex(RuntimeError, 'interrupted'):
            with checkpointed_trial(backend, lambda: saved.append('saved')):
                raise RuntimeError('interrupted')
        self.assertEqual(saved, ['saved'])


if __name__ == '__main__':
    unittest.main()
