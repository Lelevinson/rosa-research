"""Build round 2 arms on top of the fixed loop (round 1 arm C1, unchanged). Read sweep_logic.py (the trigger) and PROTOCOL.md sections 4-5 first.

  CONTROL  fixed loop + sweep SHADOW (same trigger, logs `sweep_shadow`, changes nothing) + answer rewrite SHADOW
  SWEEP    fixed loop + sweep LIVE   (runs T on the sweep names, appends the results to the triggering call's result) + answer rewrite SHADOW
Both arms are one class; the only difference is `self.sweep_live`. The answer gate and the bare-text nudge of round 1 stay OFF in both arms (the parent is built
as arm C1; its gate runs in shadow logging only, as in the round 1 control).

Where it plugs in (nothing in src/rosa, the pilot files or the round 1 files is edited):
  Round2Model._generate   registers the tool calls of every model response with the tracker (so 'names called in request k' are known before they run)
  Round2Arm.execute       after a read call returned: trigger check -> shadow log, or live sweep and result attachment
  Round2Arm.final_answer_tool   answer rewrite in shadow: logs the original and the rewritten answer; the submitted answer is never changed
"""
import json
from pathlib import Path
import sys

from langchain_core.tools import ToolException

HERE = Path(__file__).resolve().parent
ROUND1 = HERE.parent / "build_round1_20261115"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROUND1))
import answer_gate as ag  # noqa: E402
import round1_harness as r1  # noqa: E402  (also puts the pilot study on sys.path)
import sweep_logic  # noqa: E402

ARMS = ["CONTROL", "SWEEP"]
LINE_READ = "Also read with the same arguments, for other names from the same list (results keyed by full name): {names}."
LINE_NOT_READ = " Not read (limit reached): {names}."


def fixed_line(read_names, not_read_names):
    """The one fixed line of PROTOCOL.md section 4 (wording frozen before the first episode)."""
    line = LINE_READ.format(names=", ".join(read_names))
    if not_read_names:
        line += LINE_NOT_READ.format(names=", ".join(not_read_names))
    return line


def attach(output, line, also_read):
    """Original result + the fixed line + the keyed results. A dict result keeps its keys; a text result gets the line and the JSON appended."""
    if isinstance(output, dict):
        return {**output, "also_read_note": line, "also_read": also_read}
    text = output if isinstance(output, str) else json.dumps(output, default=str)
    return f"{text}\n{line}\n{json.dumps(also_read, default=str)}"


def result_size_tokens(result):
    """Real size of one swept result in tokens, estimated as characters / 4 (the unit the offline replay used)."""
    return len(json.dumps(result, default=str)) / 4


def unit_successful(tool, arguments, output):
    """Same judgement as the offline replay's parse(): the whole call counts as a successful result when it is no failure and no item reports an error."""
    import episodes as E
    text = output if isinstance(output, str) else json.dumps(output)
    harness_error = isinstance(output, str) and bool(E.HARNESS_TEXT.match(output))
    items = E.expand_call(tool, arguments, output, text, harness_error, 0)
    return (not E.is_failure(output, text, harness_error)
            and not any(not i["ok"] for i in items if i["entity"] is not None and isinstance(output, dict) and "error" in output)), text


