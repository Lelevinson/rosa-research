"""Runtime handlers around ROSA's tools for the small-model pilot (arms C1, M0, C1+FN, C1+H2, C1+H1e, C1+H1n, C1+H7).

Read this file top to bottom: every handler is a short, separate function and every decision it takes is written to the trace
as a `handler` event, so a decision can be followed from inputs to the action taken.

Where it plugs in (nothing in src/rosa is edited):
- run_pilot.PilotROSA._get_agent  -> Arm.wrap_tools   : every ROSA tool is replaced by a PilotTool that calls Arm.execute.
- run_pilot.ArmTracedModel        -> Arm.visible_schemas : the tool list offered to the model is decided per request.
- run_pilot.PilotROSA._get_executor -> Arm.make_executor : an accepted final_answer ends the episode without an extra request.

Arm definitions (see the build document, section 1):
  C1     strong control: tool errors returned to the model as text, strict JSON-schema argument check with a field-level message
         (no value repair), domain tool menu (write tools hidden AND blocked at execution), final_answer tool with one retry.
  M0     C1 + MetaTool `supertool` (returns its generated_instruction_sequence unchanged) + one prompt sentence.
  C1+FN  C1 + a `Full name: <ns>/<name>` line after every `Node name` / `Node namespace` pair in a tool output.
  C1+H2  C1 + unique-suffix name canonicalization (repair only when exactly one earlier-seen full name matches).
  C1+H1e C1 + event-aware reuse of identical ros2_param_get / ros2_param_list calls (needs /parameter_events).
  C1+H1n C1 + naive reuse of any identical earlier successful read call (harm probe, no freshness check).
  C1+H7  C1 + plan enforcement (submit_plan / replan; per-request tool lists from the plan).
"""
from dataclasses import dataclass, field
import json
import re
import subprocess
import threading
import time
from typing import Any, List

from langchain.agents import AgentExecutor
from langchain_core.agents import AgentFinish
from langchain_core.tools import StructuredTool, ToolException
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field

import pilot_score  # last_json_object only

ARMS = ["C1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H1n", "C1+H7"]

# Domain tool menu of C1: ROS 2 read tools + read_log. Everything else (calculation, system, ros2_param_set, ros2_service_call) is hidden.
DOMAIN_TOOLS = ["ros2_node_list", "ros2_topic_list", "ros2_topic_echo", "ros2_service_list", "ros2_node_info", "ros2_topic_info",
                "ros2_param_list", "ros2_param_get", "ros2_service_info", "ros2_doctor", "roslog_list", "read_log"]
WRITE_TOOLS = ["ros2_param_set", "ros2_service_call"]
READ_REUSE_TOOLS = DOMAIN_TOOLS  # H1n: any identical earlier successful read call
H1E_TOOLS = ["ros2_param_get", "ros2_param_list"]  # H1e: eligible calls only

FINAL_ANSWER_LINE = ("system", "When you have the answer, call the final_answer tool with the answer as a JSON object, using exactly the keys the task asks for. "
                               "Do not write the answer as plain text.")
M0_LINE = ("system", "Always use supertool() to think and generate a plan for the sequence of tool execution, then use that plan to execute the tools in proper order.")
# Revision 2026-11-15 (see PILOT_LOG): the first version did not tell the model which tool names exist, but at request 1 only submit_plan is offered, so a plan
# could only be valid by luck. The registry names are now listed in the prompt line and in the submit_plan description.
H7_LINE = ("system", "Before any other tool, call submit_plan with the steps you intend to take: each step lists the tool names it uses and whether it is repeated for each "
                     "item found earlier (for_each). The tools you can plan with are: " + ", ".join(DOMAIN_TOOLS) + ". "
                     "Later you only see the tools of the current and the next step; call replan if the plan was wrong.")

