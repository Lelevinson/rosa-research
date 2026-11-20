"""Opt-in native formatting and persistent schemas for pinned Ollama adapters.

No task routing, argument repair, retry, tool execution or global template edits.
The original ConfiguredChatOllama remains unchanged.
"""
import json
from typing import ClassVar

from rosa_backends.chat_ollama import ConfiguredChatOllama

PROFILE_VERSION = 'native-schema-v1'
NATIVE_GUIDANCE = {
    'llama3.1': 'Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}. Do not use variables.',
    'granite3.3': "When a tool is required to answer the user's query, respond only with <|tool_call|> followed by a JSON list of tools used. If a tool does not exist in the provided list of tools, notify the user that you do not have the ability to fulfill the request.",
}


class ToolContractProfile:
    """Mixin before the configured/measured chat class in the MRO.

    Schemas come from the tools bound to THIS request, including after tool
    results. The profile only adds a system message at the wire boundary, so
    conversation history is not mutated or padded on subsequent turns.
    """
    tool_contract_profile: ClassVar[str] = PROFILE_VERSION

    def _chat_params(self, messages, stop=None, **kwargs):
        if kwargs.get('stream', False) is not False:
            raise ValueError('native_schema_v1_requires_explicit_nonstreaming_transport')
        params = super()._chat_params(messages, stop=stop, **kwargs)
        params['stream'] = False
        tools = params.get('tools')
        if tools:
            family = params['model'].partition(':')[0]
            if family not in NATIVE_GUIDANCE:
                raise ValueError('native_schema_v1_unsupported_model_family')
            content = (NATIVE_GUIDANCE[family] + '\n'
                'Available function schemas (retain these after tool results):\n' +
                json.dumps(tools, sort_keys=True))
            rows = list(params['messages'])
            index = next((i for i, row in enumerate(rows) if row['role'] != 'system'), len(rows))
            params['messages'] = rows[:index] + [{'role': 'system', 'content': content}] + rows[index:]
        return params


class ToolContractOllama(ToolContractProfile, ConfiguredChatOllama):
    """Instantiate explicitly to enable the profile; not a default replacement."""
