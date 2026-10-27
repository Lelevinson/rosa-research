"""Opt-in, pre-parser completion handling with shared inference budgets.

No tools are dispatched here. Truncated responses are never reconstructed into
arguments. Every retry is a real, independently metered model invocation.
"""
from copy import deepcopy
import time

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda, RunnableSequence
from rosa import ROSA
from .execution import ControlledStop


RECOVERY_FEEDBACK = (
    'The preceding response was stopped by the generation limit and is incomplete. '
    'No tool calls from that incomplete response were executed. Generate a fresh, '
    'complete next step using the observations and tool results already present. '
    'Do not continue partial JSON or repeat an already accepted write. '
    'Existing task, evidence, safety, and operation limits still apply.'
)


class CompletionGate:
    def __init__(self, *, per_call=256, total_tokens=2048, calls=8,
                 seconds=180, recover=False, recovery_limit=2, tracer=None):
        for value in (per_call, total_tokens, calls):
            if type(value) is not int or value < 1:
                raise ValueError('positive integer inference budgets required')
        if seconds <= 0 or type(recovery_limit) is not int or recovery_limit < 0:
            raise ValueError('invalid recovery/time budget')
        self.per_call, self.total_tokens, self.call_limit = per_call, total_tokens, calls
        self.seconds, self.recover, self.recovery_limit = seconds, recover, recovery_limit
        self.started = time.monotonic()
        self.calls = self.output_tokens = self.input_tokens = self.recoveries = 0
        self.events, self.tracer = [], tracer

    def invoke(self, bound_model, prompt, config=None):
        messages = prompt.to_messages() if hasattr(prompt, 'to_messages') else list(prompt)
        while True:
            remaining = self.total_tokens - self.output_tokens
            if self.calls >= self.call_limit or remaining <= 0:
                raise ControlledStop('completion_shared_inference_budget_exhausted')
            if time.monotonic() - self.started >= self.seconds:
                raise ControlledStop('completion_trial_deadline_exhausted')
            allowance = min(self.per_call, remaining)
            self.calls += 1
            # Explicit full options preserve the identical pinned serving profile.
            message = bound_model.invoke(messages, config=config, options={
                'num_predict': allowance, 'num_ctx': 8192, 'temperature': 0,
                'seed': 42, 'use_mmap': True})
            usage = message.usage_metadata or {}
            if any(type(usage.get(key)) is not int or usage[key] < 0
                   for key in ('input_tokens', 'output_tokens')):
                raise ControlledStop('completion_usage_unavailable_cannot_preserve_budget')
            self.input_tokens += usage['input_tokens']
            self.output_tokens += usage['output_tokens']
            if usage['output_tokens'] > allowance:
                raise ControlledStop('provider_exceeded_requested_output_allowance')
            metadata = message.response_metadata or {}
            reason = metadata.get('done_reason', metadata.get('finish_reason'))
            event = {'call': self.calls, 'allowance': allowance,
                     'input_tokens': usage['input_tokens'], 'output_tokens': usage['output_tokens'],
                     'finish_reason': reason, 'length_terminated': reason == 'length',
                     'response_tool_calls': len(message.tool_calls),
                     'response_invalid_tool_calls': len(message.invalid_tool_calls),
                     'recover_requested': self.recover, 'recovery': None}
            self.events.append(event)
            if reason != 'length' or not self.recover:
                return message
            # Hold back ALL calls in the incomplete response, even if individually
            # parseable. Nothing from it has reached the tool parser/executor.
            if self.recoveries >= self.recovery_limit:
                event['recovery'] = 'STOP_RECOVERY_LIMIT'
                raise ControlledStop('completion_recovery_limit_exhausted')
            if self.calls >= self.call_limit or self.output_tokens >= self.total_tokens:
                event['recovery'] = 'STOP_SHARED_BUDGET'
                raise ControlledStop('completion_shared_inference_budget_exhausted')
            self.recoveries += 1
            event['recovery'] = 'FRESH_NEXT_STEP_NO_DISPATCH'
            if self.tracer:
                with self.tracer.start_as_current_span('completion.recovery') as span:
                    span.set_attribute('openinference.span.kind', 'CHAIN')
                    span.set_attribute('completion.call', self.calls)
                    span.set_attribute('completion.discarded_tool_calls', len(message.tool_calls))
                    span.set_attribute('completion.remaining_output_tokens', self.total_tokens-self.output_tokens)
            # Content is retained as explicitly incomplete context only. Neither
            # structured calls, invalid calls nor provider kwargs are copied.
            messages = [*messages, AIMessage(content=deepcopy(message.content)),
                        HumanMessage(content=RECOVERY_FEEDBACK)]

    def snapshot(self):
        return {'calls': self.calls, 'input_tokens': self.input_tokens,
                'output_tokens': self.output_tokens, 'recoveries': self.recoveries,
                'events': deepcopy(self.events)}


class CompletionAwareROSA(ROSA):
    """Use ROSA's existing prompt/tools/executor, inserting an opt-in model gate.

    This pinned integration checks the existing runnable layout rather than
    silently rebuilding ROSA or replacing its execution loop.
    """
    def __init__(self, *args, completion_gate, **kwargs):
        self.completion_gate = completion_gate
        super().__init__(*args, **kwargs)

    def _get_agent(self):
        from langchain.agents.output_parsers.tools import ToolsAgentOutputParser
        agent = super()._get_agent()
        steps = agent.steps
        if len(steps) != 4 or not isinstance(steps[-1], ToolsAgentOutputParser):
            raise RuntimeError('unsupported_rosa_agent_layout_for_completion_gate')
        bound_model = steps[-2]

        def guarded_model(prompt, config):
            return self.completion_gate.invoke(bound_model, prompt, config)

        return RunnableSequence(*steps[:-2], RunnableLambda(guarded_model), steps[-1])
