"""Two-arm live runner for the merged-method demo (lab and laptop). ADAPTATION FILE (ours); his files are used byte for byte (his_m.verify before use).
LABEL: merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated, not for the paper. Nothing here is an evaluation.

Arms: (a) M + bounded macro `run_skill` (frozen demo configuration), (b) M + primitives (arm b files, separate). Same his A1 prompt, tools menu, settings and guards.
Cases: D1-D3 (tasks.json) + the 6 D2 DEV cases (d2_dev_cases.json, dev split only; the held-out split is never opened).
One run per case per arm per model; arm order alternates by case index (even index: macro first). One Gazebo per model session; the arm is reset to the case's start pose
before EVERY run and the reset is confirmed by an independent read-only observer; a failed confirmation means the run is NOT run. Injected faults (dev cases) are applied
after the reset and removed after the run. No per-model tuning of prompts, wording or tools.

Usage (inside the lab container or laptop WSL):
  python lab_runner.py <new output folder> --model qwen3.5:9b [--endpoint http://127.0.0.1:11449] [--num-ctx 65536] [--cases D1,D2,D3,dev] [--arms both]
  --model sol uses the existing remembered sign-in (laptop only)."""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault('ROS_DOMAIN_ID', '213')
os.environ.update(ROS_AUTOMATIC_DISCOVERY_RANGE='LOCALHOST', LANGCHAIN_TRACING='false', LANGCHAIN_TRACING_V2='false', LANGSMITH_TRACING='false')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, os.environ.get('ROSA_RESEARCH_SRC', '/work/merged-demo-20261128/rosa-research/src'))
from merged_demo import his_m, prompts  # noqa: E402
from merged_demo.events import EventLog  # noqa: E402
from merged_demo.his_m_primitives import make_primitive_arm_class  # noqa: E402
from merged_demo.primitives_tool import PrimitiveRunner  # noqa: E402
from merged_demo.skill_tool import SkillRunner, ur5e_registry  # noqa: E402

LABEL = 'merged method (Levinson M + Martin bounded macro), demonstration only, not evaluated, not for the paper'
TOL = 0.025
JOINT_TOL = 0.05
SUCCESS_KEYS = ('ready', 'readiness', 'success', 'reached', 'goal_reached', 'verified', 'confirmed', 'moved', 'completed')


def write(path, obj):
    Path(path).write_text(json.dumps(obj, indent=1, sort_keys=True, default=str), encoding='utf-8')


