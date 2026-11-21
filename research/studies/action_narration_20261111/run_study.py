"""Opt-in action-narration experiment; no production ROSA changes or answer maps."""
import argparse
import asyncio
from contextvars import ContextVar
import hashlib
import importlib.metadata
import importlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
import uuid

# ROS CLI helpers need distro modules such as psutil. Append as a fallback so
# older system typing_extensions cannot shadow the pinned venv dependencies.
sys.path.append('/usr/lib/python3/dist-packages')

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_ollama import ChatOllama
from rosa.prompts import system_prompts
from rosa.tools import ros2

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if p.name == 'research').parent
READS = ('ros2_node_list', 'ros2_node_info', 'ros2_topic_list', 'ros2_topic_info',
         'ros2_service_list', 'ros2_service_info', 'ros2_param_list', 'ros2_param_get')
TOOL_ID = ContextVar('tool_id', default=None)
ACTIVATION = dict(id='activation', request='Development transport check: in one response, call ros2_node_info with nodes ["/diag_demo/source", "/diag_demo/listener"] and independently call ros2_topic_info with topics ["/diag_demo/chatter"]. After results, report both node names and topic type. This checks tool transport only.')


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, default=str) + '\n')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class Journal:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        self.failed = {}
        self.inflight = {}
        self.native_count = 0

    def add(self, kind, **data):
        with self.lock:
            with self.path.open('a') as handle:
                handle.write(json.dumps(dict(kind=kind, monotonic=time.perf_counter(),
                                             tool_id=TOOL_ID.get(), **data), default=str) + '\n')


