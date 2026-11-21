"""ADAPTATION FILE (ours): maps Levinson's method-M components onto Martin's UR5e setup. His files are used BYTE FOR BYTE from `origin/member/levinson` at e233cf5,
extracted by `extract_his_files.sh` (git archive, no eol conversion) and verified against the SHA-256 table in M_FILES.md before anything is imported. None of his files is edited.

Credit: "method M components (Levinson)": his harness.py (12-tool menu, strict pre-check, errors as text, final_answer), exam_arms.py (M = FULL + name fix), run_pilot.py (A1 prompt),
namefix_rule.py + answer_gate.py (name fix), menu_run_study.py (Recorder). Ours: `run_skill` (Martin's bounded macro), the two macro rule lines, this mapping, the fake model for dry runs.

LABEL: "merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated". It is NOT method M and is not scored as M.
SETTINGS: his M runs with NUM_CTX 65536, NUM_PREDICT 4096, MAX_ITERATIONS 40 (run_pilot.py); Martin's G1/M4 runs used num_ctx 8192. Any merged run must state which it uses."""
import hashlib
import os
import sys
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool

HERE = Path(__file__).resolve().parent.parent                      # research/demo_merged_20261122
COMMIT = 'e233cf51389885d0aaffa5453687f57437551764'
HIS_ROOT = Path(os.environ.get('HIS_ROOT', str(HERE.parent.parent.parent / 'his-M-e233cf5')))
STUDIES = HIS_ROOT / 'research' / 'studies'

MACRO_RULE_LINES = None   # filled from merged_demo.prompts (verbatim M4 sentences; submit_report sentences dropped)


class HisFilesMissing(RuntimeError):
    pass


def verify():
    """Byte-for-byte check of every row of M_FILES.md on disk. Raises on any mismatch. Returns the list of verified rows."""
    sys.path.insert(0, str(HERE))
    import verify_his_files
    if not (STUDIES / 'exam_arms_20261121' / 'exam_arms.py').is_file():
        raise HisFilesMissing('his files not found at %s: run extract_his_files.sh first' % HIS_ROOT)
    rows = verify_his_files.table()
    bad = [path for path, expected, _ in rows
           if not (HIS_ROOT / path).is_file() or hashlib.sha256((HIS_ROOT / path).read_bytes()).hexdigest() != expected]
    if bad:
        raise RuntimeError('his files differ from M_FILES.md hashes: %s' % bad)
    return rows


def load():
    """Verify, then import his real modules. Returns a namespace-like dict. Removes any reconstruction module (answer_gate stub) first so his own answer_gate is the one imported."""
    verify()
    for name in ('answer_gate', 'namefix_rule', 'namefix_rule_demo'):
        sys.modules.pop(name, None)
    sys.path.insert(0, str(STUDIES / 'exam_arms_20261121'))
    import exam_arms
    import harness
    import run_pilot
    import run_stage1
    import answer_gate
    from menu_run_study import Recorder, ToolRecorder
    from rosa.tools import ros2
    for module in (answer_gate, exam_arms, harness, run_pilot):
        if not str(Path(module.__file__).resolve()).startswith(str(HIS_ROOT.resolve())):
            raise RuntimeError('%s was not imported from his files: %s' % (module.__name__, module.__file__))
    return dict(exam_arms=exam_arms, harness=harness, run_pilot=run_pilot, run_stage1=run_stage1, answer_gate=answer_gate,
                Recorder=Recorder, ToolRecorder=ToolRecorder, ros2=ros2)


def make_arm_class(h):
    """MergedM = his exam_arms.ExamArm ('M') + ONE added tool, run_skill (same pattern as his own ActionM in exam_actions_20261121/action_arms.py)."""
    from .prompts import MACRO_RULES, SKILL_LINE
    from .skill_tool import DESCRIPTION, RunSkillArgs

    class MergedM(h['exam_arms'].ExamArm):
        def __init__(self, recorder, context, runner):
            super().__init__('M', recorder, context, list(h['run_pilot'].prompt_for('A1')) + [('system', MACRO_RULES), ('system', SKILL_LINE)])
            self.name = 'M+macro (merged demo)'
            self.runner = runner
            runner.request_of = lambda: self.request_count          # one run_skill per model response

        def base_menu(self):
            return list(super().base_menu()) + ['run_skill']

        def wrap_tools(self, tools):
            wrapped = super().wrap_tools(tools)
            inner = StructuredTool(name='run_skill', description=DESCRIPTION, args_schema=RunSkillArgs, func=self.runner.run)
            self.schemas['run_skill'] = convert_to_openai_tool(inner)['function']['parameters']
            wrapped.append(h['harness'].PilotTool(name='run_skill', description=DESCRIPTION, args_schema=RunSkillArgs, arm=self, func=self._bind(inner),
                                                  handle_tool_error=True, handle_validation_error=self._pydantic_text))
            return wrapped

    return MergedM


class FakeToolModel(BaseChatModel):
    """Scripted chat model for dry runs (NO real model call). steps: list of [(tool name, args), ...] (one response) or a string (text-only response)."""
    steps: list
    index: int = 0

    @property
    def _llm_type(self):
        return 'scripted-fake'

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.index >= len(self.steps):
            raise AssertionError('scripted model has no step left')
        step = self.steps[self.index]
        self.index += 1
        usage = {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}
        if isinstance(step, str):
            message = AIMessage(content=step, usage_metadata=usage)
        else:
            calls = [{'name': n, 'args': a, 'id': 'call_%d_%d' % (self.index, i), 'type': 'tool_call'} for i, (n, a) in enumerate(step)]
            message = AIMessage(content='', tool_calls=calls, usage_metadata=usage)
        return ChatResult(generations=[ChatGeneration(message=message)])


def run_dry(h, task_text, steps, runner_factory, trace_path, canned_ros):
    """One episode through HIS real machinery (PilotROSA, ArmTracedModel, ExamArm logic) with a fake model and canned ROS command output (no ROS graph, no Gazebo).
    runner_factory(recorder) -> SkillRunner. Returns (answer json text or None, error, arm, recorder)."""
    run_pilot, run_stage1 = h['run_pilot'], h['run_stage1']
    recorder = h['Recorder'](Path(trace_path))
    context = dict(env='merged_demo', task={'id': 'demo', 'request': task_text, 'floor': 0}, ns='')
    runner = runner_factory(recorder)
    arm = make_arm_class(h)(recorder, context, runner)
    h['ros2'].execute_ros_command = canned_ros
    answer = error = None
    try:
        model = run_pilot.ArmTracedModel(holder={'model': FakeToolModel(steps=steps)}, recorder=recorder, options={}, arm=arm)
        agent = run_pilot.PilotROSA(model, arm)
        result = agent._ROSA__executor.invoke({'input': task_text, 'chat_history': []}, config={'callbacks': [h['ToolRecorder'](recorder)]})
        answer = result['output']
    except Exception as failure:
        error = repr(failure)
    finally:
        arm.close()
    return answer, error, arm, recorder
