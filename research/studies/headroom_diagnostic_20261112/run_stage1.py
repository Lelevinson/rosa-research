"""Stage 1 harness (frozen by PROTOCOL_STAGE1.md): 1a paired prompt fix, 1b width probe.

Run with:  uv run python run_stage1.py <command> ...   (from the repository root)
Commands:  check            offline checks, no inference, no fixture
           stage1a OUT      24 local episodes
           stage1b OUT      width probe, both models (OUT is a NEW directory)
           episode ...      one worker episode (spawned by the stage commands)

ROSA source is not edited: the prompt override lives in StageROSA._get_prompts.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if p.name == 'research').parent
sys.path.insert(0, str(HERE / 'vendor'))
from menu_run_study import Recorder, ToolRecorder, guarded_native, save  # noqa: E402  (vendored baseline helpers)

from langchain_core.language_models import BaseChatModel  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder  # noqa: E402
from langchain_core.utils.function_calling import convert_to_openai_tool  # noqa: E402
from rosa.prompts import system_prompts  # noqa: E402
from rosa.rosa import ROSA  # noqa: E402
from rosa.tools import ros2  # noqa: E402

# Ollama address: ROSA_OLLAMA_URL if set (lab container), else the laptop default.
OLLAMA = os.environ.get('ROSA_OLLAMA_URL', 'http://172.30.80.1:11434')
QWEN = 'qwen3.5:9b'
LUNA = 'gpt-6-luna'
SEQUENTIAL_MARK = 'CRITICAL - SEQUENTIAL TOOL EXECUTION:'
PERMISSION = ('system', 'Independent tool calls whose arguments are already known may be made together in one response.')
TASK_1B = ('For every running node under /scale, report its configured use_sim_time. '
           'Return JSON with key clocks (an object mapping each full node name to a boolean).')
FIXTURE_1A = [
    ['ros2', 'run', 'turtlesim', 'turtlesim_node', '--ros-args', '-r', '__ns:=/diag_turtle', '-r', '__node:=palette',
     '-p', 'background_r:=37', '-p', 'background_g:=83', '-p', 'background_b:=129'],
    ['ros2', 'run', 'demo_nodes_cpp', 'talker', '--ros-args', '-r', '__ns:=/diag_demo', '-r', '__node:=source'],
    ['ros2', 'run', 'demo_nodes_cpp', 'listener', '--ros-args', '-r', '__ns:=/diag_demo', '-r', '__node:=listener'],
    ['ros2', 'run', 'demo_nodes_cpp', 'add_two_ints_server', '--ros-args', '-r', '__ns:=/diag_demo', '-r', '__node:=calculator']]
NODES_1A = ['/diag_turtle/palette', '/diag_demo/source', '/diag_demo/listener', '/diag_demo/calculator']
BASELINE = json.loads((HERE / 'vendor/baseline_protocol.json').read_text())


def prompt_messages(arm):
    """The exact system messages of an arm. A_orig is ROSA's list unchanged; A0 replaces one message in place."""
    messages = [(role, text) for role, text in system_prompts]
    if arm == 'A0':
        hits = [i for i, (_, text) in enumerate(messages) if SEQUENTIAL_MARK in text]
        assert len(hits) == 1, 'expected exactly one sequential-execution message'
        messages[hits[0]] = PERMISSION
        assert not any('Do not batch tool calls' in text or 'NEVER call multiple tools' in text for _, text in messages)
    else:
        assert arm == 'A_orig' and any('Do not batch tool calls' in text for _, text in messages)
    return messages


def prompt_hash(arm):
    return hashlib.sha256(json.dumps(prompt_messages(arm)).encode()).hexdigest()


class StageROSA(ROSA):
    """Stock ROSA with only the system-prompt list replaced (runtime override)."""
    def __init__(self, llm, arm, max_iterations):
        self.study_arm = arm
        super().__init__(ros_version=2, llm=llm, streaming=False, verbose=False,
                         max_iterations=max_iterations, accumulate_chat_history=False)

    def _get_prompts(self, robot_prompts=None):
        return ChatPromptTemplate.from_messages(prompt_messages(self.study_arm) + [
            MessagesPlaceholder('chat_history'), ('human', '{input}'), MessagesPlaceholder('agent_scratchpad')])


