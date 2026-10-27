"""Opt-in, synchronous ROSA termination after a trusted accepted report.

Uses the existing executor and tool callbacks. Tool output text alone cannot
terminate a run: acceptance must also exist in the bound session's ledger.
"""
from contextlib import contextmanager
import json

from langchain.agents import AgentExecutor
from langchain_core.agents import AgentFinish
from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import RunnableLambda
from langchain_core.tools import ToolException
from rosa import ROSA

from .execution import ControlledStop


@contextmanager
def coordination_span(session, name):
    """Workflow bookkeeping is a CHAIN, not another native/tool dispatch."""
    if session.tracer is None:
        yield
    else:
        with session.tracer.start_as_current_span(name) as span:
            span.set_attribute('openinference.span.kind', 'CHAIN')
            yield


class AcceptedReportExecutor(AgentExecutor):
    terminal_session: object

    def _get_tool_return(self, next_step_output):
        action, observation = next_step_output
        tool = next((t for t in self.tools if t.name == action.tool), None)
        session = self.terminal_session
        if (action.tool == 'submit_report' and getattr(tool, 'session', None) is session
                and isinstance(observation, dict)
                and observation.get('report_accepted') is True
                and session.reports and session.reports[-1].get('accepted') is True
                and observation.get('status') == session.reports[-1]['status']
                and observation.get('observed_values') == session.reports[-1]['observed_values']):
            with coordination_span(session, 'workflow.accepted_report_terminal'):
                session.events.append({'type': 'terminal', 'actor': 'program',
                    'reason': 'validated_accepted_report', 'status': observation['status'],
                    'additional_model_acknowledgement': False})
            return AgentFinish({'output': json.dumps(observation, sort_keys=True)}, '')
        return super()._get_tool_return(next_step_output)


def single_action(output, session):
    """Reject an entire multi-tool response before any of it is dispatched."""
    if isinstance(output, list) and len(output) > 1:
        try:
            session.feedback('multiple_tool_calls_rejected',
                {'requirement': 'Request exactly one tool; no calls from this batch were executed.'})
        except ToolException as error:
            raise OutputParserException(str(error), observation=str(error),
                llm_output='multiple_tool_calls_rejected', send_to_llm=True) from error
    return output


class AcceptedReportROSA(ROSA):
    """Backend-neutral sync prototype; legacy ROSA behavior is unchanged.

    Use a new agent/session per task. Streaming is deliberately unsupported
    until cancellation and concurrent tool dispatch have separate validation.
    """
    def __init__(self, *args, terminal_session, execution_callbacks=(), **kwargs):
        if kwargs.get('streaming', False):
            raise ValueError('accepted-report prototype supports synchronous invoke only')
        self.terminal_session = terminal_session
        self.execution_callbacks = list(execution_callbacks)
        kwargs['streaming'] = False
        kwargs.setdefault('max_iterations', 8)
        super().__init__(*args, **kwargs)

    def _get_agent(self):
        return super()._get_agent() | RunnableLambda(
            lambda output: single_action(output, self.terminal_session))

    def _get_executor(self, verbose):
        original = super()._get_executor(verbose)
        fields = {name: getattr(original, name) for name in AgentExecutor.model_fields}
        if any(t.name == 'submit_report' and t.return_direct for t in original.tools):
            raise ValueError('submit_report must not terminate unconditionally')
        executor = AcceptedReportExecutor(**fields, terminal_session=self.terminal_session)
        # Invocation config propagates to child/ExceptionTool callbacks;
        # constructor-local callbacks do not inherit down the execution tree.
        return executor.with_config(callbacks=self.execution_callbacks) if self.execution_callbacks else executor

    def invoke(self, query):
        if any(r.get('accepted') for r in self.terminal_session.reports):
            raise ControlledStop('session_already_terminal_create_a_new_task_session')
        return super().invoke(query)