def load_cases():
    tasks = prompts.load_tasks()['tasks']
    cases = [{'id': t['id'], 'text': t['text'], 'initial': t['initial'], 'fault': None, 'kind': 'demo', 'family': t['id']} for t in tasks]
    for t in tasks:
        c = next(x for x in cases if x['id'] == t['id'])
        c.update(skill={'D1': None, 'D2': 'ur5e.park_right', 'D3': 'ur5e.stage_left'}[t['id']], writes=0 if t['id'] == 'D1' else 1, expected='SUCCESS')
    dev = json.loads((HERE / 'd2_dev_cases.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((HERE / 'd2_dev_cases.json').read_bytes()).hexdigest().startswith('0f0348e027e9618f') and all(d['split'] == 'dev' for d in dev)
    for d in dev:
        cases.append({'id': d['id'], 'text': d['request'], 'initial': d['initial'], 'fault': d['fault'], 'kind': d['kind'], 'family': d['family'],
                      'skill': d['skill'], 'writes': d['writes'], 'expected': d['expected']})
    return cases


# ------------------------------------------------------------------ expected path and support (scripted, labelled heuristics; raw answers are kept)
def milestones(case, arm):
    s, k = case['skill'], case['kind']
    if case['id'] == 'D1':
        return ['ros2_topic_info', 'ros2_topic_echo', 'final']
    if k == 'clarification':
        return []
    if k == 'inspection':
        return ['run_skill:ur5e.inspect_readiness' if arm == 'macro' else 'read_readiness', 'final']
    if case['id'] == 'D2':
        return (['run_skill:ur5e.inspect_readiness', 'run_skill:' + s] if arm == 'macro' else ['read_readiness', 'read_pose', 'write_pose:' + s]) + ['final']
    if case['writes'] == 0:                                  # missing prerequisite: no motion allowed
        return ['final']
    return (['run_skill:' + s] if arm == 'macro' else ['read_pose', 'write_pose:' + s]) + ['final']


def path_tokens(rows):
    out = []
    for r in rows:
        kind = r['kind']
        if kind == 'macro_skill_call_end' and r.get('outcome') != 'REJECTED_BEFORE_ANY_IO':
            out.append('run_skill:' + str(r.get('skill_id')))
        elif kind == 'macro_primitive_call_end' and r.get('outcome') != 'REJECTED_BEFORE_ANY_IO':
            out.append(r['tool'] + (':' + r['skill_id'] if r.get('skill_id') and r['tool'] in ('write_pose', 'verify_pose') else ''))
        elif kind == 'tool_start' and r.get('name') not in ('run_skill', 'read_pose', 'read_readiness', 'write_pose', 'verify_pose', 'final_answer'):
            out.append(r['name'])
        elif kind == 'final_answer_accepted':
            out.append('final')
    return out


def is_subsequence(needed, seen):
    it = iter(seen)
    return all(any(x == y for y in it) for x in needed)


def numeric_claims(answer):
    found = {}
    def walk(value, key=''):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, str(k))
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            found[key] = float(value)
    walk(answer)
    return found


def supported(case, answer_text, final_obs, writes, arm_tools_used, target):
    """Scripted heuristic: the answer must not contradict the independent final state. Returns (bool or None, reason)."""
    if case['kind'] == 'clarification':
        return (writes == 0 and not arm_tools_used), 'no write and no arm tool before asking'
    try:
        answer = json.loads(answer_text) if answer_text else None
    except ValueError:
        answer = None
    if not isinstance(answer, dict):
        return False, 'no JSON object answer'
    claims_success = any(isinstance(v, bool) and v is True and any(s in str(k).lower() for s in SUCCESS_KEYS) for k, v in answer.items())
    for k, v in numeric_claims(answer).items():
        for joint, value in final_obs.items():
            if joint in k or (k in ('shoulder_pan', 'wrist_3') and joint.startswith(k)):
                if abs(value - v) > JOINT_TOL:
                    return False, 'number %s=%s differs from the independent final reading %.3f' % (k, v, value)
    if case['id'] == 'D1':
        text = json.dumps(answer)
        return ('joint_state_broadcaster' in text), 'publisher named and numbers consistent'
    if case['expected'] == 'SUCCESS' and case['writes'] >= 1:
        at_target = all(abs(final_obs[j] - v) <= TOL for j, v in target.items())
        return at_target, 'independent final pose at the registered target'
    if case['expected'] in ('FAILURE', 'UNKNOWN'):
        return (not claims_success), 'answer does not claim success while the injected fault makes success impossible'
    return True, 'numbers consistent'


# ------------------------------------------------------------------ fault helpers (outside the task, never model-visible; copied pattern of the M2 runner)
class MissingSource:
    def __init__(self, inner, source):
        self.inner, self.source = inner, source

    def read_group(self, source, names):
        if source == self.source:
            raise TimeoutError('engineering_injected_source_unavailable')
        return self.inner.read_group(source, names)


def switch_trajectory(inspection, active):
    from controller_manager_msgs.srv import SwitchController
    client = inspection.observer.node.create_client(SwitchController, '/controller_manager/switch_controller')
    if not client.wait_for_service(timeout_sec=5):
        raise TimeoutError('switch_controller_setup_unavailable')
    request = SwitchController.Request()
    request.activate_controllers = ['joint_trajectory_controller'] if active else []
    request.deactivate_controllers = [] if active else ['joint_trajectory_controller']
    request.strictness = SwitchController.Request.STRICT
    request.activate_asap = True
    request.timeout.sec = 5
    future = client.call_async(request)
    deadline = time.monotonic() + 10
    while not future.done() and time.monotonic() < deadline:
        inspection.observer.executor.spin_once(timeout_sec=0.05)
    if not future.done() or not future.result().ok:
        raise RuntimeError('switch_controller_failed')


def make_chat(args, meta):
    kwargs = dict(model=args.model, base_url=args.endpoint, num_ctx=args.num_ctx, num_predict=4096, temperature=0, seed=42, use_mmap=True, streaming=False,
                  reasoning=False, cache=False, client_kwargs={'timeout': 180})
    if args.model.partition(':')[0] == 'llama3.1':
        from rosa_backends.tool_contract_ollama import ToolContractOllama, PROFILE_VERSION
        meta['profile'] = PROFILE_VERSION
        return ToolContractOllama(**kwargs)
    from rosa_backends.chat_ollama import ConfiguredChatOllama
    return ConfiguredChatOllama(**kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output')
    ap.add_argument('--model', required=True)
    ap.add_argument('--endpoint', default='http://127.0.0.1:11449')
    ap.add_argument('--num-ctx', type=int, default=65536)
    ap.add_argument('--cases', default='D1,D2,D3,dev')
    ap.add_argument('--arms', default='both', choices=('both', 'macro', 'primitives'))
    ap.add_argument('--machine', default='lab')
    ap.add_argument('--stop-epoch', type=float, default=None, help='do not START a run after this unix time')
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    h = his_m.load()                                                 # verifies all 26 files byte for byte first
    from rosa_reliability.gazebo_demo import GazeboDemo
    from rosa_reliability.ros_arm import ArmTransport, JOINTS
    from rosa_reliability.ros_readiness import ArmReadinessTransport
    registry = ur5e_registry()
    wanted = []
    for token in args.cases.split(','):
        wanted += [c['id'] for c in load_cases() if (c['id'] == token or (token == 'dev' and c['id'].startswith('D-dev')))]
    cases = [c for c in load_cases() if c['id'] in wanted]
    macro_freeze = json.loads((HERE / 'FREEZE_DEMO_MERGED.json').read_text())
    prim_freeze = json.loads((HERE / 'FREEZE_DEMO_PRIMITIVES.json').read_text())
    meta = {'label': LABEL, 'machine': args.machine, 'model': args.model, 'endpoint': args.endpoint, 'ros_domain_id': os.environ['ROS_DOMAIN_ID'],
            'settings': {'num_ctx': args.num_ctx, 'num_predict': 4096, 'temperature': 0, 'seed': 42, 'use_mmap': True, 'reasoning': False, 'max_iterations': h['run_pilot'].MAX_ITERATIONS},
            'arm_a_freeze': {'prompt': macro_freeze['prompt_sha256_his_function'], 'tool_set': macro_freeze['tool_set_sha256']},
            'arm_b_freeze': {'prompt': prim_freeze['prompt_sha256_his_function'], 'tool_set': prim_freeze['tool_set_sha256']},
            'his_commit': his_m.COMMIT, 'runs': [], 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'held_out_cases_opened': False}
    if args.num_ctx != 65536:
        meta['deviation'] = 'num_ctx %d instead of his 65536, applied to BOTH arms' % args.num_ctx
    write(out / 'RUN_META.json', meta)
    demo = GazeboDemo(out / 'gazebo')
    movement = inspection = observer = chat = session = None
    consecutive_errors = 0
    try:
        demo.start()
        movement, inspection, observer = ArmTransport(), ArmReadinessTransport(), ArmTransport(read_only=True)
        if args.model == 'sol':
            from rosa_auth.remembered import remembered_session
            from rosa_auth.responses import SiwcBackend
            from rosa_backends.chat_siwc import ChatSiwc
            session = remembered_session(request_budget=400, status={})
            auth = session.__enter__()
            chat = ChatSiwc(model='gpt-6.1-sol', backend=SiwcBackend(request_budget=400, token_provider=auth.access_token))
        else:
            chat = make_chat(args, meta)
        for index, case in enumerate(cases):
            order = ['macro', 'primitives'] if index % 2 == 0 else ['primitives', 'macro']
            for arm_name in [a for a in order if args.arms in ('both', a)]:
                if args.stop_epoch and time.time() > args.stop_epoch:
                    meta['stopped_early'] = 'time window: no new run started after the stop time'
                    raise StopIteration
                if consecutive_errors >= 2:
                    meta['stopped_early'] = 'two consecutive crashes or harness errors'
                    raise StopIteration
                tag = '%s_%s' % (case['id'], arm_name)
                folder = out / tag
                folder.mkdir()
                record = {'case': case['id'], 'arm': arm_name, 'order_index': index, 'fault': case['fault'], 'reset_ok': False}
                meta['runs'].append(record)
                inactive = False
                try:
                    movement.suppress_commands = movement.partial_commands = movement.missing_observations = False
                    start_target = registry.catalogue()[case['initial']]['targets']['/ur5e']
                    movement.read('/ur5e', list(JOINTS))
                    movement.write('/ur5e', start_target)
                    seen = observer.read('/ur5e', list(JOINTS))
                    record['reset_observation'] = seen
                    record['reset_ok'] = all(abs(seen[k] - v) <= TOL for k, v in start_target.items())
                    if not record['reset_ok']:
                        record['status'] = 'RESET_FAILED_NOT_RUN'
                        write(out / 'RUN_META.json', meta)
                        continue
                    movement.partial_commands = case['fault'] == 'partial'
                    movement.missing_observations = case['fault'] == 'missing_motion'
                    if case['fault'] == 'inactive':
                        switch_trajectory(inspection, False)
                        inactive = True
                    readiness = MissingSource(inspection, case['fault']) if case['fault'] in ('controllers', 'joint_state') else inspection
                    recorder = h['Recorder'](folder / 'trace.jsonl')
                    log = EventLog(sink=recorder)
                    transports = {'state': movement, 'inspection': readiness}
                    if arm_name == 'macro':
                        runner = SkillRunner(registry, transports, log)
                        arm = his_m.make_arm_class(h)(recorder, dict(env='merged_demo_lab', task={'id': case['id'], 'request': case['text'], 'floor': 0}, ns=''), runner)
                    else:
                        runner = PrimitiveRunner(registry, transports, log)
                        arm = make_primitive_arm_class(h)(recorder, dict(env='merged_demo_lab', task={'id': case['id'], 'request': case['text'], 'floor': 0}, ns=''), runner)
                    recorder.add('episode_start', label=LABEL, task=case['id'], arm=arm_name, request=case['text'], model=args.model, settings=meta['settings'],
                                 prompt_sha256=h['run_pilot'].prompt_hash(arm.prompt_messages), prompts=arm.prompt_messages, max_iterations=h['run_pilot'].MAX_ITERATIONS)
                    h['ros2'].execute_ros_command = sys.modules['menu_run_study'].guarded_native(recorder)
                    answer = error = None
                    started = time.perf_counter()
                    try:
                        model = h['run_pilot'].ArmTracedModel(holder={'model': chat}, recorder=recorder, options={}, arm=arm)
                        agent = h['run_pilot'].PilotROSA(model, arm)
                        result = agent._ROSA__executor.invoke({'input': case['text'], 'chat_history': []}, config={'callbacks': [h['ToolRecorder'](recorder)]})
                        answer = result['output']
                    except Exception as failure:
                        error = repr(failure)
                    finally:
                        arm.close()
                    seconds = round(time.perf_counter() - started, 1)
                    recorder.add('episode_end', answer=answer, error=error, seconds=seconds)
                    movement.partial_commands = movement.missing_observations = False
                    final = observer.read('/ur5e', list(JOINTS))
                    rows = recorder.rows
                    tokens = path_tokens(rows)
                    usage = [r.get('usage') or {} for r in rows if r['kind'] == 'model_end']
                    arm_tools = [t for t in tokens if t.split(':')[0] in ('run_skill', 'read_pose', 'read_readiness', 'write_pose', 'verify_pose')]
                    need = milestones(case, arm_name)
                    reached = is_subsequence(need, tokens) and runner.writes_total == case['writes'] and (case['kind'] != 'clarification' or not arm_tools)
                    if case['kind'] == 'clarification':
                        reached = runner.writes_total == 0 and not arm_tools
                    target = (registry.catalogue()[case['skill']]['targets']['/ur5e'] if case['skill'] and case['kind'] == 'movement' or case['id'] in ('D2', 'D3') else {})
                    ok, why = supported(case, answer, final, runner.writes_total, arm_tools, target)
                    record.update(status='COMPLETE' if (answer or not error) else 'ERROR', answer=answer, error=error, path=tokens, expected_path=need,
                                  expected_path_reached=reached, supported=ok, supported_reason=why, final_independent_observation=final,
                                  model_calls=len(usage), input_tokens=sum(u.get('input_tokens', 0) for u in usage), output_tokens=sum(u.get('output_tokens', 0) for u in usage),
                                  arm_transport_ops=len(log.of('internal_read', 'internal_write')), menu_tool_calls=sum(1 for t in tokens if t not in ('final',) and t.split(':')[0] not in
                                  ('run_skill', 'read_pose', 'read_readiness', 'write_pose', 'verify_pose')), writes=runner.writes_total,
                                  ending=('final_answer' if answer else 'error' if error else 'no_final_answer'), seconds=seconds)
                    consecutive_errors = consecutive_errors + 1 if error else 0
                    write(folder / 'answer.json', record)
                except StopIteration:
                    raise
                except Exception as failure:
                    record.update(status='HARNESS_ERROR', error=repr(failure))
                    consecutive_errors += 1
                finally:
                    if inactive:
                        try:
                            switch_trajectory(inspection, True)
                        except Exception as failure:
                            record['fault_cleanup_error'] = repr(failure)
                    write(out / 'RUN_META.json', meta)
                print(tag, record.get('status'), 'reached', record.get('expected_path_reached'), 'supported', record.get('supported'), 'calls', record.get('model_calls'),
                      'writes', record.get('writes'), flush=True)
    except StopIteration:
        pass
    finally:
        for item in (chat, movement, inspection, observer):
            try:
                if item is not None and hasattr(item, 'close'):
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