class Round2Arm(r1.Round1Arm):
    def __init__(self, name, recorder, context, prompt_messages):
        assert name in ARMS, name
        super().__init__("C1", recorder, context, prompt_messages)  # exactly round 1's control: no gate, no nudge, no list arguments
        self.name = name
        self.sweep_live = name == "SWEEP"
        self.tracker = None  # built in wrap_tools, when the tool schemas (argument defaults) are known

    def wrap_tools(self, tools):
        defaults = {}
        for tool in tools:
            fields = getattr(tool.args_schema, "model_fields", {})
            defaults[tool.name] = {n: f.default for n, f in fields.items() if not f.is_required()}
        self.tracker = sweep_logic.SweepTracker(defaults)
        return super().wrap_tools(tools)

    # ---------------- sweep completion
    def execute(self, tool, arguments):
        request = self.request_count
        output = super().execute(tool, arguments)  # a failed call raises here: it gets no firing and no ledger entry
        successful, text = unit_successful(tool.name, arguments, output)
        firing = self.tracker.evaluate(request, tool.name, arguments)
        self.tracker.add_result(request, tool.name, output, text, successful)
        if firing is None:
            return output
        if not self.sweep_live:
            self.tracker.mark_covered(firing, firing["sweep"])
            self.log("sweep_shadow", request=request, tool=tool.name, group_source=firing["group_source"], group_size=firing["group_size"],
                     trigger_name=firing["trigger_name"], previous_name=firing["previous_name"], sweep=firing["sweep"], cut=firing["cut_by_name_limit"],
                     other_arguments=firing["key"])
            return output
        return self.run_sweep(tool, arguments, output, firing, request)

    def run_sweep(self, tool, arguments, output, firing, request):
        entity_key = firing["entity_key"]
        is_list_argument = isinstance(arguments[entity_key], list)
        read, results, raw_items, not_read, runs, characters = [], {}, [], [], 0, 0
        for position, name in enumerate(firing["sweep"]):
            single = dict(arguments)
            single[entity_key] = [name] if is_list_argument else name
            runs += 1
            try:
                raw = self.call_inner(tool, single)
            except ToolException as error:  # an item failure stays in its own entry
                raw = {"error": str(error)}
            result = raw[name] if is_list_argument and isinstance(raw, dict) and name in raw else raw
            if sum(result_size_tokens(results[n]) for n in read) + result_size_tokens(result) > sweep_logic.MAX_SWEEP_TOKENS:
                not_read = firing["sweep"][position:]  # this item and everything after it
                break
            read.append(name)
            results[name] = result
            raw_items.append(dict(name=name, args=single, output=raw))
            characters += len(json.dumps(result, default=str))
        cut = not_read + firing["cut_by_name_limit"]
        if not read:  # the first result alone passed the limit: nothing to append, so no firing
            self.log("sweep_empty_after_limit", request=request, tool=tool.name, sweep=firing["sweep"], extra_tool_runs=runs)
            return output
        line = fixed_line(read, cut)
        self.tracker.mark_covered(firing, read)
        for item in raw_items:  # sweep results count as successful results for the ledger and for the rewrite's name list
            ok, text = unit_successful(tool.name, item["args"], item["output"])
            self.tracker.add_result(request, tool.name, item["output"], text, ok)
            self.tool_outputs.append(item["output"])
        self.log("sweep_fire", request=request, tool=tool.name, group_source=firing["group_source"], group_size=firing["group_size"],
                 trigger_name=firing["trigger_name"], previous_name=firing["previous_name"], sweep=read, cut=cut, extra_tool_runs=runs,
                 extra_result_chars=characters, extra_result_tokens_est=round(characters / 4), line=line, other_arguments=firing["key"],
                 original_output=output, items=raw_items)
        return attach(output, line, results)

    # ---------------- answer rewrite (shadow)
    def final_answer_tool(self, arguments):
        answer = arguments.get("answer")
        if isinstance(answer, dict) and answer:
            allowed = ag.allowed_names(self.task_text, self.tool_outputs)
            events = []
            rewritten = rewrite(answer, allowed, events)
            rejects = [e for e in events if e["kind"].startswith("reject")]
            never_seen = [e for e in rejects if e["kind"] == "reject_never_seen"]
            queried = self.tracker.all_queried() if self.tracker else set()
            self.log("rewrite_shadow", answer=answer, rewritten=rewritten, changed=rewritten != answer,
                     rewrites=[e for e in events if e["kind"] == "rewrite"],
                     would_reject_ambiguous=[e for e in rejects if e["kind"] == "reject_ambiguous"], would_reject_never_seen=never_seen,
                     listed_but_unread=sorted(n for n in allowed if n not in queried) if never_seen else None)
        return super().final_answer_tool(arguments)  # the submitted answer is NOT changed


def rewrite(value, allowed, log, path="", top=True):
    """Copy of the offline replay's `rewrite` (replay.py, protocol 3): a name-like string that is not a ledger name but is the trailing part (whole final path
    segments) of exactly one ledger full name is replaced; 2+ candidates or a full name never seen are only logged. Top-level keys are left alone."""
    if isinstance(value, str):
        if ag.ABSOLUTE_NAME.fullmatch(value) or ag.RELATIVE_NAME.fullmatch(value):
            if value in allowed:
                return value
            matches = ag.trailing_matches(value, allowed)
            if len(matches) == 1:
                log.append(dict(kind="rewrite", path=path, old=value, new=matches[0]))
                return matches[0]
            if len(matches) >= 2:
                log.append(dict(kind="reject_ambiguous", path=path, value=value, candidates=matches))
            elif ag.ABSOLUTE_NAME.fullmatch(value):
                log.append(dict(kind="reject_never_seen", path=path, value=value))
        return value
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            new_key = k if top else rewrite(k, allowed, log, path + ".key", False)
            out[new_key] = rewrite(v, allowed, log, f"{path}.{k}" if path else k, False)
        return out
    if isinstance(value, list):
        return [rewrite(v, allowed, log, f"{path}[{i}]", False) for i, v in enumerate(value)]
    return value


class Round2Model(r1.Round1Model):
    """Round 1's traced model; after every response the arm learns which calls the model asked for (needed for 'names called in request k')."""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        result = super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        message = result.generations[0].message
        if self.arm.tracker is not None:
            self.arm.tracker.register_model_calls(self.arm.request_count, list(message.tool_calls or []))
        return result


def make_arm(name, recorder, context):
    return Round2Arm(name, recorder, context, r1.run_pilot.prompt_for("A1"))
