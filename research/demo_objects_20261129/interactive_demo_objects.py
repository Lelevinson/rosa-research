"""Interactive terminal demo WITH objects (Milestone 4/5). NEW FILE; the frozen demo is imported, never modified.
LABEL: merged method (Levinson M + Martin bounded macro) plus object tools, Sol; object poses read from the simulator (ground truth); simulated gripper with grasp assist;
demonstration only, not evaluated, not for the paper.
Needs the objects simulation + MoveIt already running (run_objects_demo.sh starts everything). Usage:
  python interactive_demo_objects.py <new output folder> <gz_partition.txt> [--requests-file FILE] [--block "x y yaw"]
Commands at the prompt:  reset (arm home, gripper open, block back to its start pose)   quit.  The world is NOT reset between requests (so 'pick' then 'place' can be separate requests)."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('ROS_DOMAIN_ID', '231')
os.environ.update(ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST', LANGCHAIN_TRACING='false', LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'demo_merged_20261122'))
sys.path.insert(0, os.environ.get('ROSA_RESEARCH_SRC', '/mnt/c/Proj/robotics/introtorobotics/rosa-research/src'))
from merged_demo import his_m  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

import interactive_demo as base  # noqa: E402
import objects_lib as ol  # noqa: E402
import objects_skills as sk  # noqa: E402
from objects_agent import ObjectTools, make_objects_arm_class  # noqa: E402

say, short, BAR = base.say, base.short, base.BAR
LABEL = 'merged method (Levinson M + Martin bounded macro) + object tools, Sol; ground-truth poses; simulated gripper with grasp assist; demonstration only, not evaluated'


class ObjectsPrinter(base.LivePrinter):
    def show(self, kind, v):
        if kind == 'macro_object_call_end':
            say('   [object] %s -> %s: %s' % (v.get('tool'), 'OK' if v.get('ok') else ('REFUSED' if v.get('refused') else 'FAILED at ' + str(v.get('step'))), short(v.get('detail'), 160)))
        elif kind == 'macro_object_call_start':
            return
        else:
            super().show(kind, v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    ap.add_argument('partition_file')
    ap.add_argument('--requests-file')
    ap.add_argument('--block', default='0.45 0.10 0.0', help='block start pose used by "reset" (must match the simulation)')
    ap.add_argument('--request-budget', type=int, default=400)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    scripted = [l.strip() for l in Path(args.requests_file).read_text(encoding='utf-8').splitlines() if l.strip() and not l.startswith('#')] if args.requests_file else None
    partition = Path(args.partition_file).read_text().strip()
    block_start = tuple(float(v) for v in args.block.split())
    h = his_m.load()
    from rosa_reliability.ros_arm import ArmTransport, JOINTS
    from rosa_reliability.ros_readiness import ArmReadinessTransport
    from rosa_auth.remembered import remembered_session
    from rosa_auth.responses import SiwcBackend
    from rosa_backends.chat_siwc import ChatSiwc
    registry = ur5e_registry()
    movement = inspection = observer = session = arm_obj = None
    meta = {'label': LABEL, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'model': 'sol', 'his_commit': his_m.COMMIT, 'requests': []}
    try:
        say(BAR); say('  ROSA interactive demo with objects'); say('  ' + LABEL); say(BAR)
        arm_obj = ol.ObjectsArm(partition)
        skills = sk.Skills(arm_obj)
        movement, inspection, observer = ArmTransport(), ArmReadinessTransport(), ArmTransport(read_only=True)
        session = remembered_session(request_budget=args.request_budget, status={})
        auth = session.__enter__()
        chat = ChatSiwc(model='gpt-6.1-sol', backend=SiwcBackend(request_budget=args.request_budget, token_provider=auth.access_token))
        ok, info = sk.reset_world(arm_obj, block_start, partition)
        say('World reset: %s %s' % ('ok' if ok else 'PROBLEM', info))
        say('Type a request, or: reset | quit')
        queue, number = (list(scripted) if scripted is not None else None), 0
        while True:
            if queue is not None:
                if not queue:
                    break
                line = queue.pop(0); say(''); say('request> ' + line)
            else:
                try:
                    line = input('\nrequest> ').strip()
                except EOFError:
                    break
            if not line:
                continue
            if line.lower() in ('quit', 'exit'):
                break
            if line.lower() == 'reset':
                ok, info = sk.reset_world(arm_obj, block_start, partition); skills.held = False
                say('World reset: %s %s' % ('ok' if ok else 'PROBLEM', info)); continue
            number += 1
            folder = out / ('req_%02d' % number); folder.mkdir()
            record = {'n': number, 'request': line}
            meta['requests'].append(record)
            say(BAR); say('REQUEST %d: %s' % (number, line)); say(BAR)
            recorder = h['Recorder'](folder / 'trace.jsonl')
            printer = ObjectsPrinter(recorder)
            log = EventLog(sink=recorder)
            runner = SkillRunner(registry, {'state': movement, 'inspection': inspection}, log)
            tools = ObjectTools(skills, log)
            arm = make_objects_arm_class(h)(recorder, dict(env='objects_demo_interactive', task={'id': 'typed', 'request': line, 'floor': 0}, ns=''), runner, tools)
            recorder.add('episode_start', label=LABEL, task='typed', request=line, model='sol', take=number, prompt_sha256=h['run_pilot'].prompt_hash(arm.prompt_messages),
                         prompts=arm.prompt_messages, max_iterations=h['run_pilot'].MAX_ITERATIONS)
            h['ros2'].execute_ros_command = sys.modules['menu_run_study'].guarded_native(recorder)
            answer = error = None
            started = time.perf_counter()
            try:
                model = h['run_pilot'].ArmTracedModel(holder={'model': chat}, recorder=recorder, options={}, arm=arm)
                agent = h['run_pilot'].PilotROSA(model, arm)
                answer = agent._ROSA__executor.invoke({'input': line, 'chat_history': []}, config={'callbacks': [h['ToolRecorder'](recorder)]})['output']
            except Exception as failure:
                error = repr(failure)
            finally:
                arm.close()
            seconds = round(time.perf_counter() - started, 1)
            recorder.add('episode_end', answer=answer, error=error, seconds=seconds)
            block, tray = arm_obj.truth.pose('red_block'), arm_obj.truth.pose('tray')
            held = skills.is_held()
            on_tray = skills.block_on_tray()
            final = observer.read('/ur5e', list(JOINTS))
            record.update(status='COMPLETE' if answer else 'NO_ANSWER' if not error else 'ERROR', answer=answer, error=error, model_calls=printer.model_calls,
                          object_calls=[(e['tool'], e['ok']) for e in log.of('object_call_end')], run_skill_calls=runner.calls, seconds=seconds,
                          final_state={'block_xyz': [round(v, 3) for v in block[:3]], 'block_held': held, 'block_on_tray': on_tray, 'joints': {k: round(v, 3) for k, v in final.items()}})
            say(''); say(BAR)
            say('ANSWER: %s' % (answer if answer else ('ERROR: ' + str(error) if error else '(no answer)')))
            say('Independent final state: block at x %.3f y %.3f z %.3f, held by gripper: %s, on the tray: %s' % (block[0], block[1], block[2], held, on_tray))
            say('Model calls %d, object calls %d, skill calls %d, %.1f s' % (printer.model_calls, len(log.of('object_call_end')), runner.calls, seconds))
            say(BAR)
            (folder / 'answer.json').write_text(json.dumps(record, indent=1, default=str), encoding='utf-8')
            (out / 'SESSION.json').write_text(json.dumps(meta, indent=1, default=str), encoding='utf-8')
    finally:
        for item in (movement, inspection, observer):
            try:
                if item:
                    item.close()
            except Exception:
                pass
        if arm_obj:
            try:
                arm_obj.close()
            except Exception:
                pass
        if session:
            try:
                session.__exit__(None, None, None)
            except Exception:
                pass
        meta['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        (out / 'SESSION.json').write_text(json.dumps(meta, indent=1, default=str), encoding='utf-8')
        say('Session closed (the simulation keeps running; stop it with stop_sim.sh).')


if __name__ == '__main__':
    main()