# argument that names a ROS entity, per tool: (argument name, is_list)
ENTITY_ARGS = {"ros2_param_get": ("node_name", False), "ros2_param_list": ("node_name", False), "ros2_node_info": ("nodes", True),
               "ros2_topic_info": ("topics", True), "ros2_service_info": ("services", True), "ros2_topic_echo": ("topic", False)}
NOT_FOUND = re.compile(r"not found|Unable to find|does not exist|no such", re.I)
FULL_NAME = re.compile(r"(?<![\w/.:-])/(?:[A-Za-z0-9_]+/)*[A-Za-z0-9_]+")


# ------------------------------------------------------------------ strict JSON-schema check (C1): no value repair
def type_name(value):
    return {dict: "object", list: "array", str: "string", bool: "boolean", int: "integer", float: "number", type(None): "null"}.get(type(value), type(value).__name__)


def matches_type(value, expected):
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return {"string": str, "boolean": bool, "array": list, "object": dict, "null": type(None)}[expected] is type(value) or (expected == "array" and isinstance(value, list))


def schema_problems(value, schema, path):
    """List of (field, expected, received) problems of value against a (dereferenced) JSON schema."""
    if "anyOf" in schema:
        if any(not schema_problems(value, alt, path) for alt in schema["anyOf"]):
            return []
        expected = " or ".join(alt.get("type", "any") for alt in schema["anyOf"])
        return [(path, expected, value)]
    expected = schema.get("type")
    if expected is None:
        return []
    if not matches_type(value, expected):
        return [(path, expected, value)]
    if "enum" in schema and value not in schema["enum"]:
        return [(path, "one of " + json.dumps(schema["enum"]), value)]
    problems = []
    if expected == "array" and "items" in schema:
        for index, item in enumerate(value):
            problems += schema_problems(item, schema["items"], f"{path}[{index}]")
    if expected == "object" and "properties" in schema:
        for key in schema.get("required", []):
            if key not in value:
                problems.append((f"{path}.{key}", "required field", "missing"))
        for key, child in schema["properties"].items():
            if key in value:
                problems += schema_problems(value[key], child, f"{path}.{key}")
    return problems


def strict_error(tool_name, schema, arguments):
    """The text returned to the model for invalid arguments, or None. Names the field, the expected type and the received value."""
    problems = schema_problems(arguments, schema, "")
    if not problems:
        return None
    parts = []
    for path, expected, received in problems:
        text = received if received == "missing" else f"{type_name(received)} {json.dumps(received)[:80]}"
        parts.append(f"field '{path.lstrip('.')}': expected {expected}, received {text}")
    return f"Invalid arguments for {tool_name}: " + "; ".join(parts) + ". Fix the arguments and call the tool again."


# ------------------------------------------------------------------ extra tools
class FinalAnswerArgs(BaseModel):
    answer: dict = Field(description="The final answer as a JSON object with the keys the task asks for.")


class SupertoolArgs(BaseModel):
    input_str: str = Field(description="The task or sub-task to plan for.")
    generated_instruction_sequence: str = Field(description="The generated plan: the ordered sequence of tool executions.")


class PlanStep(BaseModel):
    tools: List[str] = Field(description="Tool names used in this step.")
    for_each: bool = Field(description="True if the step is repeated for every item found earlier.")


class PlanArgs(BaseModel):
    steps: List[PlanStep] = Field(description="Ordered steps of the plan.")


EXTRA_TOOLS = {
    "final_answer": ("Submit the final answer as a JSON object. This ends the task.", FinalAnswerArgs),
    "supertool": ("Think and generate a plan for the sequence of tool execution. Returns the plan unchanged.", SupertoolArgs),
    "submit_plan": ("Submit the plan: ordered steps, each with the tool names it uses and a for_each flag. Valid tool names: " + ", ".join(DOMAIN_TOOLS) + ".", PlanArgs),
    "replan": ("Replace the current plan with a new one (same format as submit_plan).", PlanArgs),
}