def native_guard(journal):
    """Shape-checked CLI reads; no arbitrary service calls or shell execution."""
    shapes = {('node', 'list'): (3,), ('node', 'info'): (4,),
              ('topic', 'list'): (3,), ('topic', 'info'): (5,),
              ('service', 'list'): (3,), ('service', 'type'): (4,),
              ('param', 'list'): (3, 4), ('param', 'get'): (5,)}

    def execute(command):
        argv = shlex.split(command)
        valid = (len(argv) >= 3 and argv[0] == 'ros2'
                 and len(argv) in shapes.get(tuple(argv[1:3]), ())
                 and all(re.fullmatch(r'[A-Za-z0-9_./]+', x) for x in argv[:4]))
        if tuple(argv[1:3]) == ('topic', 'info'):
            valid = valid and argv[-1] == '--verbose'
        elif len(argv) == 5:
            valid = valid and bool(re.fullmatch(r'[A-Za-z0-9_.]+', argv[-1]))
        if not valid:
            journal.add('guard_rejection', command=command)
            return False, 'Read-only study: invalid command shape.'
        key = tuple(argv)
        with journal.lock:
            exhausted = journal.failed.get(key, 0) + journal.inflight.get(key, 0) >= 2 or journal.native_count >= 64
            if not exhausted:
                journal.native_count += 1
                journal.inflight[key] = journal.inflight.get(key, 0) + 1
        if exhausted:
            journal.add('budget_rejection', command=argv)
            return False, 'Read budget exhausted; report the limitation.'
        request_id = str(uuid.uuid4())
        journal.add('ros_start', command=argv, request_id=request_id)
        started = time.perf_counter()
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=12)
            result = dict(returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
        except subprocess.TimeoutExpired as error:
            result = dict(returncode=None, stdout=str(error.stdout or ''),
                          stderr=str(error.stderr or ''), timeout=True)
        journal.add('ros_end', command=argv, request_id=request_id,
                    seconds=time.perf_counter()-started, **result)
        ok = result['returncode'] == 0
        with journal.lock:
            journal.inflight[key] -= 1
            if not ok:
                journal.failed[key] = journal.failed.get(key, 0) + 1
        return ok, result['stdout'] if ok else result['stderr'] or 'Native read failed or timed out.'
    return execute


def make_tools(journal):
    ros2.execute_ros_command = native_guard(journal)
    tools = []
    for name in READS:
        original = getattr(ros2, name)
        copied = original.model_copy()
        def wrapped(_original=original, **arguments):
            identity = str(uuid.uuid4())
            token = TOOL_ID.set(identity)
            journal.add('tool_start', name=_original.name, arguments=arguments)
            try:
                output = _original.func(**arguments)
                journal.add('tool_end', name=_original.name, output=output)
                return output
            except Exception as error:
                journal.add('tool_error', name=_original.name, error=repr(error))
                return {'error': str(error)}
            finally:
                TOOL_ID.reset(token)
        copied.func = wrapped
        copied.handle_validation_error = 'Invalid arguments. Read the schema and repair once, or report unavailable.'
        tools.append(copied)
    return tools


def prompts(arm, protocol):
    # Copy, do not mutate the ROSA module-global list. Replace its complete block.
    base = [(role, text) for role, text in system_prompts
            if 'CRITICAL - SEQUENTIAL TOOL EXECUTION:' not in text]
    assert len(system_prompts) - len(base) == 1
    base += [('system', protocol['common_instruction'])]
    if arm != 'A':
        base += [('system', protocol['arm_instructions'][arm])]
    assert not any('Do not batch tool calls' in text for _, text in base)
    return base


class MeasuredModel(BaseChatModel):
    underlying: object
    journal: object

    @property
    def _llm_type(self):
        return 'action-narration-measurement'

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        schemas = kwargs.pop('tools')
        serial_start = time.perf_counter()
        envelope = self.underlying._chat_params(messages, stop=stop, tools=schemas)
        serialization_seconds = time.perf_counter()-serial_start
        self.journal.add('model_start', messages=[m.model_dump() for m in messages],
                         schemas=schemas, schema_hash=digest(schemas),
                         envelope=envelope, serialization_seconds=serialization_seconds)
        started = time.perf_counter()
        try:
            answer = self.underlying.bind_tools(schemas).invoke(messages, stop=stop)
        except Exception as error:
            self.journal.add('model_error', seconds=time.perf_counter()-started, error=repr(error))
            raise
        self.journal.add('model_end', seconds=time.perf_counter()-started,
                         message=answer.model_dump(), usage=answer.usage_metadata,
                         metadata=answer.response_metadata)
        return ChatResult(generations=[ChatGeneration(message=answer)])


async def episode(destination, arm, task, protocol):
    destination.mkdir(exist_ok=False)
    journal = Journal(destination/'trace.jsonl')
    journal.add('episode_start', arm=arm, task=task)
    model = ChatOllama(**protocol['model'], client_kwargs={'timeout': 90})
    tools = make_tools(journal)
    schemas = [convert_to_openai_tool(t) for t in tools]
    prompt = ChatPromptTemplate.from_messages(prompts(arm, protocol) + [
        ('human', '{input}'), MessagesPlaceholder('agent_scratchpad')])
    agent = create_tool_calling_agent(MeasuredModel(underlying=model, journal=journal), tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, stream_runnable=False,
                             max_iterations=3 if task['id']=='activation' else 10,
                             handle_parsing_errors=True, return_intermediate_steps=True)
    save(destination/'configuration.json', dict(arm=arm, model=protocol['model'],
         prompts=prompts(arm, protocol), schemas=schemas, schema_hash=digest(schemas)))
    started = time.perf_counter()
    try:
        result = await executor.ainvoke({'input': task['request']})
        save(destination/'intermediate_steps.json', [dict(action=a.model_dump(), observation=o)
             for a,o in result['intermediate_steps']])
        answer, error = result['output'], None
    except Exception as failure:
        answer, error = None, repr(failure)
    journal.add('episode_end', answer=answer, error=error, seconds=time.perf_counter()-started)
    save(destination/'answer.json', dict(task=task['id'], arm=arm, answer=answer, error=error))


def snapshot(destination):
    """Evaluation-only native observations, never passed into episode()."""
    commands = {'nodes': ['node', 'list', '--no-daemon', '--spin-time', '3'],
                'topics': ['topic', 'list'], 'services': ['service', 'list']}
    for n in ['/diag_turtle/palette', '/diag_demo/source', '/diag_demo/listener', '/diag_demo/calculator']:
        commands[n+':info'] = ['node', 'info', n]
        commands[n+':params'] = ['param', 'dump', n]
    for t in ['/diag_turtle/turtle1/pose', '/diag_turtle/turtle1/cmd_vel',
              '/diag_turtle/turtle1/color_sensor', '/diag_demo/chatter']:
        commands[t+':info'] = ['topic', 'info', t, '--verbose']
    commands['stale_node'] = ['node', 'info', '/diag_demo/retired_source']
    result = {}
    for key, argv in commands.items():
        started = time.perf_counter()
        p = subprocess.run(['ros2', *argv], capture_output=True, text=True, timeout=20)
        result[key] = dict(command=['ros2', *argv], returncode=p.returncode,
                           stdout=p.stdout, stderr=p.stderr, seconds=time.perf_counter()-started)
    save(destination, result)
    assert all(v['returncode'] == 0 for k, v in result.items() if k != 'stale_node')
    assert result['stale_node']['returncode'] != 0
    assert all(n in result['nodes']['stdout'].splitlines() for n in
               ['/diag_turtle/palette', '/diag_demo/source', '/diag_demo/listener', '/diag_demo/calculator'])


def freeze(out):
    source = out/'source'
    for relative in ['src/rosa', 'research/studies/action_narration_20261111',
                     'research/studies/native_read_investigation_20261111/evidence/source_snapshot']:
        shutil.copytree(ROOT/relative, source/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['AGENTS.md', 'pyproject.toml', 'uv.lock', 'research/ROSA_RESEARCH_CONTEXT.md']:
        target = source/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/relative, target)
    # Installed invocation/execution sources, before inference (not whole environment).
    import inspect
    for name in ['langchain.agents.agent', 'langchain_ollama.chat_models', 'ollama._client']:
        module = importlib.import_module(name)
        p = Path(inspect.getfile(module))
        shutil.copy2(p, source/(module.__name__+'.py'))
    save(out/'freeze.json', dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
         sha256={str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source.rglob('*') if p.is_file()}))