class TracedModel(BaseChatModel):
    """Records every request/response; the underlying chat model is built on first use."""
    holder: dict
    recorder: object
    options: dict

    @property
    def _llm_type(self):
        return 'stage1-traced'

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        schemas = kwargs.pop('tools', [])
        self.recorder.add('model_start', messages=[m.model_dump() for m in messages], schemas=schemas, options=self.options)
        started = time.perf_counter()
        try:
            answer = self.holder['model'].bind_tools(schemas).invoke(messages, stop=stop, **self.options)
        except Exception as error:
            detail = error.to_dict() if hasattr(error, 'to_dict') else {'type': type(error).__name__, 'message': str(error)}
            self.recorder.add('model_error', error=detail, seconds=time.perf_counter() - started)
            raise
        self.recorder.add('model_end', message=answer.model_dump(), usage=answer.usage_metadata,
                          response_metadata=answer.response_metadata, seconds=time.perf_counter() - started)
        return ChatResult(generations=[ChatGeneration(message=answer)])


def build_model(provider, stage, recorder, client_stack):
    if provider == 'ollama':
        from langchain_ollama import ChatOllama
        return ChatOllama(model=QWEN, base_url=OLLAMA, temperature=0, seed=42, reasoning=False,
                          num_predict=8192 if stage == '1b' else 1600, num_ctx=65536,
                          client_kwargs={'timeout': 90}), {}
    from dataclasses import replace
    from rosa_llm import Config, create_client
    from rosa_llm.langchain import ChatRosaLLM
    config = replace(Config.load(), provider='openai', openai_model=LUNA, require_explicit_model=True, timeout=90)
    client = client_stack.enter_context(create_client(
        config, observer=lambda record: recorder.add('provider_record', record=record)))
    return ChatRosaLLM(client=client, allowed_tools=None, cache=False), {'parallel_tool_calls': True}


def episode(args):
    import contextlib
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out / 'trace.jsonl')
    if args.stage == '1a':
        task = next(t for t in BASELINE['tasks'] if t['id'] == args.task)
        request, max_iterations = task['request'], BASELINE['budgets']['max_iterations']
    else:
        task = dict(id='scale%d' % args.n, n=args.n)
        request, max_iterations = TASK_1B, 40
    recorder.add('episode_start', task=task, arm=args.arm, repeat=args.repeat, provider=args.provider, stage=args.stage,
                 prompt_sha256=prompt_hash(args.arm), prompts=prompt_messages(args.arm))
    ros2.execute_ros_command = guarded_native(recorder)
    answer = error = None
    started = time.perf_counter()
    with contextlib.ExitStack() as stack:
        try:
            base, options = build_model(args.provider, args.stage, recorder, stack)
            model = TracedModel(holder={'model': base}, recorder=recorder, options=options)
            agent = StageROSA(model, args.arm, max_iterations)
            recorder.add('effective_request', request=request)
            result = agent._ROSA__executor.invoke({'input': request, 'chat_history': []},
                                                  config={'callbacks': [ToolRecorder(recorder)]})
            answer = result['output']
        except Exception as failure:
            error = repr(failure)
    recorder.add('episode_end', answer=answer, error=error, seconds=time.perf_counter() - started)
    save(out / 'answer.json', dict(task=task['id'], arm=args.arm, repeat=args.repeat, provider=args.provider,
                                   answer=answer, error=error))


# ---------------------------------------------------------------- fixture and oracle
def start_processes(commands, out, tag, recorder):
    processes, handles = [], []
    for index, command in enumerate(commands):
        handle = (out / f'{tag}-fixture-{index:02d}.log').open('w')
        handles.append(handle)
        recorder.add('fixture_start', command=command)
        processes.append(subprocess.Popen(command, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True,
                                          env=dict(os.environ, QT_QPA_PLATFORM='offscreen')))
    return processes, handles


def stop_processes(processes, handles, recorder):
    for p in processes:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
    for p in processes:
        try:
            p.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
    for handle in handles:
        handle.close()
    recorder.add('fixture_stopped', returncodes=[p.returncode for p in processes])


