"""LangChain tools with one contract and trace-safe controlled termination."""
import asyncio
from typing import Literal
from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt, StrictStr, ValidationError

Numeric = StrictInt | StrictFloat


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ReadArgs(StrictArgs):
    nodes: list[StrictStr]


class WriteArgs(StrictArgs):
    node_name: StrictStr
    values: dict[StrictStr, Numeric]


class EmptyArgs(StrictArgs):
    pass


class ReportArgs(StrictArgs):
    status: Literal['SUCCESS', 'FAILURE', 'UNKNOWN']
    observed_values: dict[StrictStr, dict[StrictStr, Numeric | None]]


class ReliableTool(StructuredTool):
    session: object

    def _parse_input(self, tool_input, tool_call_id=None):
        try:
            return super()._parse_input(tool_input, tool_call_id)
        except ValidationError as error:
            details = [{'field': '.'.join(map(str, e['loc'])), 'reason': e['type']}
                       for e in error.errors(include_url=False, include_input=False)]
            return self.session.feedback('schema_validation', details)

    def run(self, tool_input, *args, **kwargs):
        with self.session.tool_call(self.name, tool_input):
            return super().run(tool_input, *args, **kwargs)

    async def arun(self, tool_input, *args, **kwargs):
        # Finish the bounded synchronous dispatch and its LangChain callbacks
        # before propagating cancellation. No orphaned background native write.
        task = asyncio.create_task(asyncio.to_thread(self.run, tool_input, *args, **kwargs))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
            if task.done() and not task.cancelled():
                task.exception()  # retrieve worker error without suppressing cancellation
            raise


def make_tools(session):
    definitions = [
        ('read_state', ReadArgs, lambda nodes: session.read(nodes),
         'Read fresh state for canonical node IDs. Returns observed_values keyed by node, plus evidence.'),
        ('write_state', WriteArgs, lambda node_name, values: session.write(node_name, values),
         'Request a bounded state change. Command acceptance alone does not prove goal attainment.'),
        ('verify_outcome', EmptyArgs, lambda: session.verify(),
         'Read fresh outcome evidence and test the requested goal. Available in every configuration.'),
        ('submit_report', ReportArgs, lambda status, observed_values: session.report(status, observed_values),
         'Submit SUCCESS, FAILURE or UNKNOWN with the same node-keyed observed_values from fresh verification. Never invent values.'),
    ]
    return [ReliableTool(name=name, args_schema=schema, func=func, description=description,
                         session=session, handle_tool_error=lambda error: str(error))
            for name, schema, func, description in definitions]
