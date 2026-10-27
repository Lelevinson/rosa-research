"""Native SIWC Responses transport exposed as a LangChain tool-calling model.

Wire streams are buffered through response.completed. Tokens and raw output
(including encrypted reasoning needed for continuation) remain private and are
never attached to LangChain messages, callback metadata, or serialized models.
"""
from collections import OrderedDict
from copy import deepcopy
import json
import re
from threading import Lock
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import PrivateAttr

from rosa_auth.oauth import SafeError
from rosa_auth.responses import output_text, sanitized_response

NAMESPACE = 'rosa_tools'


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SafeError('duplicate_tool_argument')
        result[key] = value
    return result


class ChatSiwc(BaseChatModel):
    """Bounded text/tool adapter; authentication lifecycle belongs to its caller."""
    model: str
    _backend: object = PrivateAttr()
    _native_outputs: OrderedDict = PrivateAttr(default_factory=OrderedDict)
    _records: list = PrivateAttr(default_factory=list)
    _lock: object = PrivateAttr(default_factory=Lock)

    def __init__(self, *, model, backend):
        super().__init__(model=model, cache=False)
        self._backend = backend

    @property
    def _llm_type(self):
        return 'chatgpt-siwc-responses'

    @property
    def _identifying_params(self):
        return {'model': self.model, 'transport': 'siwc-responses-http'}

    @property
    def request_records(self):
        return deepcopy(self._records)

    def close(self):
        self._native_outputs.clear()
        self._backend.close()

    def bind_tools(self, tools, **kwargs):
        if kwargs:
            raise SafeError('unsupported_tool_binding_option')
        schemas = []
        names = set()
        for tool in tools:
            definition = convert_to_openai_tool(tool)
            if definition.get('type') != 'function':
                raise SafeError('only_function_tools_supported')
            function = definition['function']
            name = function['name']
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', name) or name in names:
                raise SafeError('invalid_or_duplicate_tool_name')
            names.add(name)
            schemas.append({'type': 'function', **function})
        return self.bind(rosa_tools=schemas)

    def _history(self, messages):
        history = []
        pending = set()
        for message in messages:
            if not isinstance(message.content, str):
                raise SafeError('only_text_messages_supported')
            if isinstance(message, (SystemMessage, HumanMessage)):
                if pending:
                    raise SafeError('tool_result_missing')
                # Preserve the instruction hierarchy using the supported role.
                role = 'developer' if isinstance(message, SystemMessage) else 'user'
                history.append({'role': role, 'content': message.content})
            elif isinstance(message, AIMessage):
                if pending:
                    raise SafeError('tool_result_missing')
                native = self._native_outputs.get(message.id)
                if native is not None:
                    history.extend(deepcopy(native))
                elif message.tool_calls:
                    raise SafeError('native_continuation_not_available')
                else:
                    history.append({'role': 'assistant', 'content': message.content})
                pending.update(call['id'] for call in message.tool_calls)
            elif isinstance(message, ToolMessage):
                if message.tool_call_id not in pending:
                    raise SafeError('unexpected_tool_result')
                pending.remove(message.tool_call_id)
                history.append({'type': 'function_call_output',
                                'call_id': message.tool_call_id, 'output': message.content})
            else:
                raise SafeError('unsupported_message_role')
        if pending:
            raise SafeError('tool_result_missing')
        return history

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if stop or set(kwargs) - {'rosa_tools'}:
            raise SafeError('unsupported_generation_option')
        schemas = kwargs.get('rosa_tools', [])
        allowed = {tool['name'] for tool in schemas}
        wire_tools = ([{'type': 'namespace', 'name': NAMESPACE,
                       'description': 'The explicitly registered ROSA tools.', 'tools': schemas}]
                      if schemas else None)
        with self._lock:
            response, elapsed = self._backend.respond(self.model, self._history(messages), wire_tools)
            calls = []
            seen = set()
            for item in response['output']:
                if item.get('type') not in ('function_call', 'message', 'reasoning'):
                    raise SafeError('unsupported_model_output_item')
                if item.get('type') != 'function_call':
                    continue
                if item.get('namespace') != NAMESPACE or item.get('name') not in allowed:
                    raise SafeError('model_requested_unregistered_tool')
                call_id = item.get('call_id')
                if not isinstance(call_id, str) or not call_id or call_id in seen:
                    raise SafeError('invalid_tool_call_id')
                seen.add(call_id)
                try:
                    arguments = json.loads(item.get('arguments', ''), object_pairs_hook=unique_object)
                except (ValueError, TypeError):
                    raise SafeError('invalid_tool_arguments') from None
                if not isinstance(arguments, dict):
                    raise SafeError('tool_arguments_must_be_object')
                calls.append({'name': item['name'], 'args': arguments, 'id': call_id, 'type': 'tool_call'})
            identifier = 'siwc-' + uuid4().hex
            usage = response.get('usage') or {}
            usage_metadata = None
            if all(isinstance(usage.get(k), int) for k in ('input_tokens', 'output_tokens', 'total_tokens')):
                usage_metadata = {key: usage[key] for key in ('input_tokens', 'output_tokens', 'total_tokens')}
            message = AIMessage(id=identifier, content=output_text(response), tool_calls=calls,
                                usage_metadata=usage_metadata,
                                response_metadata={'model_name': self.model, 'finish_reason': 'completed'})
            # Keep transport-only continuation material out of traced AIMessage fields.
            self._native_outputs[identifier] = deepcopy(response['output'])
            while len(self._native_outputs) > 64:
                self._native_outputs.popitem(last=False)
            self._records.append(sanitized_response(response, 'rosa_turn_' + str(len(self._records) + 1), elapsed))
            return ChatResult(generations=[ChatGeneration(message=message)])