def node_list():
    p = subprocess.run(['ros2', 'node', 'list', '--no-daemon', '--spin-time', '3'], capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.splitlines(), p.stderr


def wait_for(expected, recorder, attempts=8):
    for attempt in range(attempts):
        code, names, err = node_list()
        recorder.add('readiness', attempt=attempt, returncode=code, nodes=names, stderr=err)
        if code == 0 and set(expected) <= set(names):
            return True
        time.sleep(2)
    return False


def assert_domain_empty(prefixes, recorder):
    code, names, err = node_list()
    recorder.add('preexisting_domain', returncode=code, nodes=names, stderr=err)
    if code != 0 or any(n.startswith(prefixes) for n in names):
        raise RuntimeError('Domain not empty or unreadable; refusing to start')


def verify_empty(prefixes, recorder):
    code, names, err = node_list()
    left = [n for n in names if n.startswith(prefixes)]
    recorder.add('cleanup_check', returncode=code, remaining=left, stderr=err)
    return code == 0 and not left


def stop_daemon(recorder):
    p = subprocess.run(['ros2', 'daemon', 'stop'], capture_output=True, text=True, timeout=30)
    recorder.add('daemon_stop', returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)


def ollama_active_context(out, name):
    with urllib.request.urlopen(OLLAMA + '/api/ps', timeout=10) as response:
        active = json.load(response)
    save(out / name, active)
    return active


def check_context(out, name, recorder):
    active = ollama_active_context(out, name)
    ok = any(m['name'] == QWEN and m.get('context_length') == 65536 for m in active.get('models', []))
    recorder.add('context_check', ok=ok, models=active.get('models'))
    return ok


def freeze(out):
    source = out / 'source'
    for name in ['run_stage1.py', 'score_stage1.py', 'PROTOCOL_STAGE1.md', 'PROTOCOL_STAGE1C.md', 'CODEBOOK.md']:
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HERE / name, target)
    shutil.copytree(HERE / 'vendor', source / 'vendor', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT / 'src/rosa', source / 'src/rosa', ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['pyproject.toml', 'uv.lock']:
        shutil.copy2(ROOT / name, source / name)
    hashes = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
    packages = {n: importlib.metadata.version(n) for n in
                ['jpl-rosa', 'rosa-llm', 'langchain', 'langchain-core', 'langchain-ollama', 'ollama']
                if _installed(n)}
    git = lambda *a: subprocess.check_output(['git', *a], cwd=ROOT, text=True).strip()
    save(out / 'identity.json', dict(
        utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), head=git('rev-parse', 'HEAD'), branch=git('branch', '--show-current'),
        status=git('status', '--short'), python=sys.version, packages=packages, source_sha256=hashes,
        prompt_sha256={'A_orig': prompt_hash('A_orig'), 'A0': prompt_hash('A0')},
        prompts={'A_orig': prompt_messages('A_orig'), 'A0': prompt_messages('A0')},
        environment={k: os.environ.get(k) for k in ['ROS_DISTRO', 'ROS_DOMAIN_ID', 'ROS_LOCALHOST_ONLY', 'RMW_IMPLEMENTATION']}))


def _installed(name):
    try:
        importlib.metadata.version(name)
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def run_worker(out, directory, extra, timeout, recorder):
    command = [sys.executable, str(HERE / 'run_stage1.py'), 'episode', '--output', str(directory)] + extra
    recorder.add('worker_start', command=command)
    started = time.perf_counter()
    error = None
    with (out / (directory.name + '.worker.log')).open('w') as log:
        worker = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = worker.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(worker.pid, signal.SIGTERM)
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(worker.pid, signal.SIGKILL)
                worker.wait()
            code, error = worker.returncode, f'{timeout}-second episode timeout'
    record = dict(directory=directory.name, returncode=code, error=error, seconds=time.perf_counter() - started, args=extra)
    with (out / 'attempts.jsonl').open('a') as handle:
        handle.write(json.dumps(record) + '\n')
    print(json.dumps(record), flush=True)
    return record


