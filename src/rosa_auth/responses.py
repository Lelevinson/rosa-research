"""Bounded OAuth Responses transport with explicit terminal-stream validation."""
import json
import time
from urllib.request import Request

from .oauth import RESOURCE, SafeError, error_code, open_request, request_json


def parse_events(lines):
    data = []
    size = 0
    for raw in lines:
        line = raw.decode('utf-8').rstrip('\r\n') if isinstance(raw, bytes) else raw.rstrip('\r\n')
        if line.startswith('data:'):
            value = line[5:].lstrip(' ')
            data.append(value)
            size += len(value)
            if size > 4 * 1024 * 1024:
                raise SafeError('stream_event_too_large')
        elif not line and data:
            payload = '\n'.join(data)
            data, size = [], 0
            if payload == '[DONE]':
                return
            try:
                yield json.loads(payload)
            except ValueError:
                raise SafeError('invalid_stream_json') from None


def completed_response(events):
    items = {}
    final_text = []
    event_counts = {}
    started = time.monotonic()
    for index, event in enumerate(events):
        if index > 20000 or time.monotonic() - started > 120:
            raise SafeError('stream_budget_exceeded')
        kind = event.get('type')
        event_counts[kind] = event_counts.get(kind, 0) + 1
        if kind in ('error', 'response.failed', 'response.incomplete'):
            detail = event.get('response', {}).get('error') or event.get('error') or event
            code = detail.get('code') if isinstance(detail, dict) else None
            raise SafeError(error_code(code, kind.replace('.', '_')))
        if kind == 'response.output_item.done':
            item = event.get('item', {})
            if item.get('id'):
                items[item['id']] = item
        if kind == 'response.output_text.done' and isinstance(event.get('text'), str):
            final_text.append(event['text'])
        if kind == 'response.completed':
            response = event.get('response', {})
            if response.get('status') != 'completed' or not isinstance(response.get('output'), list):
                raise SafeError('malformed_completed_response')
            # Keep completed encrypted reasoning items in memory for stateless continuation.
            # They are never included in the sanitized report or Phoenix attributes.
            output = response['output'] or list(items.values())
            response['output'] = [items.get(item.get('id'), item) for item in output]
            response['_stream_final_text'] = ''.join(final_text)
            response['_stream_event_counts'] = event_counts
            return response
    raise SafeError('stream_ended_without_completed')


def output_text(response):
    text = ''.join(content.get('text', '') for item in response.get('output', [])
                   if item.get('type') == 'message' for content in item.get('content', [])
                   if content.get('type') == 'output_text')
    return text or response.get('_stream_final_text', '')


def sanitized_response(response, stage, elapsed):
    """Persist only model text, typed calls, usage and timing; exclude reasoning."""
    return {'stage': stage, 'status': response['status'], 'response_id': response.get('id'),
            'model': response.get('model'), 'usage': response.get('usage'), 'wall_seconds': elapsed,
            'assistant_text': output_text(response),
            'stream_event_counts': response.get('_stream_event_counts', {}),
            'output_shapes': [{'type': item.get('type'), 'keys': sorted(item),
                               'content_shapes': [{'type': part.get('type'), 'keys': sorted(part)}
                                                  for part in item.get('content', [])]}
                              for item in response['output']],
            'tool_calls': [{key: value for key, value in call.items()
                            if key in ('type', 'name', 'namespace', 'arguments', 'call_id')}
                           for call in response['output'] if call.get('type') == 'function_call']}


def build_request(model, history, tools=None):
    if not isinstance(history, list):
        raise SafeError('input_must_be_array')
    if any(item.get('type') == 'message' and item.get('role') == 'system' for item in history):
        raise SafeError('unsupported_system_item')
    payload = {'model': model, 'input': history, 'store': False, 'stream': True}
    if tools:
        if any(tool.get('type') != 'namespace' for tool in tools):
            raise SafeError('tools_must_be_namespaced')
        payload['tools'] = tools
    return payload


class SiwcBackend:
    def __init__(self, access_token=None, *, request_budget=3, token_provider=None):
        if type(request_budget) is not int or not 1 <= request_budget <= 2000:
            raise ValueError('Request budget must be between 1 and 2000')
        self._access_token = access_token
        self._token_provider = token_provider
        self.requests = 0
        self.request_budget = request_budget
        self._unavailable = None

    @property
    def availability_error(self):
        """Credential-free failure state for checkpoints, including swallowed errors."""
        if self._unavailable is None:
            return None
        return {'code': self._unavailable[0], 'http_status': self._unavailable[1]}

    def raise_if_unavailable(self):
        if self._unavailable is not None:
            raise SafeError(*self._unavailable)

    def models(self):
        self.raise_if_unavailable()
        try:
            result = request_json(RESOURCE + '/models', token=self._token())
        except SafeError as error:
            self._unavailable = (error.code, error.status)
            raise
        if not isinstance(result.get('models'), list):
            raise SafeError('unexpected_model_catalog_schema')
        return [{'slug': item['slug'], 'display_name': item.get('display_name', item['slug'])}
                for item in result['models'] if item.get('visibility') == 'list' and item.get('slug')]

    def respond(self, model, history, tools=None):
        self.raise_if_unavailable()
        if self.requests >= self.request_budget:
            raise SafeError('smoke_request_budget_exceeded')
        self.requests += 1
        payload = build_request(model, history, tools)
        try:
            request = Request(RESOURCE + '/responses', data=json.dumps(payload).encode(), headers={
                'Authorization': 'Bearer ' + self._token(),
                'Content-Type': 'application/json', 'Accept': 'text/event-stream'})
            started = time.perf_counter()
            with open_request(request) as stream:
                response = completed_response(parse_events(stream))
        except SafeError as error:
            # Do not spend the rest of a batch on revoked credentials or quota.
            # No inference replay: a prior stream may have partially completed.
            self._unavailable = (error.code, error.status)
            raise
        return response, time.perf_counter() - started

    def close(self):
        self._access_token = None
        self._token_provider = None
        self._unavailable = ('oauth_session_closed', None)

    def _token(self):
        value = self._token_provider() if self._token_provider else self._access_token
        if not value:
            raise SafeError('oauth_session_closed')
        return value


MOCK_TOOLS = [{'type': 'namespace', 'name': 'mock_robot',
    'description': 'Read-only, fixed in-memory robot readiness fixtures. No robot connection.',
    'tools': [{'type': 'function', 'name': 'get_robot_health',
        'description': 'Read the measured battery percentage of mock-robot.', 'strict': True,
        'parameters': {'type': 'object', 'properties': {'robot_id': {'type': 'string', 'enum': ['mock-robot']}},
                       'required': ['robot_id'], 'additionalProperties': False}}]}]


def validated_mock_call(response):
    calls = [item for item in response['output'] if item.get('type') == 'function_call']
    if len(calls) != 1:
        raise SafeError('expected_one_structured_tool_call')
    call = calls[0]
    if call.get('namespace') not in (None, 'mock_robot') or call.get('name') != 'get_robot_health':
        raise SafeError('unexpected_tool_name_or_namespace')
    if not isinstance(call.get('call_id'), str) or not call['call_id']:
        raise SafeError('missing_tool_call_id')
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise SafeError('duplicate_tool_argument')
            result[key] = value
        return result

    try:
        arguments = json.loads(call.get('arguments', ''), object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        raise SafeError('invalid_tool_arguments') from None
    if arguments != {'robot_id': 'mock-robot'}:
        raise SafeError('unexpected_tool_arguments')
    value = {'robot_id': 'mock-robot', 'battery_percent': 73, 'active_arm': 'left', 'source': 'mock'}
    return call, value
