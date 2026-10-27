"""Opt-in public ROSA integration and metering; no experiment dependencies."""
from copy import deepcopy
import json
import time

from pydantic import BaseModel, ConfigDict, Field
from .bounded_macro import MacroInvocation
from .completion import CompletionAwareROSA
from .execution import ControlledStop
from .prompt_contract import BoundedPromptROSA
from .terminal import AcceptedReportROSA


class InferenceLimits(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    calls: int = Field(default=8, ge=1)
    output_tokens: int = Field(default=2048, ge=1)
    local_per_call: int = Field(default=1024, ge=1)


class InferenceBudget:
    """Reserve before requests; count censored calls; never replay generation.

    Port of the frozen pilot's gate, parameterized instead of importing its
    configuration. Ollama context/temperature/seed stay on the supplied model.
    A batch_reserve callback must enforce any multi-task cumulative allowance.
    """

    def __init__(self, invocation, *, backend, limits=None, batch_reserve=None, local_options=None):
        if backend not in ('ollama', 'siwc', 'scripted'):
            raise ValueError('explicit_supported_backend_required')
        self.invocation, self.backend = invocation, backend
        limits = InferenceLimits() if limits is None else limits
        if not isinstance(limits, InferenceLimits):
            raise TypeError('limits_requires_InferenceLimits')
        self.limits = InferenceLimits.model_validate(limits.model_dump())
        self.batch_reserve = batch_reserve
        self.local_options = deepcopy(local_options or {})
        self.calls = self.input_tokens = self.output_tokens = 0
        self.events = []

    def invoke(self, model, prompt, config=None):
        remaining = self.limits.output_tokens - self.output_tokens
        if self.calls >= self.limits.calls or remaining <= 0:
            raise ControlledStop('inference_budget_exhausted_before_dispatch')
        budget = self.invocation.session.budget
        if time.monotonic() - budget.started >= budget.seconds:
            raise ControlledStop('inference_deadline_exhausted_before_dispatch')
        if self.batch_reserve is not None:
            self.batch_reserve()
        allowance = min(self.limits.local_per_call, remaining) if self.backend == 'ollama' else None
        self.calls += 1
        event = {'call': self.calls, 'status': 'UNRETURNED',
                 'requested_output_allowance': allowance, 'usage': None, 'finish_reason': None}
        self.events.append(event)
        options = {'options': {**self.local_options, 'num_predict': allowance}} if allowance is not None else {}
        message = model.invoke(prompt, config=config, **options)
        usage = message.usage_metadata or {}
        if any(type(usage.get(k)) is not int or usage[k] < 0
               for k in ('input_tokens', 'output_tokens', 'total_tokens')):
            event['status'] = 'RETURNED_USAGE_INVALID'
            raise ControlledStop('returned_usage_missing_or_invalid')
        self.input_tokens += usage['input_tokens']
        self.output_tokens += usage['output_tokens']
        reason = (message.response_metadata or {}).get('done_reason',
                  (message.response_metadata or {}).get('finish_reason'))
        event.update(status='RETURNED', usage=dict(usage), finish_reason=reason)
        if time.monotonic() - budget.started >= budget.seconds:
            raise ControlledStop('inference_returned_after_deadline_no_tool_dispatch')
        if allowance is not None and usage['output_tokens'] > allowance:
            raise ControlledStop('provider_exceeded_requested_output_allowance')
        if self.output_tokens > self.limits.output_tokens:
            raise ControlledStop('observed_output_threshold_exceeded_no_tools_dispatched')
        if reason == 'length':
            event['tool_calls_withheld'] = len(message.tool_calls)
            raise ControlledStop('truncated_response_no_tool_dispatch_no_automatic_retry')
        return message

    def snapshot(self):
        unreturned = [e for e in self.events if e['status'] == 'UNRETURNED']
        invalid = any(e['status'] == 'RETURNED_USAGE_INVALID' for e in self.events)
        upper = None if invalid else (self.output_tokens + sum(e['requested_output_allowance'] for e in unreturned)
            if self.backend == 'ollama' else self.output_tokens if not unreturned else None)
        return {'calls': self.calls, 'known_input_tokens': self.input_tokens,
                'known_output_tokens': self.output_tokens, 'output_upper_bound': upper,
                'usage_complete': all(e['status'] == 'RETURNED' for e in self.events),
                'events': deepcopy(self.events)}


class MacroROSA(BoundedPromptROSA, AcceptedReportROSA, CompletionAwareROSA):
    """Synchronous, fresh-task ROSA with common prompt, metering and termination.

    Backend credential/model lifetime remains with the caller. Robot-specific
    instructions can be supplied via prompts; default upstream ROSA is untouched.
    """

    def __init__(self, llm, invocation: MacroInvocation, *, backend,
                 inference_limits=None, batch_reserve=None, prompts=None, callbacks=()):
        self.macro_invocation = invocation
        # ChatOllama treats a per-request options dictionary as a replacement.
        # Preserve configured serving options instead of resetting context/seed.
        option_names = ('mirostat', 'mirostat_eta', 'mirostat_tau', 'num_ctx', 'num_gpu',
                        'num_thread', 'repeat_last_n', 'repeat_penalty', 'temperature',
                        'seed', 'stop', 'tfs_z', 'top_k', 'top_p')
        local_options = {name: getattr(llm, name) for name in option_names
                         if getattr(llm, name, None) is not None} if backend == 'ollama' else {}
        self.inference_budget = InferenceBudget(invocation, backend=backend,
            limits=inference_limits, batch_reserve=batch_reserve, local_options=local_options)
        super().__init__(ros_version=2, llm=llm, terminal_session=invocation.session,
            completion_gate=self.inference_budget, tools=invocation.tools,
            load_default_tools=False, streaming=False, accumulate_chat_history=False,
            max_iterations=self.inference_budget.limits.calls, prompts=prompts,
            execution_callbacks=callbacks)

    def invoke(self, query):
        # Always include the public permission catalogue. Never attach evaluator
        # labels or private observations to the prompt.
        request = query + '\nPublic authorized skill catalogue: ' + json.dumps(
            self.macro_invocation.catalogue, sort_keys=True)
        return super().invoke(request)


__all__ = ['MacroROSA', 'InferenceLimits', 'InferenceBudget']
