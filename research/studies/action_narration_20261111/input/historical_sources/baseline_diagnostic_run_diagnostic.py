"""Baseline-only ROSA diagnostic. No application semantics enter the agent."""
import argparse
import hashlib
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

from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_ollama import ChatOllama
from rosa.rosa import ROSA
from rosa.tools import ros2

# Reuse instrumentation and a common observation guard only, not old controllers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'menu_retrieval'))
from run_study import Recorder, ToolRecorder, guarded_native, save

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
READS = ('ros2_node_list', 'ros2_node_info', 'ros2_topic_list', 'ros2_topic_info',
         'ros2_service_list', 'ros2_service_info', 'ros2_param_list', 'ros2_param_get')


class TracedModel(BaseChatModel):
    underlying: object
    recorder: object

    @property
    def _llm_type(self):
        return 'full-registry-tracing-only'

    def bind_tools(self, tools, **kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools], **kwargs)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        schemas = kwargs.pop('tools', [])
        self.recorder.add('model_start', messages=[m.model_dump() for m in messages], schemas=schemas)
        started = time.perf_counter()
        try:
            answer = self.underlying.bind_tools(schemas).invoke(messages, stop=stop)
        except Exception as error:
            self.recorder.add('model_error', error=str(error), seconds=time.perf_counter()-started)
            raise
        self.recorder.add('model_end', message=answer.model_dump(), usage=answer.usage_metadata,
                          response_metadata=answer.response_metadata, seconds=time.perf_counter()-started)
        return ChatResult(generations=[ChatGeneration(message=answer)])


def batch_tool(recorder):
    @tool
    def batch_reads(calls: list[dict]) -> list[dict]:
        """Run 1-8 independent generic ROSA read calls with already known arguments.

        calls is a JSON list of objects: {"tool": actual tool name, "args": its
        normal argument object}. Allowed: ros2_node_list, ros2_node_info,
        ros2_topic_list, ros2_topic_info, ros2_service_list, ros2_service_info,
        ros2_param_list, ros2_param_get. Results retain tool and argument identity.
        No result references or implicit source selection. Calls execute serially;
        all ordinary tools remain available. Errors are returned individually.
        """
        started = time.perf_counter()
        if not 1 <= len(calls) <= 8:
            return [{'error':'Batch needs 1-8 calls'}]
        # Validate all entries before executing any call.
        for call in calls:
            if set(call) != {'tool', 'args'} or call['tool'] not in READS or not isinstance(call['args'], dict):
                return [{'error':'Each call needs an allowed tool and args object'}]
        results = []
        for index, call in enumerate(calls):
            recorder.add('batch_dispatch', index=index, **call)
            try:
                result = getattr(ros2, call['tool']).invoke(call['args'])
            except Exception as error:
                result = {'error':str(error)}
            results.append({**call, 'result':result})
            recorder.add('batch_result', index=index, **results[-1])
        recorder.add('batch_end', seconds=time.perf_counter()-started, calls=len(calls))
        return results
    batch_reads.handle_validation_error = 'Invalid batch: calls must be a JSON list of tool/args objects. Use ordinary tools to recover.'
    return batch_reads


def episode(args):
    protocol = json.loads((HERE/'protocol.json').read_text())
    task = next(t for t in protocol['tasks'] if t['id'] == args.task)
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    recorder = Recorder(out/'trace.jsonl')
    recorder.add('episode_start', task=task, arm=args.arm, repeat=args.repeat)
    settings = dict(protocol['model'])
    settings['model'] = settings.pop('name')
    timeout = settings.pop('timeout_seconds')
    base = ChatOllama(**settings, client_kwargs={'timeout':timeout})
    model = TracedModel(underlying=base, recorder=recorder)
    ros2.execute_ros_command = guarded_native(recorder)
    extra = [batch_tool(recorder)] if args.arm == 'C' else []
    agent = ROSA(ros_version=2, llm=model, streaming=False, verbose=False,
                 max_iterations=protocol['budgets']['max_iterations'],
                 accumulate_chat_history=False, tools=extra)
    request = task['request']
    if args.arm in ('B','C'):
        request += '\n' + protocol['guidance']
    if args.arm == 'C':
        request += '\nYou may use batch_reads for independent reads whose arguments are known. Ordinary tools and their list arguments remain available.'
    recorder.add('effective_request', request=request)
    started = time.perf_counter()
    try:
        result = agent._ROSA__executor.invoke({'input':request, 'chat_history':[]},
                                             config={'callbacks':[ToolRecorder(recorder)]})
        answer, error = result['output'], None
    except Exception as failure:
        answer, error = None, repr(failure)
    recorder.add('episode_end', answer=answer, error=error, seconds=time.perf_counter()-started)
    save(out/'answer.json', dict(task=args.task, arm=args.arm, repeat=args.repeat, answer=answer, error=error))


