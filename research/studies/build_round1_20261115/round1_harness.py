"""Build round 1 arms on top of the fixed loop (harness.Arm = arm C1 of the pilot, unchanged). Read answer_gate.py and list_args.py first.

Arm names (the report uses plain names):
  C1        fixed loop (fresh control)                         flags: none
  C1+AG     fixed loop + answer gate                           flags: answer gate
  C1+LA     fixed loop + list arguments                        flags: list arguments
  C1+AG+LA  fixed loop + both
Every arm runs through THIS class, so the control differs from the add-on arms only by the flags. In arms without the answer gate the gate is run
in SHADOW mode: the same checks are computed and logged ('gate_shadow') but never change anything, so the control also shows how often the
gate would have fired.

Where it plugs in (nothing in src/rosa and nothing in the pilot study files is edited):
  Round1Arm.wrap_tools       list arguments: schema and description of the selected tools are replaced before the pilot wrapping.
  Round1Arm.call_inner       list arguments: one original tool call per item, one combined labeled result.
  Round1Arm.final_answer_tool  answer gate: name check, key check (reject with a hint, at most 2 per episode), numbers log only.
  Round1Model._generate      answer gate, bare-text finish: one corrective message, at most 2 per episode (adopted from Forge's bare-text nudge).
"""
from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool, ToolException

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "small_model_harness_20261115"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PILOT))
import answer_gate  # noqa: E402
import harness  # noqa: E402
import list_args  # noqa: E402
import run_pilot  # noqa: E402

ARMS = ["C1", "C1+AG", "C1+LA", "C1+AG+LA"]
MAX_NUDGES = 2
MAX_REJECTIONS = 2
NUDGE_TEXT = "You did not call a tool. When you have the answer, call the final_answer tool with the answer as a JSON object. Otherwise call the tool you need next."


class Round1Arm(harness.Arm):
    def __init__(self, name, recorder, context, prompt_messages):
        assert name in ARMS, name
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the pilot's fixed loop ...
        self.name = name  # ... logged under this arm's name
        flags = name.split("+")[1:]
        self.gate_on, self.lists_on = "AG" in flags, "LA" in flags
        self.task_text = context["task"]["request"]
        self.tool_outputs = []  # genuine tool results of this episode, for the name check
        self.rejections = self.nudges = 0
        self.last_rejected = None
        self.list_tools = {}  # tool name -> list argument, filled in wrap_tools

    # ---------------- list arguments
    def wrap_tools(self, tools):
        if self.lists_on:
            self.list_tools = list_args.applicable_tools(tools, harness.DOMAIN_TOOLS)
            replaced = []
            for tool in tools:
                if tool.name in self.list_tools:
                    schema, description = list_args.with_list_schema(tool, self.list_tools[tool.name])
                    tool = StructuredTool(name=tool.name, description=description, args_schema=schema, func=tool.func)
                replaced.append(tool)
            tools = replaced
            self.log("list_tools", tools=self.list_tools)
        return super().wrap_tools(tools)

    def call_inner(self, tool, arguments):
        argument = self.list_tools.get(tool.name)
        if argument and isinstance(arguments.get(argument), list):
            problem = list_args.list_problem(arguments[argument])
            if problem:
                self.log("list_rejected", tool=tool.name, count=len(arguments[argument]), message=problem)
                raise ToolException(problem)
            combined, items = list_args.run_per_item(lambda single: harness.Arm.call_inner(self, tool, single), arguments, argument)
            for item in items:  # per-item records let the unchanged scorer read each item as an ordinary single call
                self.log("list_item", tool=tool.name, args={**arguments, argument: item}, output=combined[item])
            self.log("list_call", tool=tool.name, items=len(items), given=len(arguments[argument]))
            return combined
        return super().call_inner(tool, arguments)

    def execute(self, tool, arguments):
        output = super().execute(tool, arguments)
        self.tool_outputs.append(output)
        return output

    # ---------------- answer gate
    def final_answer_tool(self, arguments):
        answer = arguments.get("answer")
        if isinstance(answer, dict) and answer:
            if self.last_rejected is not None:
                self.log("gate_followup", changed=answer != self.last_rejected, previous=self.last_rejected, now=answer)
                self.last_rejected = None
            verdict = answer_gate.check_answer(answer, self.task_text, self.tool_outputs)
            record = dict(answer=answer, problems=verdict["problems"], numbers_unseen=verdict["numbers_unseen"], rejections_so_far=self.rejections)
            if not self.gate_on:
                self.log("gate_shadow", would_reject=verdict["reject"], **record)
            elif verdict["reject"] and self.rejections < MAX_REJECTIONS:
                self.rejections += 1
                self.last_rejected = answer
                self.log("gate_reject", hint=verdict["hint"], **record)
                raise ToolException(verdict["hint"])
            else:
                self.log("gate_pass" if not verdict["reject"] else "gate_accepted_after_limit", **record)
        return super().final_answer_tool(arguments)

    def wants_nudge(self, message):
        return self.gate_on and self.nudges < MAX_NUDGES and not message.tool_calls and not getattr(message, "invalid_tool_calls", None)


class Round1Model(run_pilot.ArmTracedModel):
    """The pilot's traced model; in arms with the answer gate a response without a tool call gets one corrective message (at most 2 per episode)."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        message = result.generations[0].message
        if self.arm.wants_nudge(message):
            self.arm.nudges += 1
            self.arm.log("bare_text_nudge", number=self.arm.nudges, text=message.content)
            retry = list(messages) + [AIMessage(content=message.content or ""), HumanMessage(content=NUDGE_TEXT)]
            return self._generate(retry, stop=stop, run_manager=run_manager, **kwargs)
        return result


def make_arm(name, recorder, context):
    return Round1Arm(name, recorder, context, run_pilot.prompt_for("A1"))
