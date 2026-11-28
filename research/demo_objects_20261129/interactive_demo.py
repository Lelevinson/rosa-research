"""Interactive terminal demo (Milestone 0). NEW FILE; the frozen merged demo (research/demo_merged_20261122) is imported and never modified.
LABEL: merged method (Levinson M + Martin bounded macro), Sol, demonstration only, not evaluated, not for the paper.
Run in WSL (research env, ROS sourced). Usage:
  python interactive_demo.py <new output folder> [--requests-file FILE]     (FILE = one request per line; used for rehearsals, otherwise you type)
Commands at the prompt:  reset  (arm back to home)   quit
Each request: arm is reset to home first (unless --keep-state), the request runs through the SAME merged agent (his M files verified byte for byte + run_skill), the tool calls
are printed live, then the answer and the independent final state are shown. Sol only, existing remembered sign-in only."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('ROS_DOMAIN_ID', '232')
os.environ.update(ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST', LANGCHAIN_TRACING='false', LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false')
HERE = Path(__file__).resolve().parent
FROZEN = HERE.parent / 'demo_merged_20261122'
sys.path.insert(0, str(FROZEN))
sys.path.insert(0, os.environ.get('ROSA_RESEARCH_SRC', str(HERE.parents[2] / 'rosa-research/src')))
sys.path.insert(0, '/mnt/c/Proj/robotics/introtorobotics/rosa-research/src')
from merged_demo import his_m  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

LABEL = 'merged method (Levinson M + Martin bounded macro), Sol, demonstration only, not evaluated'
TOL = 0.025
BAR = '=' * 64


def say(text='', **kw):
    print(text, flush=True, **kw)


def short(value, limit=200):
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit - 3] + '...'


class LivePrinter:
    """Wraps his Recorder.add: every row is still written to trace.jsonl; the readable ones are also printed (one idea per line, large-font friendly)."""
    def __init__(self, recorder):
        self.recorder = recorder
        self.original = recorder.add
        recorder.add = self.add
        self.model_calls = 0

    def add(self, kind, **values):
        result = self.original(kind, **values)
        try:
            self.show(kind, values)
        except Exception:
            pass
        return result

    def show(self, kind, v):
        if kind == 'model_start':
            self.model_calls += 1
            say('')
            say('-- model call %d ...' % self.model_calls)
        elif kind == 'model_end':
            message = v.get('message') or {}
            for call in message.get('tool_calls') or []:
                say('   model asks: %s %s' % (call['name'], short(call.get('args'), 120)))
            text = message.get('content')
            if text and isinstance(text, str) and text.strip():
                say('   model says: %s' % short(text, 300))
            usage = v.get('usage') or {}
            say('   (tokens in %s / out %s, %.1f s)' % (usage.get('input_tokens', '?'), usage.get('output_tokens', '?'), v.get('seconds') or 0))
        elif kind == 'tool_start':
            say('   >> tool: %s %s' % (v.get('name'), short(v.get('input'), 120)))
        elif kind == 'tool_end':
            say('   << result: %s' % short(v.get('output'), 220))
        elif kind == 'macro_skill_call_end':
            say('   [macro] %s %s, writes dispatched: %s%s' % (v.get('skill_id'), v.get('outcome'), v.get('writes_dispatched'),
                                                              (', write skipped: ' + str(v['write_skipped'])) if v.get('write_skipped') else ''))
        elif kind == 'final_answer_accepted':
            say('   ** final answer accepted: %s' % short(v.get('answer'), 300))


def reset_home(registry, movement, observer, JOINTS):
    home = registry.catalogue()['ur5e.home']['targets']['/ur5e']
    movement.read('/ur5e', list(JOINTS))
    movement.write('/ur5e', home)
    seen = observer.read('/ur5e', list(JOINTS))
    return all(abs(seen[k] - v) <= TOL for k, v in home.items()), seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    ap.add_argument('--requests-file')
    ap.add_argument('--keep-state', action='store_true', help='do not reset the arm to home before each request')
    ap.add_argument('--request-budget', type=int, default=400)
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    scripted = [line.strip() for line in Path(args.requests_file).read_text(encoding='utf-8').splitlines() if line.strip() and not line.startswith('#')] if args.requests_file else None
    h = his_m.load()
    from rosa_reliability.gazebo_demo import GazeboDemo
    from rosa_reliability.ros_arm import ArmTransport, JOINTS
    from rosa_reliability.ros_readiness import ArmReadinessTransport
    from rosa_auth.remembered import remembered_session
    from rosa_auth.responses import SiwcBackend
    from rosa_backends.chat_siwc import ChatSiwc
    registry = ur5e_registry()
    demo = GazeboDemo(out / 'gazebo')
    movement = inspection = observer = session = None
    meta = {'label': LABEL, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'model': 'sol', 'his_commit': his_m.COMMIT, 'requests': []}
    try:
        say(BAR); say('  ROSA interactive demo'); say('  ' + LABEL); say(BAR)
        say('Starting the simulator (about 30 s) ...')
        demo.start()
        movement, inspection, observer = ArmTransport(), ArmReadinessTransport(), ArmTransport(read_only=True)
        status = {}
        session = remembered_session(request_budget=args.request_budget, status=status)
        auth = session.__enter__()
        chat = ChatSiwc(model='gpt-6.1-sol', backend=SiwcBackend(request_budget=args.request_budget, token_provider=auth.access_token))
        ok, seen = reset_home(registry, movement, observer, JOINTS)
        say('Arm at home: %s' % ('yes' if ok else 'NO (reset check failed)'))
        say('Type a request, or: reset | quit')
        number = 0
        queue = list(scripted) if scripted is not None else None
        while True:
            if queue is not None:
                if not queue:
                    break
                line = queue.pop(0)
                say(''); say('request> ' + line)
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
                ok, seen = reset_home(registry, movement, observer, JOINTS)
                say('Arm reset to home: %s' % ('yes' if ok else 'NO'))
                continue
            number += 1
            folder = out / ('req_%02d' % number)
            folder.mkdir()
            record = {'n': number, 'request': line}
            meta['requests'].append(record)
            if not args.keep_state:
                ok, seen = reset_home(registry, movement, observer, JOINTS)
                record['reset_ok'] = ok
                if not ok:
                    say('RESET FAILED: request not run'); record['status'] = 'RESET_FAILED_NOT_RUN'; continue
            say(BAR); say('REQUEST %d: %s' % (number, line)); say(BAR)
            recorder = h['Recorder'](folder / 'trace.jsonl')
            printer = LivePrinter(recorder)
            log = EventLog(sink=recorder)
            runner = SkillRunner(registry, {'state': movement, 'inspection': inspection}, log)
            context = dict(env='merged_demo_interactive', task={'id': 'typed', 'request': line, 'floor': 0}, ns='')
            arm = his_m.make_arm_class(h)(recorder, context, runner)
            recorder.add('episode_start', label=LABEL, task='typed', request=line, model='sol', take=number,
                         prompt_sha256=h['run_pilot'].prompt_hash(arm.prompt_messages), prompts=arm.prompt_messages, max_iterations=h['run_pilot'].MAX_ITERATIONS)
            h['ros2'].execute_ros_command = sys.modules['menu_run_study'].guarded_native(recorder)
            answer = error = None
            started = time.perf_counter()
            try:
                model = h['run_pilot'].ArmTracedModel(holder={'model': chat}, recorder=recorder, options={}, arm=arm)
                agent = h['run_pilot'].PilotROSA(model, arm)
                result = agent._ROSA__executor.invoke({'input': line, 'chat_history': []}, config={'callbacks': [h['ToolRecorder'](recorder)]})
                answer = result['output']
            except Exception as failure:
                error = repr(failure)
            finally:
                arm.close()
            seconds = round(time.perf_counter() - started, 1)
            recorder.add('episode_end', answer=answer, error=error, seconds=seconds)
            final = observer.read('/ur5e', list(JOINTS))
            record.update(status='COMPLETE' if answer else 'NO_ANSWER' if not error else 'ERROR', answer=answer, error=error, final_independent_observation=final,
                          model_calls=printer.model_calls, run_skill_calls=runner.calls, writes=runner.writes_total, seconds=seconds)
            say(''); say(BAR)
            say('ANSWER: %s' % (answer if answer else ('ERROR: ' + str(error) if error else '(no answer)')))
            say('Independent final state: shoulder_pan %.3f, wrist_3 %.3f (all joints read by a separate read-only observer)' % (final['shoulder_pan_joint'], final['wrist_3_joint']))
            say('Model calls %d, skill calls %d, writes %d, %.1f s' % (printer.model_calls, runner.calls, runner.writes_total, seconds))
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
        if session:
            try:
                session.__exit__(None, None, None)
            except Exception:
                pass
        meta['gazebo_close'] = demo.close()
        meta['ended'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        (out / 'SESSION.json').write_text(json.dumps(meta, indent=1, default=str), encoding='utf-8')
        say('Simulator closed. Bye.')


if __name__ == '__main__':
    main()
