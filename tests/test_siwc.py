"""Offline security and wire-contract tests; never use real credentials."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import socket
import threading
import time
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

from rosa_auth.oauth import (Attempt, ISSUER, LoginServer, MemorySession, PLAN_SCOPE, SafeError,
                             error_code, load_registration, pkce_challenge,
                             save_registration, validate_identity)
from rosa_auth.responses import (MOCK_TOOLS, SiwcBackend, build_request, completed_response,
                                 parse_events, sanitized_response, validated_mock_call)


class OAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def token(self, **changes):
        claims = {'iss': ISSUER, 'aud': 'oaiapp_test', 'sub': 'offline-user',
                  'exp': int(time.time()) + 300, 'nonce': 'offline-nonce'}
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm='RS256')

    def test_pkce_rfc7636_vector(self):
        self.assertEqual(pkce_challenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk'),
                         'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM')

    def test_idle_browser_preconnection_cannot_block_listener_deadline(self):
        attempt = Attempt('urn:uuid:offline-host')
        with LoginServer(attempt, ISSUER + '/authorize', 0) as server:
            server.request_timeout = 0.1
            worker = threading.Thread(target=server.handle_request, daemon=True)
            worker.start()
            with socket.create_connection(server.server_address, timeout=1):
                worker.join(timeout=2)
                self.assertFalse(worker.is_alive(), 'Idle browser socket blocked the listener')
            self.assertIsNone(attempt.callback)

    def test_authorization_uses_dynamic_client_only_for_registration(self):
        attempt = Attempt('urn:uuid:offline-host')
        attempt.redirect_uri = 'http://127.0.0.1:1455/auth/callback'
        params = parse_qs(urlsplit(attempt.authorization_url(ISSUER + '/authorize')).query)
        self.assertEqual(params['client_id'], ['dynamic_agent_client'])
        self.assertIn('agent_name_hint', params)
        self.assertEqual(params['code_challenge_method'], ['S256'])
        attempt.saved_client_id = 'oaiapp_test'
        returning = parse_qs(urlsplit(attempt.authorization_url(ISSUER + '/authorize')).query)
        self.assertEqual(returning['client_id'], ['oaiapp_test'])
        self.assertNotIn('agent_name_hint', returning)

    def test_callback_rejects_state_client_mismatch_and_duplicate_parameters(self):
        attempt = Attempt('urn:uuid:offline-host', 'oaiapp_test')
        for query in (urlencode({'state': 'wrong', 'code': 'secret'}),
                      urlencode({'state': attempt.state, 'code': 'secret', 'client_id': 'different'}),
                      urlencode({'state': attempt.state, 'code': 'secret'}) + '&code=duplicate'):
            with self.subTest(query_kind=query.split('=')[0]), self.assertRaises(SafeError):
                attempt.accept_callback(query)
        self.assertIsNone(attempt.callback)

    def test_callback_requires_issued_client_and_rejects_replay(self):
        attempt = Attempt('urn:uuid:offline-host')
        with self.assertRaises(SafeError):
            attempt.accept_callback(urlencode({'state': attempt.state, 'code': 'offline-code'}))
        attempt.accept_callback(urlencode({'state': attempt.state, 'code': 'offline-code', 'client_id': 'oaiapp_test'}))
        with self.assertRaises(SafeError):
            attempt.accept_callback(urlencode({'state': attempt.state, 'code': 'replay', 'client_id': 'oaiapp_test'}))
        self.assertNotIn('offline-code', repr(attempt))

    def test_denied_consent_is_not_a_successful_code_exchange(self):
        attempt = Attempt('urn:uuid:offline-host')
        attempt.accept_callback(urlencode({'state': attempt.state, 'error': 'access_denied'}))
        self.assertEqual(attempt.callback, {'error': 'access_denied'})

    def test_identity_signature_nonce_issuer_audience_expiry_and_account(self):
        expected = hashlib.sha256(b'offline-user').hexdigest()
        self.assertEqual(validate_identity(self.token(), key=self.key.public_key(), client_id='oaiapp_test',
                                          nonce='offline-nonce'), expected)
        for changes in ({'iss': 'https://example.com'}, {'aud': 'wrong'}, {'nonce': 'wrong'},
                        {'exp': int(time.time()) - 90}, {'sub': ''}):
            with self.subTest(changes=changes), self.assertRaises(SafeError):
                validate_identity(self.token(**changes), key=self.key.public_key(),
                                  client_id='oaiapp_test', nonce='offline-nonce')
        with self.assertRaises(SafeError):
            validate_identity(self.token(), key=self.key.public_key(), client_id='oaiapp_test',
                              nonce='offline-nonce', expected_subject_hash='different-account')
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(SafeError):
            validate_identity(self.token(), key=other_key.public_key(), client_id='oaiapp_test', nonce='offline-nonce')

    def test_registration_never_persists_token_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'registration.json'
            first = load_registration(path)
            self.assertEqual(load_registration(path), first)
            save_registration(path, {**first, 'client_id': 'oaiapp_test', 'access_token': 'SECRET', 'refresh_token': 'SECRET'})
            self.assertNotIn('SECRET', path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_revocation_uses_refresh_token_and_clears_memory(self):
        endpoints = {'issuer': ISSUER, **{name: ISSUER + '/' + name for name in (
            'authorization_endpoint', 'token_endpoint', 'revocation_endpoint', 'jwks_uri')}}
        session = MemorySession(endpoints)
        session.client_id = 'oaiapp_test'
        session.tokens = {'access_token': 'ACCESS_SECRET', 'refresh_token': 'REFRESH_SECRET', 'scope': PLAN_SCOPE}
        self.assertTrue(session.has_plan_scope())
        with patch('rosa_auth.oauth.request_json', return_value={}) as request:
            self.assertEqual(session.revoke(), 'REVOKED')
            self.assertEqual(request.call_args.kwargs['form']['token'], 'REFRESH_SECRET')
        self.assertIsNone(session.tokens)

    def test_untrusted_provider_endpoint_and_arbitrary_errors_are_rejected(self):
        with self.assertRaises(SafeError):
            MemorySession({'issuer': ISSUER, 'authorization_endpoint': 'https://example.com/authorize'})
        self.assertEqual(error_code('this contains ACCESS_SECRET'), 'request_failed')
        self.assertEqual(error_code('subscription_sharing_user_not_eligible'), 'subscription_sharing_user_not_eligible')

    def test_memory_refresh_rotates_once_and_revokes_latest_refresh_token(self):
        endpoints = {'issuer': ISSUER, **{name: ISSUER + '/' + name for name in (
            'authorization_endpoint', 'token_endpoint', 'revocation_endpoint', 'jwks_uri')}}
        session = MemorySession(endpoints)
        session.client_id = 'oaiapp_test'
        session.tokens = {'access_token': 'OLD_ACCESS', 'refresh_token': 'OLD_REFRESH', 'scope': PLAN_SCOPE}
        renewed = {'access_token': 'NEW_ACCESS', 'refresh_token': 'NEW_REFRESH',
                   'token_type': 'Bearer', 'expires_in': 3600}
        with patch('rosa_auth.oauth.request_json', return_value=renewed) as request:
            self.assertEqual(session.access_token(), 'NEW_ACCESS')
            self.assertEqual(session.access_token(), 'NEW_ACCESS')
            request.assert_called_once()
            self.assertEqual(request.call_args.kwargs['form']['refresh_token'], 'OLD_REFRESH')
            self.assertNotIn('scope', request.call_args.kwargs['form'])
        self.assertEqual(session.refresh_count, 1)
        with patch('rosa_auth.oauth.request_json', return_value={}) as revoke:
            session.revoke()
            self.assertEqual(revoke.call_args.kwargs['form']['token'], 'NEW_REFRESH')

    def test_invalid_refresh_does_not_replace_last_revokeable_token_set(self):
        endpoints = {'issuer': ISSUER, **{name: ISSUER + '/' + name for name in (
            'authorization_endpoint', 'token_endpoint', 'revocation_endpoint', 'jwks_uri')}}
        session = MemorySession(endpoints)
        session.client_id = 'oaiapp_test'
        old = {'access_token': 'OLD_ACCESS', 'refresh_token': 'OLD_REFRESH', 'scope': PLAN_SCOPE}
        session.tokens = dict(old)
        with patch('rosa_auth.oauth.request_json', return_value={'access_token': 'NEW_ACCESS'}):
            with self.assertRaises(SafeError):
                session.access_token()
        self.assertEqual(session.tokens, old)


class ResponsesTests(unittest.TestCase):
    def completed(self, output=None):
        return {'type': 'response.completed', 'response': {'status': 'completed', 'output': output or []}}

    def tool(self, **changes):
        return {'type': 'function_call', 'namespace': 'mock_robot', 'name': 'get_robot_health',
                'call_id': 'offline-call', 'arguments': '{"robot_id":"mock-robot"}', **changes}

    def test_wire_contract_has_no_unsupported_fields(self):
        payload = build_request('account-model', [{'role': 'user', 'content': 'test'}], MOCK_TOOLS)
        self.assertFalse(payload['store'])
        self.assertTrue(payload['stream'])
        self.assertEqual(set(payload), {'model', 'input', 'store', 'stream', 'tools'})
        with self.assertRaises(SafeError):
            build_request('account-model', [{'role': 'user', 'content': 'test'}], [{'type': 'function'}])

    def test_sse_requires_completed_not_just_text_or_done_marker(self):
        raw = b'data: {"type":"response.output_text.delta","delta":"READY"}\n\ndata: [DONE]\n\n'
        with self.assertRaises(SafeError):
            completed_response(parse_events(io.BytesIO(raw)))
        result = completed_response([self.completed()])
        self.assertEqual(result['status'], 'completed')

    def test_failure_after_text_is_still_failure(self):
        with self.assertRaisesRegex(SafeError, 'subscription_sharing_usage_limit_exceeded'):
            completed_response([{'type': 'response.output_text.delta', 'delta': 'OK'},
                {'type': 'response.failed', 'response': {'error': {'code': 'subscription_sharing_usage_limit_exceeded'}}}])

    def test_partial_tool_call_does_not_count_as_completed_inference(self):
        with self.assertRaises(SafeError):
            completed_response([{'type': 'response.output_item.done', 'item': self.tool()}])

    def test_stream_items_survive_an_empty_terminal_output_array(self):
        item = {'id': 'msg1', 'type': 'message', 'role': 'assistant',
                'content': [{'type': 'output_text', 'text': 'READY'}]}
        result = completed_response([{'type': 'response.output_item.done', 'item': item}, self.completed()])
        self.assertEqual(sanitized_response(result, 'test', 1)['assistant_text'], 'READY')
        self.assertEqual(result['output'], [item])

    def test_final_text_event_can_supply_text_only_after_completed(self):
        result = completed_response([{'type': 'response.output_text.done', 'text': 'READY'}, self.completed()])
        self.assertEqual(sanitized_response(result, 'test', 1)['assistant_text'], 'READY')
        with self.assertRaises(SafeError):
            completed_response([{'type': 'response.output_text.done', 'text': 'READY'}])

    def test_completed_reasoning_is_retained_in_memory_but_excluded_from_reports(self):
        final = {'id': 'r1', 'type': 'reasoning', 'encrypted_content': 'PRIVATE_REASONING'}
        result = completed_response([{'type': 'response.output_item.done', 'item': final},
                                     self.completed([{'id': 'r1', 'type': 'reasoning'}])])
        self.assertEqual(result['output'][0]['encrypted_content'], 'PRIVATE_REASONING')
        self.assertNotIn('PRIVATE_REASONING', json.dumps(sanitized_response(result, 'test', 1.0)))

    def test_tool_name_arguments_and_call_id_are_validated_before_execution(self):
        call, value = validated_mock_call({'output': [self.tool()]})
        self.assertEqual(value['battery_percent'], 73)
        self.assertEqual(call['call_id'], 'offline-call')
        for changes in ({'name': 'execute_motion'}, {'namespace': 'untrusted'}, {'call_id': ''},
                        {'arguments': '{}'}, {'arguments': 'not JSON'},
                        {'arguments': '{"robot_id":"bad","robot_id":"mock-robot"}'}):
            with self.subTest(changes=changes), self.assertRaises(SafeError):
                validated_mock_call({'output': [self.tool(**changes)]})

    def test_textual_fake_call_is_not_native_tool_call(self):
        with self.assertRaises(SafeError):
            validated_mock_call({'output': [{'type': 'message', 'content': [{'type': 'output_text',
                                   'text': '<tool_call>get_robot_health</tool_call>'}]}]})

    def test_three_request_budget_is_enforced_before_network(self):
        backend = SiwcBackend('DO_NOT_PRINT_SECRET')
        backend.requests = 3
        with patch('rosa_auth.responses.open_request') as request, self.assertRaises(SafeError):
            backend.respond('account-model', [])
        request.assert_not_called()
        backend.close()
        self.assertIsNone(backend._access_token)

    def test_live_token_provider_is_not_retained_after_close(self):
        backend = SiwcBackend(token_provider=lambda: 'PRIVATE_TOKEN', request_budget=1200)
        self.assertEqual(backend._token(), 'PRIVATE_TOKEN')
        backend.close()
        with self.assertRaises(SafeError):
            backend._token()


if __name__ == '__main__':
    unittest.main()
