"""Demo loop (LABEL: a plain tool-calling loop written for the demo, NOT his frozen steady loop `harness`/`run_pilot`, which are not public).
Rules taken from his public description: a short read menu plus a structured `final_answer` tool; the only terminal is a valid `final_answer` (non-empty JSON object);
every failed call comes back as text and the episode goes on; the name fix is applied to the submitted answer and the raw answer is kept beside it.
Added by the demo: the `run_skill` tool (at most 2 calls per task, one per response) and a request cap."""
import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from . import soft_errors
from .events import EventLog

FINAL_NAME = 'final_answer'
FINAL_DESCRIPTION = 'Give the final answer as a JSON object and finish.'   # verbatim, his smoke_loop.py:37-38 / run_action_study.py:47-48


class FinalArgs(BaseModel):
    answer: dict


def final_tool():
    """Schema carrier only: the loop intercepts the call (it is the terminal)."""
    return StructuredTool(name=FINAL_NAME, description=FINAL_DESCRIPTION, args_schema=FinalArgs, func=lambda answer: answer)


def task_message(task_text, registry):
    # Same construction as MacroROSA.invoke (macro_agent.py:115-119): the public catalogue is appended to the user request.
    return task_text + '\nPublic authorized skill catalogue: ' + json.dumps(registry.catalogue(), sort_keys=True)


def run_episode(task_text, model_invoke, tools, system_prompt, log, *, registry, name_fixer, skill_runner=None, max_requests=8, extra_context=None):
    """tools: menu tools + run_skill tool (final_answer is added here). model_invoke(messages) -> AIMessage. Returns a result dict; the full event log is in `log`."""
    by_name = {t.name: t for t in tools}
    final = final_tool()
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=task_message(task_text, registry))]
    outputs, ending, accepted, raw, namefix_events = [], 'request_cap', None, None, []
    log.add('episode_start', task=task_text, tools=[t.name for t in tools] + [FINAL_NAME], max_requests=max_requests, **(extra_context or {}))
    for request in range(1, max_requests + 1):
        reply = model_invoke(messages)
        log.add('model_request', number=request, usage=reply.usage_metadata, tool_calls=[{'name': c['name'], 'args': c['args']} for c in reply.tool_calls],
                content=reply.content if isinstance(reply.content, str) else str(reply.content))
        messages.append(reply)
        if not reply.tool_calls:
            ending = 'text_without_final_answer'
            break
        skill_this_response, finished = 0, False
        for call in reply.tool_calls:
            name, args = call['name'], call['args']
            if name == FINAL_NAME:
                problems = soft_errors.precheck(final, args)
                if not problems and not args['answer']:
                    problems = ['field "answer": must be a non-empty JSON object']
                if problems:
                    text = 'Error calling final_answer: %s. Fix the arguments and call again.' % '; '.join(problems)
                    log.add('tool_call', name=name, args=args, ok=False, result=text)
                    messages.append(ToolMessage(content=text, tool_call_id=call['id']))
                    continue
                raw = args['answer']
                accepted, namefix_events, ledger_size = name_fixer.apply(task_text, outputs, raw)
                log.add('final_answer_original', answer=raw)
                log.add('namefix', rule=name_fixer.rule.RULE_NAME, changed=accepted != raw, events=namefix_events, ledger_size=ledger_size, **name_fixer.provenance)
                log.add('final_answer_accepted', answer=accepted)
                ending, finished = 'final_answer', True
                break
            tool = by_name.get(name)
            if tool is None:
                text = 'Error: unknown tool "%s". Available tools: %s.' % (name, ', '.join(sorted(list(by_name) + [FINAL_NAME])))
                log.add('tool_call', name=name, args=args, ok=False, result=text)
                messages.append(ToolMessage(content=text, tool_call_id=call['id']))
                continue
            if name == 'run_skill':
                skill_this_response += 1
                if skill_this_response > 1 or (skill_runner and skill_runner.calls >= skill_runner.max_calls):
                    why = 'one run_skill per response' if skill_this_response > 1 else 'run_skill limit reached (%d per task)' % skill_runner.max_calls
                    text = 'Error: %s. Nothing was run.' % why
                    log.add('tool_call', name=name, args=args, ok=False, result=text)
                    messages.append(ToolMessage(content=text, tool_call_id=call['id']))
                    continue
            start_seq = log.add('tool_call_start', name=name, args=args)
            ok, text, output = soft_errors.execute_tool(tool, args)
            log.add('tool_call', name=name, args=args, ok=ok, result=text, start_seq=start_seq)
            if ok:
                outputs.append(output)
            messages.append(ToolMessage(content=text, tool_call_id=call['id']))
        if finished:
            break
    log.add('episode_end', ending=ending, requests=sum(1 for e in log.events if e['kind'] == 'model_request'))
    return {'ending': ending, 'requests': len(log.of('model_request')), 'answer_raw': raw, 'answer_accepted': accepted,
            'namefix_events': namefix_events, 'tool_calls': [(e['name'], e['ok']) for e in log.of('tool_call')]}