def run(out, protocol, activation_only=False):
    assert os.environ.get('ROS_DOMAIN_ID') == '174' and os.environ.get('ROS_LOCALHOST_ONLY') == '1'
    out.mkdir(parents=True, exist_ok=False)
    freeze(out)
    journal = Journal(out/'setup.jsonl')
    save(out/'identity.json', dict(head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
         branch=subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
         status=subprocess.check_output(['git', 'status', '--short'], text=True), python=sys.version,
         environment={k:os.environ.get(k) for k in ['ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY','ROS_DISTRO','RMW_IMPLEMENTATION']},
         versions={n:importlib.metadata.version(n) for n in
                   ['jpl-rosa','rosa-llm','langchain','langchain-core','langchain-ollama','ollama']},
         activation_only=activation_only))
    for endpoint in ['tags', 'version']:
        with urllib.request.urlopen(protocol['model']['base_url']+'/api/'+endpoint, timeout=10) as response:
            save(out/('ollama-'+endpoint+'.json'), json.load(response))
    tags = json.loads((out/'ollama-tags.json').read_text())
    assert any(m['name']==protocol['model']['model'] and m['digest']==protocol['model_digest']
               for m in tags['models']), 'Frozen checkpoint unavailable'
    commands = [
        ['ros2','run','turtlesim','turtlesim_node','--ros-args','-r','__ns:=/diag_turtle','-r','__node:=palette',
         '-p','background_r:=37','-p','background_g:=83','-p','background_b:=129'],
        ['ros2','run','demo_nodes_cpp','talker','--ros-args','-r','__ns:=/diag_demo','-r','__node:=source'],
        ['ros2','run','demo_nodes_cpp','listener','--ros-args','-r','__ns:=/diag_demo','-r','__node:=listener'],
        ['ros2','run','demo_nodes_cpp','add_two_ints_server','--ros-args','-r','__ns:=/diag_demo','-r','__node:=calculator']]
    processes, handles = [], []
    try:
        p = subprocess.run(['ros2','node','list','--no-daemon','--spin-time','2'], capture_output=True, text=True, timeout=15)
        journal.add('collision_check', stdout=p.stdout, stderr=p.stderr, returncode=p.returncode)
        assert p.returncode == 0 and not p.stdout.strip(), 'Domain must be empty'
        for index, command in enumerate(commands):
            handle = (out/f'fixture-{index}.log').open('w')
            handles.append(handle)
            p = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True,
                                 env=dict(os.environ, QT_QPA_PLATFORM='offscreen'))
            processes.append(p)
            journal.add('fixture_start', command=command, pid=p.pid)
        time.sleep(5)
        snapshot(out/'oracle-before.json')
        if activation_only:
            # Same prompts/model/schemas; known args are explicitly user-authorized here.
            for arm in 'ABC':
                command = [sys.executable, str(HERE/'run_study.py'), '--episode',
                           '--output', str(out/('activation-'+arm)), '--arm', arm, '--task', 'activation']
                with (out/('activation-'+arm+'.log')).open('w') as handle:
                    p = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
                    try: code = p.wait(timeout=240)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGKILL)
                        p.wait()
                        journal.add('activation_timeout', arm=arm)
                        raise RuntimeError('Activation timeout')
                assert code == 0, 'Activation worker failed'
                events = [json.loads(line) for line in (out/('activation-'+arm)/'trace.jsonl').read_text().splitlines()]
                responses = [e for e in events if e['kind']=='model_end']
                assert responses and not responses[-1]['message'].get('tool_calls'), 'No final answer'
                assert any(len(e['message'].get('tool_calls',[])) >= 2 for e in responses), 'Independent multicall not activated'
                assert any(e['kind']=='tool_start' and e['name']=='ros2_node_info' and len(e['arguments'].get('nodes',[]))==2 for e in events), 'List args not activated'
                assert sum(e['kind']=='ros_end' and e['returncode']==0 for e in events) >= 3, 'Native reads failed'
                journal.add('activation_passed', arm=arm)
        else:
            schedule = [(t['id'], a) for t in protocol['tasks'] for a in 'ABC']
            random.Random(20261111).shuffle(schedule)
            save(out/'schedule.json', schedule)
            started = time.perf_counter()
            for index, (task_id, arm) in enumerate(schedule):
                if time.perf_counter()-started > 2400:
                    journal.add('study_budget_stop', unattempted=len(schedule)-index)
                    break
                assert all(p.poll() is None for p in processes), 'Fixture exited'
                task = next(t for t in protocol['tasks'] if t['id'] == task_id)
                destination = out/f'{index:02d}-{task_id}-{arm}'
                command = [sys.executable, str(HERE/'run_study.py'), '--episode', '--output', str(destination),
                           '--arm', arm, '--task', task_id]
                journal.add('episode_launch', index=index, command=command)
                with (out/f'worker-{index:02d}.log').open('w') as handle:
                    p = subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        code = p.wait(timeout=240)
                    except subprocess.TimeoutExpired:
                        os.killpg(p.pid, signal.SIGTERM)
                        try: p.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(p.pid, signal.SIGKILL)
                            p.wait()
                        code = p.returncode
                        journal.add('episode_timeout', index=index)
                journal.add('episode_process_end', index=index, returncode=code)
                print(json.dumps(dict(index=index, task=task_id, arm=arm, returncode=code)), flush=True)
                if (index+1) % 3 == 0:
                    snapshot(out/f'oracle-after-{index+1:02d}.json')
        snapshot(out/'oracle-after.json')
    except Exception as error:
        journal.add('study_error', error=repr(error))
        raise
    finally:
        for p in processes:
            if p.poll() is None:
                os.killpg(p.pid, signal.SIGINT)
                try: p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid, signal.SIGKILL)
                    p.wait()
            journal.add('fixture_stop', pid=p.pid, returncode=p.returncode)
        for handle in handles: handle.close()
        p = subprocess.run(['ros2','daemon','stop'], capture_output=True, text=True, timeout=15)
        journal.add('daemon_stop', stdout=p.stdout, stderr=p.stderr, returncode=p.returncode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--activation-only', action='store_true')
    parser.add_argument('--episode', action='store_true')
    parser.add_argument('--arm', choices=list('ABC'))
    parser.add_argument('--task')
    args = parser.parse_args()
    protocol = json.loads((HERE/'cases.json').read_text())
    if args.episode:
        task = ACTIVATION if args.task == 'activation' else next(t for t in protocol['tasks'] if t['id'] == args.task)
        asyncio.run(episode(args.output, args.arm, task, protocol))
    else:
        run(args.output, protocol, args.activation_only)
