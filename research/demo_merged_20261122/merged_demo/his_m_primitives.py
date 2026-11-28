"""ADAPTATION FILE (ours), arm (b): his exam_arms.ExamArm ('M', byte for byte, loaded by his_m.load) + FOUR primitive action tools instead of `run_skill`.
LABEL: merged-method demo, arm (b) "M + primitives", demonstration only, not evaluated, not for the paper. Same pattern as his_m.make_arm_class (arm a)."""
from langchain_core.tools import StructuredTool
from langchain_core.utils.function_calling import convert_to_openai_tool


def make_primitive_arm_class(h):
    from .primitive_prompts import PRIMITIVE_LINE, PRIMITIVE_RULES
    from .primitives_tool import TOOL_NAMES

    class MergedPrimitives(h['exam_arms'].ExamArm):
        def __init__(self, recorder, context, runner):
            super().__init__('M', recorder, context, list(h['run_pilot'].prompt_for('A1')) + [('system', PRIMITIVE_RULES), ('system', PRIMITIVE_LINE)])
            self.name = 'M+primitives (merged demo arm b)'
            self.runner = runner
            runner.request_of = lambda: self.request_count          # one primitive tool per model response

        def base_menu(self):
            return list(super().base_menu()) + list(TOOL_NAMES)

        def wrap_tools(self, tools):
            wrapped = super().wrap_tools(tools)
            for inner in self.runner.tools():
                self.schemas[inner.name] = convert_to_openai_tool(inner)['function']['parameters']
                wrapped.append(h['harness'].PilotTool(name=inner.name, description=inner.description, args_schema=inner.args_schema, arm=self, func=self._bind(inner),
                                                      handle_tool_error=True, handle_validation_error=self._pydantic_text))
            return wrapped

    return MergedPrimitives