def snapshot(out, label):
    """Independent evaluation only. Not imported by episode logic."""
    directory = out/'oracle'/label
    directory.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(directory/'trace.jsonl')
    commands = {'nodes':['node','list','--no-daemon','--spin-time','3'],
                'topics':['topic','list'], 'services':['service','list']}
    for node in ['/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator']:
        commands[node+':info'] = ['node','info',node]
        commands[node+':params'] = ['param','dump',node]
    for topic in ['/diag_turtle/turtle1/pose','/diag_turtle/turtle1/cmd_vel','/diag_turtle/turtle1/color_sensor','/diag_demo/chatter']:
        commands[topic+':info'] = ['topic','info',topic,'--verbose']
    records = {}
    for key, argv in commands.items():
        recorder.add('oracle_start', key=key, command=['ros2',*argv])
        p = subprocess.run(['ros2',*argv],capture_output=True,text=True,timeout=20)
        records[key] = dict(command=['ros2',*argv],returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        recorder.add('oracle_end', key=key, **records[key])
    for service in records['services']['stdout'].splitlines():
        if service.startswith(('/diag_turtle/','/diag_demo/')):
            argv = ['ros2','service','type',service]
            recorder.add('oracle_start',key=service+':type',command=argv)
            p = subprocess.run(argv,capture_output=True,text=True,timeout=20)
            records[service+':type'] = dict(command=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
            recorder.add('oracle_end',key=service+':type',**records[service+':type'])
    save(directory/'snapshot.json', records)
    if any(r['returncode'] for r in records.values()):
        raise RuntimeError('Oracle operation failed; inspect preserved snapshot')
    expected_nodes = ['/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator']
    if not all(n in records['nodes']['stdout'].splitlines() for n in expected_nodes):
        raise RuntimeError('Independent oracle missing fixture nodes')


def study(args):
    protocol = json.loads((HERE/'protocol.json').read_text())
    if any(os.environ.get(k) != v for k,v in protocol['environment'].items() if k.startswith('ROS_')):
        raise RuntimeError('Use frozen disposable domain 89, localhost only')
    out = Path(args.output)
    out.mkdir(exist_ok=False)
    # Snapshot sources before any model execution. Never copy .env or auth files.
    for relative in ['research/baseline_diagnostic','research/menu_retrieval','src/rosa']:
        shutil.copytree(ROOT/relative, out/'source'/relative, ignore=shutil.ignore_patterns('__pycache__'))
    for relative in ['pyproject.toml','uv.lock','AGENTS.md']:
        shutil.copy2(ROOT/relative,out/'source'/relative)
    save(out/'freeze.json', {'utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         'sha256':{str(p.relative_to(out/'source')):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (out/'source').rglob('*') if p.is_file()}})
    save(out/'identity.json', {'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
         'status':subprocess.check_output(['git','status','--short'],text=True),
         'python':sys.version,'environment':{k:os.environ.get(k) for k in ['ROS_DISTRO','ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY','RMW_IMPLEMENTATION']}})
    with urllib.request.urlopen(protocol['model']['base_url']+'/api/tags',timeout=15) as response:
        save(out/'ollama-tags.json',json.load(response))
    save(out/'packages.json', {name:__import__('importlib.metadata',fromlist=['version']).version(name)
          for name in ['jpl-rosa','rosa-llm','langchain','langchain-core','langchain-ollama','ollama']})
    commands = [
      ['ros2','run','turtlesim','turtlesim_node','--ros-args','-r','__ns:=/diag_turtle','-r','__node:=palette','-p','background_r:=37','-p','background_g:=83','-p','background_b:=129'],
      ['ros2','run','demo_nodes_cpp','talker','--ros-args','-r','__ns:=/diag_demo','-r','__node:=source'],
      ['ros2','run','demo_nodes_cpp','listener','--ros-args','-r','__ns:=/diag_demo','-r','__node:=listener'],
      ['ros2','run','demo_nodes_cpp','add_two_ints_server','--ros-args','-r','__ns:=/diag_demo','-r','__node:=calculator']]
    save(out/'fixture-commands.json',commands)
    recorder = Recorder(out/'setup.jsonl')
    processes, handles = [], []
    try:
        p = subprocess.run(['ros2','node','list','--no-daemon'],capture_output=True,text=True,timeout=20)
        recorder.add('preexisting_domain',returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        if p.returncode or any(line.startswith(('/diag_turtle','/diag_demo')) for line in p.stdout.splitlines()):
            raise RuntimeError('Cannot establish collision-free fixture namespaces')
        for index,cmd in enumerate(commands):
            handle = (out/f'fixture-{index}.log').open('w')
            handles.append(handle)
            recorder.add('fixture_start',command=cmd)
            processes.append(subprocess.Popen(cmd,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,
                                              env=dict(os.environ,QT_QPA_PLATFORM='offscreen')))
        time.sleep(5)
        for attempt in range(4):
            p = subprocess.run(['ros2','node','list'],capture_output=True,text=True,timeout=15)
            recorder.add('readiness',attempt=attempt,stdout=p.stdout,stderr=p.stderr,returncode=p.returncode)
            if all(n in p.stdout for n in ['/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator']):
                break
            time.sleep(1)
        else:
            raise RuntimeError('Fixture discovery not ready')
        snapshot(out,'before')
        schedule = []
        rng = random.Random(protocol['budgets']['order_seed'])
        # Keep same-task repetitions separated; shuffle each repetition.
        for repeat in range(protocol['budgets']['repeats']):
            block = [(repeat,t['id'],a) for t in protocol['tasks'] for a in protocol['arms']]
            rng.shuffle(block)
            schedule.extend(block)
        save(out/'schedule.json',schedule)
        primary_started = time.perf_counter()
        for index,(repeat,task,arm) in enumerate(schedule):
            if time.perf_counter()-primary_started > protocol['budgets']['total_seconds']:
                recorder.add('budget_stop',unattempted=len(schedule)-index)
                break
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Fixture process exited during study')
            destination = out/f'{index:02d}-{task}-{arm}-r{repeat}'
            cmd = [sys.executable,str(HERE/'run_diagnostic.py'),'--episode','--task',task,'--arm',arm,
                   '--repeat',str(repeat),'--output',str(destination)]
            recorder.add('episode_launch',index=index,task=task,arm=arm,repeat=repeat,command=cmd)
            started = time.perf_counter()
            with (out/f'{index:02d}-worker.log').open('w') as handle:
                worker = subprocess.Popen(cmd,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    code = worker.wait(timeout=protocol['budgets']['episode_seconds'])
                    error = None
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid,signal.SIGTERM)
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(worker.pid,signal.SIGKILL)
                        worker.wait()
                    code,error = worker.returncode,'240-second episode timeout'
            record = dict(index=index,task=task,arm=arm,repeat=repeat,returncode=code,error=error,
                          seconds=time.perf_counter()-started,directory=destination.name)
            with (out/'attempts.jsonl').open('a') as handle:
                handle.write(json.dumps(record)+'\n')
            print(json.dumps(record),flush=True)
            if (index+1)%6 == 0:
                snapshot(out,f'after-{index+1:02d}')
        snapshot(out,'after')
    except Exception as error:
        recorder.add('study_error',error=repr(error))
        raise
    finally:
        for p in processes:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGTERM)
        for p in processes:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL)
                p.wait()
        for handle in handles:
            handle.close()
        recorder.add('fixture_cleanup',returncodes=[p.returncode for p in processes])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--episode',action='store_true')
    parser.add_argument('--task')
    parser.add_argument('--arm',choices=['A','B','C'])
    parser.add_argument('--repeat',type=int,default=0)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    episode(args) if args.episode else study(args)
