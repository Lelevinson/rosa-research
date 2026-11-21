"""Freeze record of the demo texts and tool definitions (step 6). Zero model calls. Run in WSL: python freeze.py
Writes FREEZE_DEMO.json. Re-run with a dated amendment when Levinson's prompt strings / answer_gate.py arrive (the prompt and name-fix provenance then change)."""
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from merged_demo import menu, prompts  # noqa: E402
from merged_demo.fakes import FakeArm, FakeReadiness  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.loop import FINAL_DESCRIPTION, final_tool  # noqa: E402
from merged_demo.namefix import load  # noqa: E402
from merged_demo.skill_tool import DESCRIPTION, SkillRunner, ur5e_registry  # noqa: E402


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


def main():
    tasks = prompts.load_tasks()
    prompt, prompt_info = prompts.load_prompt()
    registry = ur5e_registry()
    runner = SkillRunner(registry, {'state': FakeArm(), 'inspection': FakeReadiness()}, EventLog())
    tools = menu.stock_menu() + [runner.tool(), final_tool()]
    _, _, namefix_info = load()
    research_main = HERE.parent.parent.parent / 'rosa-research'
    record = {
        'frozen_at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        'status': 'DRAFT FREEZE: prompt is the FALLBACK (not his wording) and answer_gate is a RECONSTRUCTION until Levinson sends his strings/file',
        'purpose': 'demo only; no scoring, no claims; not pooled with any M4/G1/D/F1/parity or Levinson result',
        'tasks': {t['id']: {'text': t['text'], 'sha256': sha(t['text'])} for t in tasks['tasks']},
        'prompt': {'text': prompt, **prompt_info},
        'finish_tool_description': FINAL_DESCRIPTION,
        'run_skill_description': DESCRIPTION,
        'catalogue_sha256': sha(json.dumps(registry.catalogue(), sort_keys=True)),
        'tools': {t.name: sha(json.dumps(menu.tool_json(t), sort_keys=True, default=str)) for t in tools},
        'tool_set_sha256': sha(json.dumps([menu.tool_json(t) for t in tools], sort_keys=True, default=str)),
        'name_fix': namefix_info,
        'limits': {'max_requests': 8, 'run_skill_calls': 2, 'writes_per_task': 1, 'macro': 'MacroLimits() defaults (10 native operations, 16 tool attempts, 3 corrections, 180 s, tolerance 0.025)'},
        'code': {'rosa_research_checkout': git('rev-parse', 'HEAD', cwd=research_main), 'rosa_research_branch': git('rev-parse', '--abbrev-ref', 'HEAD', cwd=research_main),
                 'merge_branch_head': git('rev-parse', 'HEAD', cwd=HERE),
                 'files': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((HERE / 'merged_demo').glob('*.py'))}},
    }
    (HERE / 'FREEZE_DEMO.json').write_text(json.dumps(record, indent=1, sort_keys=True), encoding='utf-8')
    print('tool_set_sha256', record['tool_set_sha256'])
    print('prompt', prompt_info)
    print('catalogue', record['catalogue_sha256'][:16], 'tools', list(record['tools']))


if __name__ == '__main__':
    main()
