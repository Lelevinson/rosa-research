"""Live arms for the thinking-escalation study (protocol: PROTOCOL.md, hash in PROTOCOL.sha256). Read the protocol first.

FULL     = pilot arm C1 unchanged (reasoning=False in the chat-model constructor, no per-request override).
ESCALATE = FULL, but the 2 requests after a trigger (error, not-found, empty result, identical repeat) are sent with thinking on.
ESCALATE_CAPPED = ESCALATE, but at most CAP (6) requests per episode are sent with thinking on; after that thinking stays off for the rest of the episode (amendment A2).
ALWAYS   = FULL, but every request is sent with thinking on.
Trigger detection and logging (`call_class`, `think_request` events) run identically in all arms; only ESCALATE acts on them.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDIES = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDIES / "small_model_harness_20261115"))
sys.path.insert(0, str(STUDIES / "residual_failures_20261115"))
import harness  # noqa: E402
import run_pilot  # noqa: E402
import run_stage1 as S1  # noqa: E402

ARMS_ORIGINAL = ["FULL", "ESCALATE", "ALWAYS"]  # the arms of the original protocol and of parts A / B
ARMS = ARMS_ORIGINAL + ["ESCALATE_CAPPED"]  # amendment A2 adds a capped arm
CAP = 6  # ESCALATE_CAPPED: at most this many requests per episode are sent with thinking on (amendment A2)
MENU_TOOLS = set(harness.DOMAIN_TOOLS)
WINDOW = 2  # requests that follow a trigger
# Same expression as offline_replay_20261116/episodes.py NOT_FOUND (a unit test checks they are equal).
NOT_FOUND = re.compile(r"not found|Unable to find|does not exist|no such", re.I)
HTTP_TIMEOUT_SECONDS = 240  # protocol section 3: earlier runs used 90 s, which a long thinking response can exceed
CURRENT_MODEL = {"name": None}  # set by the runner's episode() before the arm is built


def thinking_on_value(model_name):
    """True for models with an on/off switch; gpt-oss only has levels (it cannot be turned off), so 'high'."""
    return "high" if str(model_name).startswith("gpt-oss") else True


def canonical(value):
    return json.dumps(value, sort_keys=True, default=str)


def error_entries(output):
    """Messages of `error` entries: a top-level `error` or an `error` inside a per-item dict (list tools return one entry per item)."""
    found = []
    if isinstance(output, dict):
        if "error" in output:
            found.append(output["error"])
        for value in output.values():
            if isinstance(value, dict) and "error" in value:
                found.append(value["error"])
    return found


def is_empty_container(output):
    """[] / {} / '' and a dict whose values are all empty containers or empty text (list tools return {"nodes": []} when nothing matches; protocol R1)."""
    if isinstance(output, (str, list)):
        return not output
    if isinstance(output, dict):
        return not output or all(v is None or (isinstance(v, (str, list, dict)) and is_empty_container(v)) for v in output.values())
    return False


def classify_result(output):
    """'not_found', 'empty' or 'ok' for a call that returned (protocol section 2, classes 2 and 3). Errors (raised calls) and repeats are decided by the caller."""
    text = output if isinstance(output, str) else canonical(output)
    entries = error_entries(output)
    if NOT_FOUND.search(text) or any(str(e).strip() for e in entries):
        return "not_found"
    if entries or output is None or is_empty_container(output) or (isinstance(output, str) and output.strip() in ("", "null", "None", "[]", "{}")):
        return "empty"
    return "ok"


class ThinkArm(harness.Arm):
    def __init__(self, variant, recorder, context, prompt_messages):
        assert variant in ARMS, variant
        super().__init__("C1", recorder, context, prompt_messages)  # exactly the base arm
        self.name, self.variant = variant, variant
        self.level_on = thinking_on_value(CURRENT_MODEL["name"])
        self.remaining = 0  # escalated requests still to send
        self.current_level = None
        self.successful_calls = set()
        self.fire_requests = set()
        self.fires = 0
        self.escalated_sent = 0   # requests sent with thinking on so far (only used by ESCALATE_CAPPED)
        self.cap_reached = False

    # ---- per-request thinking setting (called by ThinkTracedModel right after visible_schemas)
    def visible_schemas(self, schemas, messages):
        chosen = super().visible_schemas(schemas, messages)  # increments request_count
        before = self.remaining
        if self.variant == "ALWAYS":
            self.current_level = self.level_on
        elif self.variant in ("ESCALATE", "ESCALATE_CAPPED") and self.remaining > 0:
            if self.variant == "ESCALATE_CAPPED" and self.escalated_sent >= CAP:
                self.current_level, self.remaining = None, 0   # cap reached: thinking stays off for the rest of the episode
                if not self.cap_reached:
                    self.cap_reached = True
                    self.log("cap_reached", request=self.request_count, cap=CAP)
            else:
                self.current_level = self.level_on
                self.remaining -= 1
                self.escalated_sent += 1
        else:
            self.current_level = None
        self.log("think_request", request=self.request_count, level=self.current_level, remaining_before=before)
        return chosen

    def request_options(self):
        return {} if self.current_level is None else {"reasoning": self.current_level}

    # ---- trigger detection (all arms) ----
    def log(self, event, **values):
        super().log(event, **values)
        if event == "validation_error":  # strict pre-check rejection: raised before execute() is reached, so it is hooked here
            self._record(values.get("tool"), values.get("args"), "error")

    def _pydantic_text(self, error):  # pydantic validation text returned to the model, also before execute()
        self._record("unknown", None, "error")
        return super()._pydantic_text(error)

    def _record(self, tool, arguments, klass):
        self.log("call_class", request=self.request_count, tool=tool, args=arguments, klass=klass)
        if klass != "ok" and self.variant in ("ESCALATE", "ESCALATE_CAPPED") and not self.cap_reached:
            self.remaining = WINDOW
        if klass != "ok" and self.request_count not in self.fire_requests:
            self.fire_requests.add(self.request_count)
            self.fires += 1
            self.log("trigger_fire", request=self.request_count, klass=klass, window_set=self.variant in ("ESCALATE", "ESCALATE_CAPPED") and not self.cap_reached)

    def execute(self, tool, arguments):
        try:
            output = super().execute(tool, arguments)
        except Exception:
            self._record(tool.name, arguments, "error")
            raise
        klass = classify_result(output) if tool.name in MENU_TOOLS else "ok"
        if klass == "ok" and tool.name in MENU_TOOLS and not harness.failed_items(tool.name, arguments, output):
            key = (tool.name, canonical(arguments), canonical(output))
            if key in self.successful_calls:
                klass = "repeat"
            self.successful_calls.add(key)
        self._record(tool.name, arguments, klass)
        return output

    def execute_extra(self, name, arguments):
        try:
            return super().execute_extra(name, arguments)
        except Exception:
            self._record(name, arguments, "error")
            raise


class ThinkTracedModel(run_pilot.ArmTracedModel):
    """ArmTracedModel that also sets the per-request thinking option; the base class logs `options` in `model_start`."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        kwargs["tools"] = self.arm.visible_schemas(kwargs.get("tools", []), messages)
        self.options = self.arm.request_options()
        return S1.TracedModel._generate(self, messages, stop=stop, run_manager=run_manager, **kwargs)


def build_chat_model(model, temperature, seed):
    """run_pilot.build_chat_model with the longer HTTP timeout (everything else identical; reasoning=False is the base for every arm)."""
    from langchain_ollama import ChatOllama
    return ChatOllama(model=model, base_url=S1.OLLAMA, temperature=temperature, seed=seed, reasoning=False,
                      num_predict=run_pilot.NUM_PREDICT, num_ctx=run_pilot.NUM_CTX, client_kwargs={"timeout": HTTP_TIMEOUT_SECONDS})


def make_arm(variant, recorder, context):
    return ThinkArm(variant, recorder, context, run_pilot.prompt_for("A1"))