# ---------------------------------------------------------------- oracle snapshots (stage 1a)
def snapshot_1a(out, label):
    directory = out / 'oracle' / label
    directory.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(directory / 'trace.jsonl')
    commands = {'nodes': ['node', 'list', '--no-daemon', '--spin-time', '3'], 'topics': ['topic', 'list'], 'services': ['service', 'list']}
    for node in NODES_1A:
        commands[node + ':info'] = ['node', 'info', node]
        commands[node + ':params'] = ['param', 'dump', node]
    for topic in ['/diag_turtle/turtle1/pose', '/diag_turtle/turtle1/cmd_vel', '/diag_turtle/turtle1/color_sensor', '/diag_demo/chatter']:
        commands[topic + ':info'] = ['topic', 'info', topic, '--verbose']
    records = {}
    for key, argv in commands.items():
        for attempt in range(3 if key == 'nodes' else 1):  # revision 1: node enumeration may miss a node; retry (evaluation only)
            p = subprocess.run(['ros2', *argv], capture_output=True, text=True, timeout=30)
            records[key] = dict(command=['ros2', *argv], returncode=p.returncode, stdout=p.stdout, stderr=p.stderr, attempt=attempt)
            recorder.add('oracle', key=key, **records[key])
            if key != 'nodes' or set(NODES_1A) <= set(p.stdout.splitlines()):
                break
    for service in records['services']['stdout'].splitlines():
        if service.startswith(('/diag_turtle/', '/diag_demo/')):
            p = subprocess.run(['ros2', 'service', 'type', service], capture_output=True, text=True, timeout=30)
            records[service + ':type'] = dict(command=['ros2', 'service', 'type', service], returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
    save(directory / 'snapshot.json', records)
    if any(r['returncode'] for r in records.values()):
        raise RuntimeError('Oracle operation failed; inspect preserved snapshot')
    if not set(NODES_1A) <= set(records['nodes']['stdout'].splitlines()):
        raise RuntimeError('Oracle missing fixture nodes')


def stage1a(out, resume=None, start=0, provider='ollama', arms=('A_orig', 'A0'), seed=20261112):
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {'ROS_DOMAIN_ID': '211', 'ROS_LOCALHOST_ONLY': '1'}.items():
        assert os.environ.get(key) == value, f'set {key}={value} before running'
    freeze(out)
    recorder = Recorder(out / 'setup.jsonl')
    save(out / 'protocol_reference.json', dict(protocol='PROTOCOL_STAGE1C.md' if provider == 'openai' else 'PROTOCOL_STAGE1.md', stage='1c' if provider == 'openai' else '1a', models=[LUNA if provider == 'openai' else QWEN], ollama=OLLAMA))
    if provider == 'ollama':
        with urllib.request.urlopen(OLLAMA + '/api/tags', timeout=15) as response:
            save(out / 'ollama-tags.json', json.load(response))
    rng = random.Random(seed)
    schedule = []
    for repeat in range(2):
        block = [(repeat, t['id'], arm) for t in BASELINE['tasks'] for arm in arms]
        rng.shuffle(block)
        schedule.extend(block)
    assert len(schedule) == 12 * len(arms)
    if resume:  # revision 2: continue the SAME schedule after an aborted run; the old schedule must be identical
        assert json.loads((Path(resume) / 'schedule.json').read_text()) == [list(x) for x in schedule], 'schedule differs'
    save(out / 'schedule.json', schedule)
    save(out / 'resume.json', dict(resumed_from=str(resume), start_index=start))
    processes = handles = None
    try:
        assert_domain_empty(('/diag_turtle', '/diag_demo'), recorder)
        processes, handles = start_processes(FIXTURE_1A, out, '1a', recorder)
        time.sleep(5)
        if not wait_for(NODES_1A, recorder):
            raise RuntimeError('Fixture discovery not ready')
        snapshot_1a(out, 'before')
        for index, (repeat, task, arm) in enumerate(schedule):
            if index < start:
                continue
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Fixture process exited during study')
            destination = out / f'{index:02d}-{task}-{arm}-r{repeat}'
            record = run_worker(out, destination, ['--stage', '1a', '--provider', provider, '--task', task, '--arm', arm,
                                                  '--repeat', str(repeat)], 240, recorder)
            if provider == 'ollama' and index == start and not check_context(out, 'ollama-active-context.json', recorder):
                raise RuntimeError('Active Ollama context is not 65536; stopping')
            if provider == 'openai':
                text = (destination / 'trace.jsonl').read_text() if (destination / 'trace.jsonl').exists() else ''
                answer_missing = '"answer": null' in text.split('"kind": "episode_end"')[-1][:400]
                if 'model_error' in text and answer_missing:
                    recorder.add('provider_stop', directory=destination.name)
                    raise RuntimeError(f'Strong-model access or provider error in {destination.name}; stopping')
            if (index + 1) % 6 == 0:
                snapshot_1a(out, f'after-{index + 1:02d}')
        snapshot_1a(out, 'after')
    except Exception as failure:
        recorder.add('study_error', error=repr(failure))
        raise
    finally:
        if processes is not None:
            stop_processes(processes, handles, recorder)
            recorder.add('cleanup_ok', ok=verify_empty(('/diag_turtle', '/diag_demo'), recorder))
        stop_daemon(recorder)


# ---------------------------------------------------------------- stage 1b
def scale_commands(n):
    return [['ros2', 'run', 'demo_nodes_cpp', 'talker', '--ros-args', '-r', '__ns:=/scale', '-r', f'__node:=n{i:02d}',
             '-p', f'use_sim_time:={"true" if i % 3 == 0 else "false"}'] for i in range(n)]


def scale_truth(n):
    return {f'/scale/n{i:02d}': (i % 3 == 0) for i in range(n)}


def scale_oracle(out, n, recorder):
    """Direct read of every node's parameter; must equal the declared truth or the run aborts."""
    truth, observed = scale_truth(n), {}
    for node in truth:
        observed[node] = None
        for attempt in range(3):  # evaluation-only reads may retry; the agent's own reads never do
            p = subprocess.run(['ros2', 'param', 'get', node, 'use_sim_time'], capture_output=True, text=True, timeout=30)
            recorder.add('oracle', node=node, attempt=attempt, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr)
            if p.returncode == 0:
                observed[node] = p.stdout.strip() == 'Boolean value is: True'
                break
            time.sleep(2)
    save(out / f'oracle-N{n:02d}.json', dict(truth=truth, observed=observed))
    return observed == truth


def stage1b(out, providers, only_n=None):
    out = Path(out)
    out.mkdir(exist_ok=False)
    for key, value in {'ROS_DOMAIN_ID': '212', 'ROS_LOCALHOST_ONLY': '1'}.items():
        assert os.environ.get(key) == value, f'set {key}={value} before running'
    freeze(out)
    recorder = Recorder(out / 'setup.jsonl')
    save(out / 'protocol_reference.json', dict(protocol='PROTOCOL_STAGE1.md', stage='1b', providers=providers, ollama=OLLAMA, strong_model=LUNA))
    caps = {'ollama': 16, 'openai': 16}
    used = {p: 0 for p in providers}
    active = list(providers)
    episodes = 0
    try:
        assert_domain_empty(('/scale',), recorder)
        for n in ((only_n,) if only_n else (4, 8, 16, 32)):
            processes, handles = start_processes(scale_commands(n), out, f'N{n:02d}', recorder)
            try:
                time.sleep(4)
                expected = list(scale_truth(n))
                listed = wait_for(expected, recorder)
                # revision 3: if `ros2 node list` omits a live node, proceed only when the direct oracle reads confirm all N nodes
                recorder.add('readiness_summary', n=n, fully_listed=listed)
                if not listed and not only_n:
                    raise RuntimeError(f'Fixture N={n} not discoverable')
                if not scale_oracle(out, n, recorder):
                    raise RuntimeError(f'Oracle mismatch at N={n}')
                jobs = [('pilot', 'pilot')] if n == 4 and not only_n else []
                jobs += [(f'r{r}', r) for r in (0, 1)]
                for label, repeat in jobs:
                    for provider in list(active):
                        if used[provider] >= caps[provider] or episodes >= 60:
                            raise RuntimeError('Episode cap reached')
                        if any(p.poll() is not None for p in processes):
                            raise RuntimeError('Fixture process exited during study')
                        destination = out / f'N{n:02d}-{provider}-{label}'
                        timeout = 900 if provider == 'ollama' else 600
                        record = run_worker(out, destination, ['--stage', '1b', '--provider', provider, '--n', str(n), '--arm', 'A0',
                                                              '--repeat', '0' if label == 'pilot' else str(repeat)], timeout, recorder)
                        used[provider] += 1
                        episodes += 1
                        if provider == 'ollama' and episodes == 1:
                            if not check_context(out, 'ollama-active-context.json', recorder):
                                raise RuntimeError('Active Ollama context is not 65536; stopping')
                        trace = destination / 'trace.jsonl'
                        text = trace.read_text() if trace.exists() else ''
                        if provider == 'openai' and ('model_error' in text and 'episode_end' in text and '"answer": null' in text.split('"kind": "episode_end"')[-1][:400]):
                            recorder.add('provider_stop', provider=provider, directory=destination.name)
                            active.remove(provider)
                            print(f'STOP strong-model part after {destination.name}: see trace', flush=True)
                    if not active:
                        raise RuntimeError('No provider left')
            finally:
                stop_processes(processes, handles, recorder)
                if not verify_empty(('/scale',), recorder):
                    raise RuntimeError('Cleanup failed; aborting')
    except Exception as failure:
        recorder.add('study_error', error=repr(failure))
        raise
    finally:
        recorder.add('cleanup_ok', ok=verify_empty(('/scale',), recorder))
        stop_daemon(recorder)


def offline_check():
    """No inference, no fixture."""
    a, b = prompt_messages('A_orig'), prompt_messages('A0')
    diff = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x != y]
    assert len(a) == len(b) and len(diff) == 1, 'A0 must differ from A_orig in exactly one message'
    print('prompt messages:', len(a), 'differing index:', diff[0][0])
    print('A_orig sha256', prompt_hash('A_orig'))
    print('A0     sha256', prompt_hash('A0'))
    print('removed text:', diff[0][1][1][:90], '...')
    print('added text  :', diff[0][2][1])
    assert len(scale_commands(32)) == 32 and sum(scale_truth(32).values()) == 11
    registry = StageROSA.__mro__  # construct once with a dummy model to confirm the override is used
    class Dummy(BaseChatModel):
        @property
        def _llm_type(self):
            return 'dummy'
        def bind_tools(self, tools, **kwargs):
            return self
        def _generate(self, *args, **kwargs):
            raise RuntimeError('no inference in offline check')
    agent = StageROSA(Dummy(), 'A0', 3)
    prompts = agent._ROSA__prompts.format_messages(chat_history=[], input='x', agent_scratchpad=[])
    texts = '\n'.join(m.content for m in prompts)
    assert 'Independent tool calls whose arguments are already known' in texts and 'Do not batch tool calls' not in texts
    names = sorted(t.name for t in agent._ROSA__tools.get_tools())
    print('registry tools:', len(names), 'param_get present:', 'ros2_param_get' in names)
    schema = next(t for t in agent._ROSA__tools.get_tools() if t.name == 'ros2_param_get').args
    print('ros2_param_get args:', list(schema))
    print('OFFLINE CHECK OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check')
    s1 = sub.add_parser('stage1a'); s1.add_argument('output'); s1.add_argument('--resume'); s1.add_argument('--start', type=int, default=0)
    s3 = sub.add_parser('stage1c'); s3.add_argument('output')
    s2 = sub.add_parser('stage1b'); s2.add_argument('output'); s2.add_argument('--only-n', type=int); s2.add_argument('--providers', nargs='+', default=['ollama', 'openai'])
    e = sub.add_parser('episode')
    e.add_argument('--output', required=True); e.add_argument('--stage', choices=['1a', '1b'], required=True)
    e.add_argument('--provider', choices=['ollama', 'openai'], required=True); e.add_argument('--arm', choices=['A_orig', 'A0'])
    e.add_argument('--task'); e.add_argument('--n', type=int); e.add_argument('--repeat', default='0')
    args = parser.parse_args()
    if args.command == 'check':
        offline_check()
    elif args.command == 'stage1a':
        stage1a(args.output, args.resume, args.start)
    elif args.command == 'stage1c':
        stage1a(args.output, None, 0, provider='openai', arms=('A0',), seed=20261113)
    elif args.command == 'stage1b':
        stage1b(args.output, args.providers, args.only_n)
    else:
        episode(args)
