"""Bounded native ROSA study. All output goes to an explicitly new /tmp directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shlex
import signal
import subprocess
import sys
import time
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_ollama import ChatOllama
from pydantic import Field

from rosa.rosa import ROSA
from rosa.tools import ros2
from menu_policy import MenuPolicy

HERE = Path(__file__).resolve().parent


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str))


class Recorder:
    def __init__(self, path):
        self.path = path
        self.rows = []

    def add(self, kind, **values):
        row = {'kind': kind, 'monotonic': time.perf_counter(), 'tool_run_id':getattr(self,'active_tool',None), **values}
        self.rows.append(row)
        with self.path.open('a') as f:
            f.write(json.dumps(row, default=str) + '\n')


class ToolRecorder(BaseCallbackHandler):
    def __init__(self, recorder):
        self.recorder = recorder

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self.recorder.active_tool = str(run_id)
        self.recorder.add('tool_start', name=serialized.get('name'), input=input_str, run_id=str(run_id))

    def on_tool_end(self, output, *, run_id, **kwargs):
        self.recorder.add('tool_end', output=output, run_id=str(run_id))
        self.recorder.active_tool = None

    def on_tool_error(self, error, *, run_id, **kwargs):
        self.recorder.add('tool_error', error=str(error), run_id=str(run_id))
        self.recorder.active_tool = None


class MenuModel(BaseChatModel):
    """Intercept schema binding; preserve the existing AgentExecutor loop."""
    underlying: Any
    recorder: Any
    arm: str
    request: str
    policy: Any = None
    schemas: list = Field(default_factory=list)

    @property
    def _llm_type(self):
        return 'experimental-documentation-menu'

    def bind_tools(self, tools, **kwargs):
        schemas = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=schemas, **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        schemas = kwargs.pop('tools', [])
        normal = [s for s in schemas if s['function']['name'] != 'expand_tool_menu']
        extra = [s for s in schemas if s['function']['name'] == 'expand_tool_menu']
        if self.policy is None:
            self.policy = MenuPolicy(normal, self.arm)
            self.recorder.add('preprocessing', seconds=self.policy.preprocessing_seconds)
        observations = [m for m in messages if isinstance(m, ToolMessage)]
        expanded = any(m.content == 'FULL_TOOL_MENU_REQUESTED' for m in observations)
        observation = str(observations[-1].content) if observations else ''
        selected, decision = self.policy.select(self.request, observation, expanded)
        advertised = selected + extra
        self.recorder.add('model_start', messages=[m.model_dump() for m in messages], schemas=advertised, schema_characters=len(json.dumps(advertised)), decision=decision)
        started = time.perf_counter()
        try:
            answer = self.underlying.bind_tools(advertised).invoke(messages, stop=stop)
        except Exception as error:
            self.recorder.add('model_error', seconds=time.perf_counter()-started, error=str(error))
            raise
        self.recorder.add('model_end', seconds=time.perf_counter()-started, message=answer.model_dump(), usage=answer.usage_metadata, response_metadata=answer.response_metadata)
        return ChatResult(generations=[ChatGeneration(message=answer)])


@tool
def expand_tool_menu(reason: str) -> str:
    """Request the complete original tool menu when the visible tools are insufficient."""
    return 'FULL_TOOL_MENU_REQUESTED'


def guarded_native(recorder):
    """Same observation-only command guard for all arms, not an endpoint map."""
    allowed = {('node', 'list'), ('node', 'info'), ('topic', 'list'), ('topic', 'info'), ('topic', 'echo'), ('param', 'list'), ('param', 'get'), ('service', 'list'), ('service', 'type')}

    def execute(command):
        started = time.perf_counter()
        args = shlex.split(command)
        if len(args) < 3 or args[0] != 'ros2' or tuple(args[1:3]) not in allowed or any(not re.fullmatch(r'[A-Za-z0-9_./:=+-]+', x) for x in args):
            recorder.add('guard_rejection', command=command)
            return False, 'Observation-only study: command rejected.'
        recorder.add('ros_start', command=args)
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=15)
            recorder.add('ros_end', command=args, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, seconds=time.perf_counter()-started)
            return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
        except subprocess.TimeoutExpired as error:
            recorder.add('ros_error', command=args, error='15-second native command timeout', seconds=time.perf_counter()-started)
            return False, 'Native command timed out after 15 seconds.'
    return execute


def episode(args):
    protocol = json.loads((HERE/'protocol.json').read_text())
    tasks = protocol['development'] + protocol['tasks']
    task = next(t for t in tasks if t['id'] == args.task)
    dest = Path(args.output)
    dest.mkdir(exist_ok=False)
    recorder = Recorder(dest/'trace.jsonl')
    model = protocol['model']
    # These exact options are used in every arm, independent of .env provider.
    base = ChatOllama(model=model['name'], base_url=args.base_url, temperature=model['temperature'], seed=model['seed'], reasoning=model['reasoning'], num_predict=model['num_predict'], client_kwargs={'timeout': model['timeout_seconds']})
    llm = MenuModel(underlying=base, recorder=recorder, arm=args.arm, request=task['request'])
    ros2.execute_ros_command = guarded_native(recorder)
    agent = ROSA(ros_version=2, llm=llm, streaming=False, verbose=False, max_iterations=protocol['budgets']['max_iterations'], accumulate_chat_history=False, tools=[expand_tool_menu] if args.arm in ('simple', 'candidate') else [])
    recorder.add('episode_start', task=task, arm=args.arm)
    request = task['request']
    if args.arm != 'original':
        request += '\nUse independent tool calls together when possible. Reuse acquired facts. Answer only the requested JSON.'
        if args.arm in ('simple', 'candidate'):
            request += ' If needed, request the full tool menu with expand_tool_menu.'
    started = time.perf_counter()
    try:
        # Invoke the existing executor directly only to attach a read-only callback.
        # This is the same executor ROSA.invoke calls, with fresh empty history.
        result = agent._ROSA__executor.invoke({'input': request, 'chat_history': []}, config={'callbacks': [ToolRecorder(recorder)]})
        answer = result['output']
        error = None
    except Exception as failure:
        answer, error = None, str(failure)
    recorder.add('episode_end', answer=answer, error=error, seconds=time.perf_counter()-started)
    save(dest/'answer.json', {'task_id':args.task,'arm':args.arm,'answer':answer,'error':error})


def oracle(out, phase):
    commands = {
        'nodes':['node','list','--no-daemon','--spin-time','3'],
        'rgb':['param','dump','/restart_turtle/palette'],
        't_parameters':['param','list','/restart_turtle/palette'],
        't_absent':['param','get','/restart_turtle/palette','unconfigured_gain'],
        'pose':['topic','info','/restart_turtle/turtle1/pose','--verbose'],
        'd_use_sim_time':['param','get','/restart_demo/source','use_sim_time'],
        'chatter':['topic','info','/restart_demo/chatter','--verbose'],
        'service':['service','type','/restart_demo/add_two_ints'],
        'source':['node','info','/restart_demo/source'],
        'topics':['topic','list'],
    }
    records = {}
    for name, argv in commands.items():
        p = subprocess.run(['ros2', *argv], capture_output=True, text=True, timeout=20)
        records[name] = {'command':['ros2',*argv],'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    save(out/f'oracle-{phase}.json', records)
    for name, record in records.items():
        if name != 't_absent' and record['returncode'] != 0:
            raise RuntimeError('Invalid native oracle: '+name)
    nodes = records['nodes']['stdout'].splitlines()
    if not all(n in nodes for n in ('/restart_turtle/palette', '/restart_demo/source', '/restart_demo/calculator')):
        raise RuntimeError('Native discovery not ready: expected fixture nodes absent.')


def study(args):
    if os.environ.get('ROS_DOMAIN_ID') != '86' or os.environ.get('ROS_LOCALHOST_ONLY') != '1':
        raise RuntimeError('Study requires ROS_DOMAIN_ID=86 and ROS_LOCALHOST_ONLY=1.')
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    protocol = json.loads((HERE/'protocol.json').read_text())
    source = out/'source'
    shutil = __import__('shutil')
    shutil.copytree(HERE, source, ignore=shutil.ignore_patterns('__pycache__'))
    save(out/'frozen-sha256.json', {p.name:hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in source.iterdir() if p.is_file()})
    # Source/registry identity establishes provenance, not execution correctness.
    save(out/'identity.json', {'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'core_files':{str(p):hashlib.file_digest(p.open('rb'),'sha256').hexdigest() for p in Path('src/rosa').rglob('*.py')},'ros_domain_id':os.environ.get('ROS_DOMAIN_ID'),'ros_localhost_only':os.environ.get('ROS_LOCALHOST_ONLY'),'rmw_implementation':os.environ.get('RMW_IMPLEMENTATION','platform default'),'python':sys.version})
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
    processes = []
    handles = []
    commands = [
        ['ros2','run','turtlesim','turtlesim_node','--ros-args','-r','__ns:=/restart_turtle','-r','__node:=palette','-p','background_r:=37','-p','background_g:=83','-p','background_b:=129'],
        ['ros2','run','demo_nodes_cpp','talker','--ros-args','-r','__ns:=/restart_demo','-r','__node:=source'],
        ['ros2','run','demo_nodes_cpp','add_two_ints_server','--ros-args','-r','__ns:=/restart_demo','-r','__node:=calculator'],
    ]
    save(out/'fixture-commands.json',commands)
    try:
        existing = subprocess.run(['ros2','node','list','--no-daemon'],capture_output=True,text=True,timeout=15)
        save(out/'preexisting-domain.json',{'stdout':existing.stdout,'stderr':existing.stderr,'returncode':existing.returncode})
        if existing.returncode != 0:
            raise RuntimeError('Cannot establish empty disposable namespace.')
        if '/restart_' in existing.stdout:
            raise RuntimeError('Selected disposable namespace already exists; refusing collision.')
        for index, command in enumerate(commands):
            handle = (out/f'fixture-{index}.log').open('w')
            handles.append(handle)
            processes.append(subprocess.Popen(command,stdout=handle,stderr=subprocess.STDOUT,env=env,start_new_session=True))
        time.sleep(5)
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('Stock fixture failed to start; inspect fixture logs.')
        oracle(out,'before')
        if args.phase == 'development':
            schedule = [(t['id'], arm) for arm in ('original','simple','candidate') for t in protocol['development']]
        else:
            rng = random.Random(protocol['budgets']['order_seed'])
            tasks = protocol['tasks'].copy()
            rng.shuffle(tasks)
            schedule=[]
            for task in tasks:
                arms=protocol['arms'].copy()
                rng.shuffle(arms)
                schedule.extend((task['id'], arm) for arm in arms)
        save(out/'schedule.json',schedule)
        for index,(task_id, arm) in enumerate(schedule):
            episode_path = out/f'{index:02d}-{task_id}-{arm}'
            command = [sys.executable,str(HERE/'run_study.py'),'--episode','--task',task_id,'--arm',arm,'--output',str(episode_path),'--base-url',args.base_url]
            started = time.perf_counter()
            with (out/f'{index:02d}-worker.log').open('w') as log:
                worker=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    returncode=worker.wait(timeout=protocol['budgets']['episode_seconds'])
                    error=None
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid,signal.SIGTERM)
                    try:worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(worker.pid,signal.SIGKILL)
                        worker.wait()
                    returncode=worker.returncode
                    error='150-second episode budget exceeded'
            record={'index':index,'task':task_id,'arm':arm,'returncode':returncode,'seconds_including_process_start':time.perf_counter()-started,'error':error}
            with (out/'attempts.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
            print(json.dumps(record),flush=True)
        oracle(out,'after')
    finally:
        for process in processes:
            if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
        for process in processes:
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
        for handle in handles:handle.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',action='store_true')
    parser.add_argument('--task')
    parser.add_argument('--arm',choices=['original','prompted','simple','candidate'])
    parser.add_argument('--phase',choices=['development','evaluation'],default='development')
    parser.add_argument('--output',required=True)
    parser.add_argument('--base-url',default=os.environ.get('ROSA_OLLAMA_URL', 'http://172.30.80.1:11434'))
    args=parser.parse_args()
    if args.episode:episode(args)
    else:study(args)


if __name__=='__main__':main()
