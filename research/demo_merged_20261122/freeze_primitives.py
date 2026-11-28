"""Freeze record of arm (b) "M + primitives". Zero model calls. Run in WSL: python freeze_primitives.py
Writes FREEZE_DEMO_PRIMITIVES.json. LABEL: merged method (Levinson M + Martin bounded macro), arm (b) primitives, demonstration only, not evaluated, not for the paper."""
import datetime
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from merged_demo import his_m  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.his_m_primitives import make_primitive_arm_class  # noqa: E402
from merged_demo.primitives_tool import PrimitiveRunner  # noqa: E402
from merged_demo.skill_tool import ur5e_registry  # noqa: E402


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def file_sha(rel):
    return hashlib.sha256((HERE / rel).read_bytes()).hexdigest()


def main():
    rows = his_m.verify()
    h = his_m.load()
    from rosa.tools import ROSATools
    recorder = h['Recorder'](Path('/tmp/freeze_b_trace.jsonl'))
    runner = PrimitiveRunner(ur5e_registry(), {'state': FakeArm(), 'inspection': FakeReadiness()}, EventLog())
    arm = make_primitive_arm_class(h)(recorder, dict(env='freeze', task={'id': 'f', 'request': 'x', 'floor': 0}, ns=''), runner)
    tools = arm.wrap_tools(ROSATools(2).get_tools())
    offered = arm.base_menu()
    by_name = {t.name: t for t in tools}
    tool_defs = {n: {'description': by_name[n].description, 'schema': arm.schemas[n]} for n in offered}
    a = json.loads((HERE / 'FREEZE_DEMO_MERGED.json').read_text())
    record = {
        'label': 'merged method (Levinson M + Martin bounded macro), arm (b) M + primitives, demonstration only, not evaluated, not for the paper',
        'frozen_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'his_files': {'commit': his_m.COMMIT, 'rows_verified_byte_for_byte': len(rows), 'edited': False},
        'arm_a_reference': {'freeze_file': 'FREEZE_DEMO_MERGED.json', 'prompt_sha256': a['prompt_sha256_his_function'], 'tool_set_sha256': a['tool_set_sha256']},
        'prompt_messages': arm.prompt_messages,
        'prompt_sha256_his_function': h['run_pilot'].prompt_hash(arm.prompt_messages),
        'prompt_difference_from_arm_a': 'only the words naming run_skill in the first rule sentence (replaced by the four primitive tool names) and the skill line (describes the four tools); '
                                         'all other sentences and his A1 messages identical (see tests/test_primitives_arm.py)',
        'offered_tools': offered,
        'tool_defs_sha256': {n: sha(json.dumps(d, sort_keys=True, default=str)) for n, d in tool_defs.items()},
        'tool_set_sha256': sha(json.dumps(tool_defs, sort_keys=True, default=str)),
        'guards_same_as_arm_a': {'writes_per_task': 1, 'native_operations': 10, 'tool_attempts': 16, 'seconds': 180, 'tolerance': 0.025,
                                 'targets': 'registered skill targets only (ur5e_registry)', 'one_primitive_per_response': True, 'read_before_write': True,
                                 'no_replay_after_unconfirmed_write': True},
        'files_sha256': {rel: file_sha(rel) for rel in ('merged_demo/primitives_tool.py', 'merged_demo/primitive_prompts.py', 'merged_demo/his_m_primitives.py',
                                                         'tests/test_primitives_arm.py')},
        'arm_a_files_unchanged_sha256': {rel: file_sha(rel) for rel in ('merged_demo/skill_tool.py', 'merged_demo/prompts.py', 'merged_demo/his_m.py', 'live_demo.py')},
        'no_per_model_tuning': True,
    }
    (HERE / 'FREEZE_DEMO_PRIMITIVES.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(record['tool_set_sha256'], record['prompt_sha256_his_function'])


if __name__ == '__main__':
    main()
