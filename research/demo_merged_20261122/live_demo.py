"""LIVE driver (steps 7-8) for the merged demo. Run in WSL. ADAPTATION FILE (ours); his files are used unedited.
LABEL: "merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated". Not method M, not scored.
Usage: python live_demo.py <new output folder> [--model sol|qwen] [--tasks D1,D2,D3] [--take N]
Sol: settings are the hosted session's (no local context). Qwen fallback only if Sol is unavailable: num_ctx 8192 instead of his 65536 (labelled).
One Gazebo instance, ROS_DOMAIN_ID 232, reset + independent confirmation before each task, every take kept."""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

os.environ.update(ROS_DOMAIN_ID='232', ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST',
                  LANGCHAIN_TRACING='false', LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, '/mnt/c/Proj/robotics/introtorobotics/rosa-research/src')
from merged_demo import his_m, prompts  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

LABEL = 'merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated'
TOL = 0.025


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    ap.add_argument('--model', choices=('sol', 'qwen'), default='sol')
    ap.add_argument('--tasks', default='D1,D2,D3')
    ap.add_argument('--take', type=int, default=1)
    ap.add_argument('--endpoint', default='http://127.0.0.1:11434')
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    h = his_m.load()
    from rosa_reliability.gazebo_demo import GazeboDemo
    from rosa_reliability.ros_arm import ArmTransport, JOINTS
    from rosa_reliability.ros_readiness import ArmReadinessTransport
    registry = ur5e_registry()
    tasks = {t['id']: t for t in prompts.load_tasks()['tasks']}
    freeze = json.loads((HERE / 'FREEZE_DEMO_MERGED.json').read_text())
    meta = {'label': LABEL, 'model': args.model, 'take': args.take, 'ros_domain_id': 232, 'freeze_tool_set_sha256': freeze['tool_set_sha256'],
            'freeze_prompt_sha256': freeze['prompt_sha256_his_function'], 'his_commit': his_m.COMMIT, 'tasks': [], 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z')}
    if args.model == 'qwen':
        meta['settings'] = {'num_ctx': 8192, 'deviation': 'context 8192 instead of his 65536', 'temperature': 0, 'seed': 42, 'num_predict': 1024}
    else:
        meta['settings'] = {'model': 'gpt-6.1-sol', 'note': 'hosted session settings; no local context limit'}
    write(out / 'RUN_META.json', meta)
    demo = GazeboDemo(out / 'gazebo')
    movement = inspection = observer = None
    chat = transport = session = None
    try:
        demo.start()
        movement, inspection, observer = ArmTransport(), ArmReadinessTransport(), ArmTransport(read_only=True)
        if args.model == 'sol':
            from rosa_auth.remembered import remembered_session
            from rosa_auth.responses import SiwcBackend
            from rosa_backends.chat_siwc import ChatSiwc
            status = {}
            session = remembered_session(request_budget=60, status=status)
            auth = session.__enter__()
            transport = SiwcBackend(request_budget=60, token_provider=auth.access_token)
            chat = ChatSiwc(model='gpt-6.1-sol', backend=transport)
        else:
            from rosa_backends.chat_ollama import ConfiguredChatOllama
            chat = ConfiguredChatOllama(model='qwen3.5:9b', base_url=args.endpoint, num_ctx=8192, num_predict=1024, temperature=0, seed=42,
                                        use_mmap=True, streaming=False, reasoning=False, cache=False, client_kwargs={'timeout': 180})
        for tid in args.tasks.split(','):
            task = tasks[tid]
            folder = out / ('%s_take%d' % (tid, args.take))
            folder.mkdir()
            record = {'task': tid, 'reset_ok': False}
            meta['tasks'].append(record)
            # outside-task reset to the documented start pose + independent confirmation (not model-visible)
            home = registry.catalogue()[task['initial']]['targets']['/ur5e']
            movement.read('/ur5e', list(JOINTS))
            movement.write('/ur5e', home)
            seen = observer.read('/ur5e', list(JOINTS))
            record['reset_observation'] = seen
            record['reset_ok'] = all(abs(seen[k] - v) <= TOL for k, v in home.items())
            write(out / 'RUN_META.json', meta)
            if not record['reset_ok']:
                record['status'] = 'RESET_FAILED_NOT_RUN'
                write(out / 'RUN_META.json', meta)
                continue
            recorder = h['Recorder'](folder / 'trace.jsonl')
            log = EventLog(sink=recorder)
            runner = SkillRunner(registry, {'state': movement, 'inspection': inspection}, log)
            context = dict(env='merged_demo_live', task={'id': tid, 'request': task['text'], 'floor': 0}, ns='')
            arm = his_m.make_arm_class(h)(recorder, context, runner)
            recorder.add('episode_start', label=LABEL, task=tid, request=task['text'], model=args.model, settings=meta['settings'], take=args.take,
                         prompt_sha256=h['run_pilot'].prompt_hash(arm.prompt_messages), prompts=arm.prompt_messages,
                         max_iterations=h['run_pilot'].MAX_ITERATIONS)
            guarded = sys.modules['menu_run_study'].guarded_native
            h['ros2'].execute_ros_command = guarded(recorder)
            answer = error = None
            started = time.perf_counter()
            try:
                model = h['run_pilot'].ArmTracedModel(holder={'model': chat}, recorder=recorder, options={}, arm=arm)
                agent = h['run_pilot'].PilotROSA(model, arm)
                result = agent._ROSA__executor.invoke({'input': task['text'], 'chat_history': []}, config={'callbacks': [h['ToolRecorder'](recorder)]})
                answer = result['output']
            except Exception as failure:
                error = repr(failure)
            finally:
                arm.close()
            recorder.add('episode_end', answer=answer, error=error, seconds=time.perf_counter() - started)
            final = observer.read('/ur5e', list(JOINTS))
            record.update(status='COMPLETE' if answer else 'NO_ANSWER', answer=answer, error=error, final_independent_observation=final,
                          run_skill_calls=runner.calls, writes=runner.writes_total, seconds=round(time.perf_counter() - started, 1))
            write(folder / 'answer.json', record)
            write(out / 'RUN_META.json', meta)
            print(tid, record['status'], 'writes', runner.writes_total, 'calls', runner.calls, flush=True)
    finally:
        for item in (chat, movement, inspection, observer):
            try:
                if item:
                    item.close()
            except Exception:
                pass
        if session:
            try:
                session.__exit__(None, None, None)
            except Exception:
                pass
        meta['gazebo_close'] = demo.close()
        meta['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        write(out / 'RUN_META.json', meta)


if __name__ == '__main__':
    main()