class PilotTool(StructuredTool):
    """A ROSA tool whose arguments are checked strictly before pydantic can coerce them, and whose errors become observations."""
    arm: Any = None

    def _parse_input(self, tool_input, tool_call_id=None):
        if isinstance(tool_input, dict) and self.arm is not None:
            message = strict_error(self.name, self.arm.schema_of(self.name), tool_input)
            if message:
                self.arm.log("validation_error", tool=self.name, args=tool_input, message=message)
                if self.name in ("submit_plan", "replan") and self.arm.h7 and not self.arm.plan_fallback:
                    message = self.arm.register_invalid_plan(self.name, "arguments do not match the plan format: " + message.split(": ", 1)[1])
                raise ToolException(message)
        return super()._parse_input(tool_input, tool_call_id)


class PilotExecutor(AgentExecutor):
    """AgentExecutor that ends the episode as soon as final_answer was accepted (no extra model request)."""
    arm: Any = None

    def _get_tool_return(self, next_step_output):
        action, _ = next_step_output
        if action.tool == "final_answer" and self.arm.final_done:
            return AgentFinish({"output": json.dumps(self.arm.final_answer)}, "")
        return super()._get_tool_return(next_step_output)


# ------------------------------------------------------------------ parameter-event monitor (H1e)
class ParameterEventMonitor:
    """Follows /parameter_events with `ros2 topic echo` from episode start. events: list of (monotonic arrival time, node name)."""
    def __init__(self, log):
        self.log, self.events, self.process, self.started = log, [], None, None

    def start(self):
        self.started = time.perf_counter()
        self.process = subprocess.Popen(["ros2", "topic", "echo", "/parameter_events"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()
        time.sleep(3.0)  # discovery time; counted as monitoring overhead
        self.log("monitor_started", process=self.process.pid, startup_seconds=time.perf_counter() - self.started)

    def _read(self):
        for line in self.process.stdout:
            match = re.match(r"node:\s*(\S+)", line)
            if match:
                self.events.append((time.perf_counter(), match.group(1)))

    def changed_since(self, node_name, since):
        """Parameter events for node_name (or any node when node_name is None) that arrived after time `since`."""
        time.sleep(0.25)  # let an event published just before this call arrive
        wanted = None if node_name is None else "/" + node_name.lstrip("/")
        return [e for e in self.events if e[0] > since and (wanted is None or e[1] == wanted)]

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.log("monitor_stopped", events_seen=len(self.events), seconds=time.perf_counter() - self.started if self.started else 0)


# ------------------------------------------------------------------ episode state
@dataclass
class Step:
    number: int
    name: str
    args: dict
    given_args: dict
    ok: bool
    output: Any
    finished: float
    from_cache: bool = False


@dataclass
class Plan:
    steps: list
    index: int = 0


# Tool names of each Stage 3 task's verified minimal route (checked against the floor-check logs in the unit tests).
ROUTE_BY_ID = {"u2": ["ros2_topic_info", "ros2_param_get"], "u3": ["ros2_topic_info", "ros2_node_info"], "u4": ["ros2_topic_info", "ros2_node_info", "ros2_param_get"],
               "p2": ["ros2_param_get"], "p3": ["ros2_param_get"], "p4": ["ros2_param_get"], "h2": ["ros2_topic_info", "ros2_node_info"],
               "h3": ["ros2_topic_info", "ros2_node_info"], "h4": ["ros2_topic_info", "ros2_node_info", "ros2_param_get"], "v2": ["ros2_node_list", "ros2_node_info"],
               "v3": ["ros2_node_list", "ros2_node_info", "ros2_param_get"], "v4": ["ros2_node_list", "ros2_node_info", "ros2_param_get"]}


def route_tools(task):
    """Tool names of the verified minimal route (used only to log whether a submitted plan is complete)."""
    return set(task.get("route_tools") or ROUTE_BY_ID.get(task["id"], []))


class Arm:
    def __init__(self, name, recorder, context, prompt_messages):
        assert name in ARMS, name
        self.name, self.recorder, self.context = name, recorder, context
        flags = name.split("+")
        self.fn, self.h2, self.h1e, self.h1n, self.h7 = ("FN" in flags[1:], "H2" in flags[1:], "H1e" in flags[1:], "H1n" in flags[1:], "H7" in flags[1:])
        self.m0 = name == "M0"
        self.prompt_messages = prompt_messages + [FINAL_ANSWER_LINE] + ([M0_LINE] if self.m0 else []) + ([H7_LINE] if self.h7 else [])
        self.steps: List[Step] = []
        self.seen_names = set()
        self.request_count = 0
        self.final_done, self.final_answer, self.final_invalid = False, None, 0
        self.schemas = {}
        self.offered = set()
        self.monitor = None
        self.plan, self.plan_invalid, self.replans, self.plan_fallback = None, 0, 0, False
        self.supertool_calls = 0
        self.tools_called_before_supertool = 0
        if self.h1e:
            self.monitor = ParameterEventMonitor(self.log)
            self.monitor.start()

    # -------- logging
    def log(self, event, **values):
        self.recorder.add("handler", handler=self.name, event=event, **values)

    def close(self):
        if self.monitor:
            self.monitor.stop()

    def schema_of(self, tool_name):
        return self.schemas[tool_name]

    # -------- tools offered
    def base_menu(self):
        names = list(DOMAIN_TOOLS) + ["final_answer"] + (["supertool"] if self.m0 else [])
        return names

    def offered_names(self):
        if self.h7 and not self.plan_fallback:
            return self.h7_offered()
        return self.base_menu()

    def h7_offered(self):
        """H7: planning request -> only submit_plan; afterwards tools of the current and the next step + replan + final_answer."""
        if self.plan is None:
            return ["submit_plan"]
        current = self.plan.steps[self.plan.index]["tools"]
        following = self.plan.steps[self.plan.index + 1]["tools"] if self.plan.index + 1 < len(self.plan.steps) else []
        names = []
        for name in current + following + ["replan", "final_answer"]:
            if name not in names:
                names.append(name)
        return names

    def visible_schemas(self, schemas, messages):
        """Per-request tool binding: the model only sees the offered tools (this is the list that reaches Ollama)."""
        self.request_count += 1
        names = self.offered_names()
        self.offered = set(names)
        chosen = [s for s in schemas if s["function"]["name"] in self.offered]
        self.log("tools_offered", request=self.request_count, names=[s["function"]["name"] for s in chosen])
        return chosen

    def wrap_tools(self, tools):
        wrapped = []
        for tool in tools:
            schema = convert_to_openai_tool(tool)["function"]["parameters"]
            self.schemas[tool.name] = schema
            wrapped.append(PilotTool(name=tool.name, description=tool.description, args_schema=tool.args_schema, arm=self,
                                     func=self._bind(tool), handle_tool_error=True, handle_validation_error=self._pydantic_text))
        for name, (description, model) in EXTRA_TOOLS.items():
            self.schemas[name] = convert_to_openai_tool(StructuredTool(name=name, description=description, args_schema=model, func=lambda **kw: None))["function"]["parameters"]
            wrapped.append(PilotTool(name=name, description=description, args_schema=model, arm=self,
                                     func=self._bind_extra(name), handle_tool_error=True, handle_validation_error=self._pydantic_text))
        return wrapped

    def _pydantic_text(self, error):
        return "Invalid arguments: " + "; ".join(f"field '{'.'.join(map(str, e['loc']))}': {e['msg']}" for e in error.errors())

    def _bind(self, tool):
        def run(**arguments):
            return self.execute(tool, arguments)
        return run

    def _bind_extra(self, name):
        def run(**arguments):
            return self.execute_extra(name, arguments)
        return run

    def make_executor(self, agent, tools, max_iterations):
        return PilotExecutor(agent=agent, tools=tools, verbose=False, max_iterations=max_iterations, handle_parsing_errors=True, arm=self)

    # -------- execution of one tool call
    def execute(self, tool, arguments):
        name = tool.name
        if name in WRITE_TOOLS:
            self.log("blocked_write_tool", tool=name, args=arguments)
            raise ToolException(f"Tool {name} is not available in this session.")
        if name not in self.offered:
            self.log("tool_not_offered", tool=name, offered=sorted(self.offered))
            if self.h7 and not self.plan_fallback and self.plan is None:  # a tool call instead of the required plan counts as an invalid plan
                raise ToolException(self.register_invalid_plan(name, "no plan submitted; call submit_plan first"))
            raise ToolException(f"Tool {name} is not available at this step. Available tools: {', '.join(sorted(self.offered))}.")
        if self.supertool_calls == 0 and self.m0:
            self.tools_called_before_supertool += 1
        given = dict(arguments)
        reused = self.try_reuse(name, arguments)
        if reused is not None:
            return reused
        output = self.call_inner(tool, arguments)
        effective = dict(arguments)
        note = None
        if self.h2:
            output, effective, note = self.h2_repair(tool, arguments, output)
        self.record_step(name, effective, given, output)
        if effective != given:
            self.recorder.add("effective_call", args=effective, given=given)
        if self.fn:
            output = self.add_full_names(output)
        if note:
            output = prepend_note(output, note)
        self.advance_plan(name)
        return output

    def call_inner(self, tool, arguments):
        try:
            return tool.func(**arguments)
        except Exception as error:  # a tool exception becomes an observation instead of ending the episode
            self.log("tool_exception", tool=tool.name, error=f"{type(error).__name__}: {error}")
            raise ToolException(f"Tool {tool.name} failed: {type(error).__name__}: {error}")

    def record_step(self, name, effective, given, output):
        text = json.dumps(output) if not isinstance(output, str) else output
        failed = (isinstance(output, dict) and "error" in output) or bool(failed_items(name, effective, output))
        self.steps.append(Step(len(self.steps) + 1, name, effective, given, not failed, output, time.perf_counter()))
        if not failed:
            self.seen_names.update(FULL_NAME.findall(text.replace("\\n", "\n")))
            if isinstance(output, dict) and name == "ros2_node_list":
                self.seen_names.update(n for n in output.get("nodes", []) if isinstance(n, str))
            self.seen_names.update(assembled_names(text))

    # -------- H1: reuse of identical read calls
    def try_reuse(self, name, arguments):
        if not (self.h1e or self.h1n):
            return None
        if self.h1e and name not in H1E_TOOLS or self.h1n and name not in READ_REUSE_TOOLS:
            return None
        earlier = [s for s in self.steps if s.name == name and s.args == arguments and s.ok and not s.from_cache]
        if not earlier:
            return None
        previous = earlier[-1]
        if self.h1n:
            self.log("reuse", reuse_kind="naive", tool=name, args=arguments, from_step=previous.number)
            self.steps.append(Step(len(self.steps) + 1, name, arguments, arguments, True, previous.output, time.perf_counter(), from_cache=True))
            return prepend_note(previous.output, f"Repeated call: returning the result of step {previous.number}.")
        node = arguments.get("node_name")
        changed = self.monitor.changed_since(node, previous.finished)
        if changed:
            self.log("reuse_blocked", tool=name, args=arguments, from_step=previous.number, events=[e[1] for e in changed])
            return None
        self.log("reuse", reuse_kind="event_aware", tool=name, args=arguments, from_step=previous.number, events_seen=len(self.monitor.events))
        self.steps.append(Step(len(self.steps) + 1, name, arguments, arguments, True, previous.output, time.perf_counter(), from_cache=True))
        return prepend_note(previous.output, f"Unchanged since step {previous.number} (no parameter event).")

    # -------- H2: unique-suffix name canonicalization
    def h2_repair(self, tool, arguments, output):
        spec = ENTITY_ARGS.get(tool.name)
        if spec is None:
            return output, arguments, None
        arg_name, is_list = spec
        given_items = arguments.get(arg_name)
        if given_items is None:
            return output, arguments, None
        items = list(given_items) if is_list else [given_items]
        failed = failed_items(tool.name, arguments, output) if is_list else ([items[0]] if (isinstance(output, dict) and "error" in output) else [])
        replacements, notes = {}, []
        for given in failed:
            if not isinstance(given, str):
                continue
            error_text = json.dumps(output)
            if not (NOT_FOUND.search(error_text) or not given.startswith("/")):
                continue  # failed for another reason (not a naming problem)
            candidates = sorted(self.candidates_for(given))
            if len(candidates) == 1:
                replacements[given] = candidates[0]
                notes.append(f"Note: '{given}' resolved to '{candidates[0]}'")
                self.log("h2_repair", tool=tool.name, given=given, resolved=candidates[0], rule="exactly one earlier-seen full name ends with the given name")
            else:
                self.log("h2_no_repair", tool=tool.name, given=given, candidates=candidates)
                if candidates:
                    notes.append(f"Several full names end with '{given}': {', '.join(candidates)}. Use one of them.")
        if not replacements:
            return append_hint(output, notes), arguments, None
        new_items = [replacements.get(i, i) for i in items]
        new_arguments = dict(arguments)
        new_arguments[arg_name] = new_items if is_list else new_items[0]
        rerun = self.call_inner(tool, new_arguments)
        return rerun, new_arguments, "; ".join(n for n in notes if n.startswith("Note:"))

    def candidates_for(self, given):
        suffix = given if given.startswith("/") else "/" + given
        return {n for n in self.seen_names if n != given and n.endswith(suffix)}

    # -------- FN: full-name lines
    def add_full_names(self, output):
        def transform(text):
            return re.sub(r"(Node name:\s*(\S+)\s*\nNode namespace:\s*(\S+)[^\n]*\n)", lambda m: f"{m.group(1)}Full name: {m.group(3).rstrip('/')}/{m.group(2)}\n", text)
        if isinstance(output, str):
            return transform(output)
        if isinstance(output, dict):
            return {k: (transform(v) if isinstance(v, str) else v) for k, v in output.items()}
        return output

    # -------- extra tools
    def execute_extra(self, name, arguments):
        if name not in self.offered:
            self.log("tool_not_offered", tool=name, offered=sorted(self.offered))
            raise ToolException(f"Tool {name} is not available at this step. Available tools: {', '.join(sorted(self.offered))}.")
        if name == "final_answer":
            return self.final_answer_tool(arguments)
        if name == "supertool":
            if self.supertool_calls == 0:
                self.log("supertool_first_call", tools_called_before=self.tools_called_before_supertool)
            self.supertool_calls += 1
            return arguments["generated_instruction_sequence"]
        return self.plan_tool(name, arguments)

    def final_answer_tool(self, arguments):
        answer = arguments.get("answer")
        if isinstance(answer, dict) and answer:
            self.final_done, self.final_answer = True, answer
            self.recorder.add("final_answer_accepted", answer=answer, retried=self.final_invalid)
            return "Answer recorded."
        self.final_invalid += 1
        if self.final_invalid >= 2:  # one retry only: the second submission is accepted as it is and scored as it is
            parsed = pilot_score.last_json_object(answer) if isinstance(answer, str) else None
            self.final_done, self.final_answer = True, parsed if parsed is not None else {}
            self.recorder.add("final_answer_accepted", answer=self.final_answer, retried=self.final_invalid, invalid=True)
            return "Answer recorded."
        self.log("final_answer_invalid", args=arguments)
        raise ToolException("final_answer needs a non-empty JSON object in the field 'answer'. Submit it again once.")

    # -------- H7: plan enforcement
    def validate_plan(self, steps):
        """One compact error string, or None. Tool names must belong to the C1 domain menu (the registry the model may use)."""
        if not steps:
            return "plan has no steps"
        allowed = set(DOMAIN_TOOLS)
        for number, step in enumerate(steps, 1):
            if not step["tools"]:
                return f"step {number} lists no tools"
            unknown = [t for t in step["tools"] if t not in allowed]
            if unknown:
                return f"step {number} uses unknown tools {unknown}"
        return None

    def register_invalid_plan(self, tool, problem):
        """Count an invalid plan; the first gets one compact error, the second switches plan enforcement off (fall back to C1)."""
        self.plan_invalid += 1
        self.log("plan_invalid", tool=tool, problem=problem, count=self.plan_invalid)
        if self.plan_invalid >= 2:
            self.plan_fallback = True
            self.log("plan_fallback", reason="second invalid plan")
            return f"Invalid plan ({problem}). Plan enforcement is switched off; use the available tools freely."
        return f"Invalid plan: {problem}. Submit a corrected plan."

    def plan_tool(self, name, arguments):
        steps = [dict(tools=list(s["tools"]), for_each=bool(s["for_each"])) if isinstance(s, dict) else dict(tools=list(s.tools), for_each=s.for_each) for s in arguments["steps"]]
        if name == "replan":
            self.replans += 1
            if self.replans > 2:
                self.plan_fallback = True
                self.log("plan_fallback", reason="more than 2 replans")
                return "Plan enforcement is switched off; use the available tools freely."
        problem = self.validate_plan(steps)
        if problem:
            message = self.register_invalid_plan(name, problem)
            if self.plan_fallback:
                return message
            raise ToolException(message)
        used = {t for s in steps for t in s["tools"]}
        floor_tools = route_tools(self.context["task"])
        self.plan = Plan(steps=steps)
        self.log("plan_accepted", tool=name, steps=steps, complete_vs_floor_route=floor_tools <= used if floor_tools else None, missing_tools=sorted(floor_tools - used))
        return f"Plan accepted with {len(steps)} steps."

    def advance_plan(self, tool_name):
        if not self.h7 or self.plan_fallback or self.plan is None:
            return
        step = self.plan.steps[self.plan.index]
        following = self.plan.steps[self.plan.index + 1]["tools"] if self.plan.index + 1 < len(self.plan.steps) else []
        if tool_name not in step["tools"] and tool_name in following:
            self.plan.index += 1
            self.log("plan_advance", to_step=self.plan.index + 1, tool=tool_name)


# ------------------------------------------------------------------ helpers shared by handlers
def failed_items(name, arguments, output):
    """Entity arguments whose individual result is an error (list tools return one entry per item)."""
    spec = ENTITY_ARGS.get(name)
    if spec is None or not isinstance(output, dict):
        return []
    arg_name, is_list = spec
    given = arguments.get(arg_name)
    if is_list:
        return [item for item in (given or []) if isinstance(output.get(item), dict) and "error" in output[item]]
    return [given] if "error" in output and given else []


def assembled_names(text):
    text = text.replace("\\n", "\n")
    return {f"{ns.rstrip('/')}/{name}" for name, ns in re.findall(r"Node name:\s*(\S+)\s+Node namespace:\s*(\S+)", text)}


def prepend_note(output, note):
    if isinstance(output, dict):
        return {"note": note, **output}
    return f"{note}\n{output}"


def append_hint(output, notes):
    notes = [n for n in notes if not n.startswith("Note:")]
    if not notes:
        return output
    if isinstance(output, dict):
        return {**output, "hint": " ".join(notes)}
    return f"{output}\n{' '.join(notes)}"


def make_arm(name, recorder, context, base_prompt):
    return Arm(name, recorder, context, base_prompt)
