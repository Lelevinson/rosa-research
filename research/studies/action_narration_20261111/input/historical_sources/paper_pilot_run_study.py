"""Disposable native ROSA pilot. Evaluator snapshots never enter the agent."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import shutil
import signal
import subprocess
import sys
import time
import urllib.request

from langchain_ollama import ChatOllama
from rosa.rosa import ROSA
from rosa.tools import ros2
from code_reads import READ_TOOLS, ReadProgram, make_program_tool

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'research' / 'menu_retrieval'))
sys.path.insert(0, str(ROOT / 'research' / 'baseline_diagnostic'))
from run_diagnostic import TracedModel, batch_tool
from run_study import Recorder, ToolRecorder, guarded_native, save

GUIDANCE = ('Use independent tool calls together when possible. Reuse already acquired facts and '
            'discovery results within this request. Use list arguments and batch_reads for independent '
            'reads whose arguments are known. Preserve source identity. Distinguish observed values '
            'from configuration and missing sources. Do not infer facts from names or tool success. '
            'Answer only the requested JSON; explicitly report unavailable information.')
PROGRAM_GUIDANCE = ('When the request needs discovery followed by reads for discovered items, '
                    'first use run_read_program to perform that discovery and subsequent reads '
                    'together. Write a Python for loop over the earlier structured result as shown '
                    'in the tool description. Call ordinary tools when the source is ambiguous or '
                    'the program returns incomplete evidence. Preserve source identity and do not guess.')
FIXTURES = [
 ['ros2','run','turtlesim','turtlesim_node','--ros-args','-r','__ns:=/paper_turtle','-r','__node:=palette','-p','background_r:=37','-p','background_g:=83','-p','background_b:=129'],
 ['ros2','run','demo_nodes_cpp','talker','--ros-args','-r','__ns:=/paper_demo','-r','__node:=source'],
 ['ros2','run','demo_nodes_cpp','listener','--ros-args','-r','__ns:=/paper_demo','-r','__node:=listener'],
 ['ros2','run','demo_nodes_cpp','add_two_ints_server','--ros-args','-r','__ns:=/paper_demo','-r','__node:=calculator'],
]
NODES = ['/paper_turtle/palette','/paper_demo/source','/paper_demo/listener','/paper_demo/calculator']


def episode(args):
    config = json.loads((HERE / 'protocol.json').read_text())
    task = next(t for t in config['development'] + config['heldout'] if t['id'] == args.task)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    recorder = Recorder(out/'trace.jsonl')
    settings = config['model']
    base = ChatOllama(model=settings['name'], base_url=settings['base_url'], temperature=0, seed=42,
                      reasoning=False, num_predict=1600, client_kwargs={'timeout':90})
    model = TracedModel(underlying=base, recorder=recorder)
    ros2.execute_ros_command = guarded_native(recorder)
    extra = []
    if args.arm != 'A':
        extra.append(batch_tool(recorder))
    if args.arm == 'C':
        setup_started = time.perf_counter()
        extra.append(make_program_tool(ReadProgram({n: getattr(ros2, n) for n in READ_TOOLS}, recorder)))
        recorder.add('program_setup', seconds=time.perf_counter()-setup_started)
    agent = ROSA(ros_version=2, llm=model, streaming=False, verbose=False,
                 max_iterations=10, accumulate_chat_history=False, tools=extra)
    request = task['request']
    if args.arm != 'A':
        request += '\n' + GUIDANCE
    if args.arm == 'C':
        request += '\n' + PROGRAM_GUIDANCE
    recorder.add('episode_start', task=task, arm=args.arm, request=request)
    started = time.perf_counter()
    try:
        result = agent._ROSA__executor.invoke({'input':request, 'chat_history':[]},
                                               config={'callbacks':[ToolRecorder(recorder)]})
        answer, error = result['output'], None
    except Exception as failure:
        answer, error = None, repr(failure)
    recorder.add('episode_end', answer=answer, error=error, seconds=time.perf_counter()-started)
    save(out/'answer.json', {'task':args.task, 'arm':args.arm, 'answer':answer, 'error':error})


def snapshot(out, label):
    # Preserve both views: independent direct node/parameter checks below also
    # establish that the listed fixture nodes actually answer at snapshot time.
    commands = {'nodes':['node','list'], 'nodes_no_daemon':['node','list','--no-daemon','--spin-time','3'], 'topics':['topic','list'],
                'services':['service','list']}
    for node in NODES:
        commands[node+':info'] = ['node','info',node]
        commands[node+':params'] = ['param','dump',node]
        commands[node+':param_names'] = ['param','list',node]
    for topic in ['/paper_turtle/turtle1/pose','/paper_turtle/turtle1/cmd_vel','/paper_demo/chatter']:
        commands[topic+':info'] = ['topic','info',topic,'--verbose']
    records = {}
    for name, command in commands.items():
        try:
            p = subprocess.run(['ros2',*command],capture_output=True,text=True,timeout=20)
            records[name] = {'command':['ros2',*command], 'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
        except subprocess.TimeoutExpired as error:
            records[name] = {'command':['ros2',*command], 'error':repr(error)}
    save(out/('oracle-'+label+'.json'),records)
    if any(r.get('returncode') != 0 for r in records.values()) or not all(n in records['nodes']['stdout'].splitlines() for n in NODES):
        raise RuntimeError('Independent snapshot incomplete; preserved without replacement')


def study(args):
    if os.environ.get('ROS_DOMAIN_ID') != '91' or os.environ.get('ROS_LOCALHOST_ONLY') != '1':
        raise RuntimeError('Requires ROS_DOMAIN_ID=91 and ROS_LOCALHOST_ONLY=1')
    config = json.loads((HERE/'protocol.json').read_text())
    if args.phase == 'evaluation' and config.get('status') != 'frozen':
        raise RuntimeError('Heldout protocol must be frozen before evaluation')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    for rel in ['research/paper_pilot','research/menu_retrieval','research/baseline_diagnostic','src/rosa']:
        shutil.copytree(ROOT/rel, out/'source'/rel, ignore=shutil.ignore_patterns('__pycache__'))
    for rel in ['pyproject.toml','uv.lock','AGENTS.md']:
        shutil.copy2(ROOT/rel, out/'source'/rel)
    save(out/'source-hashes.json',{str(p.relative_to(out/'source')):hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (out/'source').rglob('*') if p.is_file()})
    save(out/'identity.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'status':subprocess.check_output(['git','status','--short'],text=True), 'python':sys.version,
         'platform':platform.platform(), 'ros_distro':os.environ.get('ROS_DISTRO'),
         'ros_domain_id':os.environ.get('ROS_DOMAIN_ID'), 'localhost_only':os.environ.get('ROS_LOCALHOST_ONLY'),
         'packages':{name:importlib.metadata.version(name) for name in
                     ('jpl-rosa','rosa-llm','langchain','langchain-core','langchain-ollama','ollama')},
         'phase':args.phase,'fixtures':FIXTURES})
    with urllib.request.urlopen(config['model']['base_url']+'/api/tags',timeout=15) as response:
        save(out/'ollama-tags.json',json.load(response))
    recorder = Recorder(out/'setup.jsonl')
    processes, files = [], []
    try:
        for command in (['ros2','node','list'], ['ros2','node','list','--no-daemon','--spin-time','3']):
            p = subprocess.run(command,capture_output=True,text=True,timeout=20)
            recorder.add('preexisting_domain',command=command,code=p.returncode,stdout=p.stdout,stderr=p.stderr)
            if p.returncode or any(n.startswith(('/paper_demo','/paper_turtle')) for n in p.stdout.splitlines()):
                raise RuntimeError('Domain/namespace collision or failed discovery')
        for i, command in enumerate(FIXTURES):
            f = (out/f'fixture-{i}.log').open('w')
            files.append(f)
            processes.append(subprocess.Popen(command,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,
                                               env=dict(os.environ,QT_QPA_PLATFORM='offscreen')))
            recorder.add('fixture_start',command=command,pid=processes[-1].pid)
        time.sleep(6)
        if any(p.poll() is not None for p in processes):
            raise RuntimeError('Fixture exited before readiness')
        # The shared ROS CLI daemon can discover nodes after the no-daemon
        # inventory. Require each ordinary node-info lookup to be ready before
        # collecting the independent baseline snapshot.
        for attempt in range(4):
            checks = []
            for node in NODES:
                p = subprocess.run(['ros2','node','info',node],capture_output=True,text=True,timeout=20)
                checks.append({'node':node,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
            recorder.add('readiness',attempt=attempt,checks=checks)
            if all(check['returncode'] == 0 for check in checks):
                break
            time.sleep(3)
        else:
            raise RuntimeError('CLI daemon did not discover every fixture')
        snapshot(out,'before')
        if args.phase == 'development':
            # Direct native mechanism smoke. This program is development-only and not a model response.
            rec = Recorder(out/'native-mechanism.jsonl')
            ros2.execute_ros_command = guarded_native(rec)
            program = ReadProgram({n:getattr(ros2,n) for n in READ_TOOLS},rec)
            code = "nodes = ros2_node_list(pattern='/paper_demo')\nfor n in nodes['nodes']:\n    ros2_param_get(node_name=n, param_name='use_sim_time')"
            save(out/'native-mechanism.json',{'code':code,'result':program.execute(code)})
            schedule = [('dev_t','C'), ('dev_d','C')]
        else:
            schedule = [(t['id'],arm) for t in config['heldout'] for arm in ['A','B','C']]
            random.Random(20261107).shuffle(schedule)
        save(out/'schedule.json',schedule)
        start = time.perf_counter()
        for index,(task,arm) in enumerate(schedule):
            if any(p.poll() is not None for p in processes):
                raise RuntimeError('Fixture exited during study')
            dest = out/f'{index:02d}-{task}-{arm}'
            cmd = [sys.executable,str(HERE/'run_study.py'),'--episode','--task',task,'--arm',arm,'--output',str(dest)]
            recorder.add('episode_launch',index=index,task=task,arm=arm)
            worker_started = time.perf_counter()
            with (out/f'{index:02d}-worker.log').open('w') as log:
                worker = subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    code = worker.wait(timeout=240)
                except subprocess.TimeoutExpired:
                    os.killpg(worker.pid,signal.SIGTERM)
                    try:
                        worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(worker.pid,signal.SIGKILL)
                        worker.wait()
                    code = 'timeout'
            recorder.add('episode_exit',index=index,code=code,worker_seconds=time.perf_counter()-worker_started)
        recorder.add('schedule_end',seconds=time.perf_counter()-start)
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
        for f in files:
            f.close()
        recorder.add('fixture_cleanup',exitcodes=[p.returncode for p in processes])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--episode',action='store_true')
    parser.add_argument('--task')
    parser.add_argument('--arm',choices=['A','B','C'])
    parser.add_argument('--phase',choices=['development','evaluation'])
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    episode(args) if args.episode else study(args)
