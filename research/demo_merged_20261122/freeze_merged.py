"""Freeze record of the merged demo built on HIS real files (step 6, revised). Zero model calls. Run in WSL: python freeze_merged.py
Writes FREEZE_DEMO_MERGED.json. Supersedes FREEZE_DEMO.json (which used our substitutes for his prompt and answer_gate)."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from merged_demo import his_m, prompts  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.skill_tool import DESCRIPTION, SkillRunner, ur5e_registry  # noqa: E402


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


def main():
    rows = his_m.verify()                                             # raises unless all 26 rows match M_FILES.md byte for byte
    h = his_m.load()
    from rosa.tools import ROSATools
    registry = ur5e_registry()
    recorder = h['Recorder'](Path('/tmp/freeze_trace.jsonl'))
    runner = SkillRunner(registry, {'state': FakeArm(), 'inspection': FakeReadiness()}, EventLog())
    arm = his_m.make_arm_class(h)(recorder, dict(env='freeze', task={'id': 'f', 'request': 'x', 'floor': 0}, ns=''), runner)
    tools = arm.wrap_tools(ROSATools(2).get_tools())
    offered = arm.base_menu()
    by_name = {t.name: t for t in tools}
    tool_defs = {n: {'description': by_name[n].description, 'schema': arm.schemas[n]} for n in offered}
    tasks = prompts.load_tasks()
    messages = arm.prompt_messages
    research_main = HERE.parent.parent.parent / 'rosa-research'
    record = {
        'label': 'merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated',
        'credit': 'method M components (Levinson); bounded macro run_skill (Martin)',
        'frozen_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'purpose': 'demo only; no scoring; not method M; never pooled with or compared against his M / Stage 1 results or any M4/G1/D/F1/parity result',
        'his_files': {'branch': 'origin/member/levinson', 'commit': his_m.COMMIT, 'table': 'M_FILES.md', 'rows_verified_byte_for_byte': len(rows),
                      'extraction': 'extract_his_files.sh (git archive, eol conversion disabled)', 'edited': False},
        'his_settings_not_applied_to_a_fake_run': {'NUM_CTX': h['run_pilot'].NUM_CTX, 'NUM_PREDICT': h['run_pilot'].NUM_PREDICT, 'MAX_ITERATIONS': h['run_pilot'].MAX_ITERATIONS,
                                                   'note': 'Martin G1/M4 used num_ctx 8192. A live demo run must state which settings it uses.'},
        'tasks': {t['id']: {'text': t['text'], 'sha256': sha(t['text'])} for t in tasks['tasks']},
        'prompt_messages': messages,
        'prompt_sha256_his_function': h['run_pilot'].prompt_hash(messages),
        'prompt_composition': 'his run_pilot.prompt_for("A1") (7 messages, verbatim) + 2 macro lines (ours: M4 RULES sentences 1-4 and last, run_skill line) + his FINAL_ANSWER_LINE',
        'offered_tools': offered,
        'tool_defs_sha256': {n: sha(json.dumps(d, sort_keys=True, default=str)) for n, d in tool_defs.items()},
        'tool_set_sha256': sha(json.dumps(tool_defs, sort_keys=True, default=str)),
        'run_skill_description': DESCRIPTION,
        'catalogue_sha256': sha(json.dumps(registry.catalogue(), sort_keys=True)),
        'limits': {'his_executor_iterations': h['run_pilot'].MAX_ITERATIONS, 'run_skill_calls': 2, 'run_skill_per_response': 1, 'writes_per_task': 1,
                   'macro': 'MacroLimits() defaults (10 native operations, 16 tool attempts, 3 corrections, 180 s, tolerance 0.025)'},
        'code': {'rosa_research_checkout': git('rev-parse', 'HEAD', cwd=research_main), 'rosa_research_branch': git('rev-parse', '--abbrev-ref', 'HEAD', cwd=research_main),
                 'merge_branch_head': git('rev-parse', 'HEAD', cwd=HERE),
                 'files': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE / 'merged_demo').glob('*.py'))}},
    }
    (HERE / 'FREEZE_DEMO_MERGED.json').write_text(json.dumps(record, indent=1, sort_keys=True), encoding='utf-8')
    print('verified rows', len(rows))
    print('offered', offered)
    print('tool_set_sha256', record['tool_set_sha256'])
    print('prompt_sha256', record['prompt_sha256_his_function'])


if __name__ == '__main__':
    main()
