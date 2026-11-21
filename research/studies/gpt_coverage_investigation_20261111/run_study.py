"""Bounded provider/prompt diagnostic using actual ROSA and ChatRosaLLM."""
import argparse
import asyncio
from dataclasses import replace
import importlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import urllib.request

sys.path.append('/usr/lib/python3/dist-packages')
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if p.name == 'research').parent
legacy_spec=importlib.util.spec_from_file_location('nov11_action_driver',HERE.parent/'action_narration_20261111/run_study.py')
previous=importlib.util.module_from_spec(legacy_spec)
legacy_spec.loader.exec_module(previous)

from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.utils.function_calling import convert_to_openai_tool
from rosa.rosa import ROSA
from rosa_llm import Config, create_client, package_info
from rosa_llm.langchain import ChatRosaLLM
from rosa_llm.errors import LLMError

Journal=previous.Journal
save=previous.save
FIXTURE_NODES={'/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator'}


class EvaluationROSA(ROSA):
    """Isolate prompts/read tools, preserving ROSA's model/agent/executor methods."""
    def __init__(self,model,tools,messages,max_iterations):
        self.study_messages=messages
        super().__init__(ros_version=2,llm=model,tools=tools,streaming=False,
            accumulate_chat_history=False,max_iterations=max_iterations,return_intermediate_steps=True)

    def _get_tools(self,ros_version,packages,tools,blacklist):
        assert {t.name for t in tools}==set(previous.READS) and len(tools)==len(previous.READS)
        # ROSA's blacklist filters entities, not registered tools. Explicit registry isolation.
        return SimpleNamespace(get_tools=lambda:tools)

    def _get_prompts(self,robot_prompts=None):
        return ChatPromptTemplate.from_messages(self.study_messages+[
            MessagesPlaceholder('chat_history'),('human','{input}'),MessagesPlaceholder('agent_scratchpad')])


class MeasuredModel(BaseChatModel):
    underlying: object
    journal: object
    options: dict

    @property
    def _llm_type(self):return 'measured-chatrosallm'

    def bind_tools(self,tools,**kwargs):
        return self.bind(tools=[convert_to_openai_tool(t) for t in tools],**kwargs)

    def _generate(self,messages,stop=None,run_manager=None,**kwargs):
        schemas=kwargs.pop('tools')
        self.journal.add('model_start',messages=[m.model_dump() for m in messages],
            schemas=schemas,schema_hash=previous.digest(schemas),options=self.options)
        started=time.perf_counter()
        try:
            answer=self.underlying.bind_tools(schemas).invoke(messages,stop=stop,**self.options)
        except Exception as error:
            detail=error.to_dict() if isinstance(error,LLMError) else {'type':type(error).__name__,'message':str(error)}
            self.journal.add('model_error',error=detail,seconds=time.perf_counter()-started)
            raise
        self.journal.add('model_end',message=answer.model_dump(),usage=answer.usage_metadata,
                         metadata=answer.response_metadata,seconds=time.perf_counter()-started)
        return ChatResult(generations=[ChatGeneration(message=answer)])


def model_config(provider,protocol):
    setting=protocol['providers'][provider]
    if provider=='openai':
        return replace(Config.load(),provider='openai',openai_model=setting['model'],
                       require_explicit_model=True,timeout=90)
    return Config(provider='ollama',ollama_model=setting['model'],
                  ollama_base_url=setting['base_url'],timeout=90)


async def episode(destination,provider,arm,task,protocol):
    destination.mkdir(exist_ok=False)
    journal=Journal(destination/'trace.jsonl')
    journal.add('episode_start',provider=provider,arm=arm,task=task)
    tools=previous.make_tools(journal)
    config=model_config(provider,protocol)
    def observe(record):journal.add('provider_record',record=record)
    started=time.perf_counter()
    answer=error=None
    with create_client(config,observer=observe) as client:
        base=ChatRosaLLM(client=client,allowed_tools=frozenset(previous.READS),cache=False)
        options=protocol['providers'][provider]['options']
        llm=MeasuredModel(underlying=base,journal=journal,options=options,cache=False)
        systems=previous.prompts(arm,protocol)
        rosa=EvaluationROSA(llm,tools,systems,3 if task['id']=='activation' else 10)
        save(destination/'configuration.json',dict(provider=provider,arm=arm,config=config.to_dict(),
             options=options,prompts=systems,schemas=[convert_to_openai_tool(t) for t in tools],package=package_info()))
        try:
            result=await rosa._ROSA__executor.ainvoke({'input':task['request'],'chat_history':[]})
            answer=result['output']
            save(destination/'intermediate_steps.json',[dict(action=a.model_dump(),observation=o)
                 for a,o in result['intermediate_steps']])
        except Exception as failure:
            error=failure.to_dict() if isinstance(failure,LLMError) else {'type':type(failure).__name__,'message':str(failure)}
    journal.add('episode_end',answer=answer,error=error,seconds=time.perf_counter()-started)
    save(destination/'answer.json',dict(provider=provider,arm=arm,task=task['id'],answer=answer,error=error))


class OracleGraph:
    def __init__(self):
        import rclpy
        from rclpy.context import Context
        from rclpy.executors import SingleThreadedExecutor
        self.context=Context()
        rclpy.init(context=self.context)
        self.node=rclpy.create_node('_coverage_oracle',namespace='/evaluation',context=self.context)
        self.executor=SingleThreadedExecutor(context=self.context)
        self.executor.add_node(self.node)
        self.thread=threading.Thread(target=self.executor.spin,daemon=True)
        self.thread.start()

    def names(self):
        return sorted(ns.rstrip('/')+'/'+name for name,ns in self.node.get_node_names_and_namespaces())

    def close(self):
        self.executor.shutdown(timeout_sec=3)
        self.thread.join(timeout=3)
        self.node.destroy_node()
        self.context.shutdown()


def snapshot(destination,graph):
    inventories=[]
    for index in range(2):
        inventories.append(dict(monotonic=time.perf_counter(),nodes=graph.names()))
        if index==0:time.sleep(.3)
    commands={'nodes':['node','list','--no-daemon','--spin-time','3'],
              'topics':['topic','list'],'services':['service','list']}
    for node in sorted(FIXTURE_NODES):
        commands[node+':info']=['node','info',node]
        commands[node+':params']=['param','dump',node]
    for topic in ['/diag_turtle/turtle1/pose','/diag_turtle/turtle1/cmd_vel',
                  '/diag_turtle/turtle1/color_sensor','/diag_demo/chatter']:
        commands[topic+':info']=['topic','info',topic,'--verbose']
    commands['stale_node']=['node','info','/diag_demo/retired_source']
    records={}
    for key,argv in commands.items():
        started=time.perf_counter()
        try:
            p=subprocess.run(['ros2',*argv],capture_output=True,text=True,timeout=20)
            value=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        except subprocess.TimeoutExpired:
            value=dict(returncode=None,stdout='',stderr='Evaluation native timeout',timeout=True)
        records[key]=dict(command=['ros2',*argv],seconds=time.perf_counter()-started,**value)
    result=dict(inventories=inventories,records=records)
    save(destination,result)
    assert all({n for n in obs['nodes'] if n.startswith(('/diag_demo/','/diag_turtle/'))}==FIXTURE_NODES
               for obs in inventories),'Persistent inventory incomplete'
    assert all(v['returncode']==0 for k,v in records.items() if k!='stale_node'),'Direct oracle failed'
    assert records['stale_node']['returncode']==1 and 'Unable to find node' in records['stale_node']['stderr'], 'Absence not established'


def freeze(out):
    source=out/'source'
    for relative in ['src/rosa','research/studies/action_narration_20261111','research/studies/gpt_coverage_investigation_20261111']:
        shutil.copytree(ROOT/relative,source/relative,ignore=shutil.ignore_patterns('__pycache__'))
    import rosa_llm
    shutil.copytree(Path(inspect.getfile(rosa_llm)).parent,source/'installed_rosa_llm',
                    ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['AGENTS.md','pyproject.toml','uv.lock','research/ROSA_RESEARCH_CONTEXT.md']:
        target=source/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/name,target)
    for name in ['langchain.agents.agent','langchain_core.language_models.chat_models']:
        module=importlib.import_module(name)
        shutil.copy2(inspect.getfile(module),source/(name+'.py'))
    import hashlib
    save(out/'freeze.json',dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
         sha256={str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in source.rglob('*') if p.is_file()}))


def worker(out,provider,arm,task,journal):
    command=[sys.executable,str(HERE/'run_study.py'),'--episode','--provider',provider,
             '--arm',arm,'--task',task,'--output',str(out)]
    journal.add('worker_start',command=command)
    with out.with_suffix('.log').open('w') as log:
        p=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:code=p.wait(timeout=240)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid,signal.SIGKILL);p.wait()
            code=p.returncode
            journal.add('worker_timeout',provider=provider,arm=arm,task=task)
    journal.add('worker_end',provider=provider,arm=arm,task=task,returncode=code)
    return code


def provider_metadata(out,protocol):
    for suffix in ['tags','version','ps']:
        with urllib.request.urlopen(protocol['providers']['ollama']['base_url']+'/api/'+suffix,timeout=10) as response:
            save(out/('ollama-'+suffix+'.json'),json.load(response))
    tags=json.loads((out/'ollama-tags.json').read_text())
    setting=protocol['providers']['ollama']
    assert any(m['name']==setting['model'] and m['digest']==setting['digest'] for m in tags['models'])
    with create_client(model_config('openai',protocol)) as client:
        catalog=client.models()
        save(out/'openai-catalog.json',catalog)
        assert protocol['providers']['openai']['model'] in {m['id'] for m in catalog}


def run(out,protocol,mode):
    assert os.environ.get('ROS_DOMAIN_ID')=='175' and os.environ.get('ROS_LOCALHOST_ONLY')=='1'
    out.mkdir(parents=True,exist_ok=False)
    freeze(out)
    journal=Journal(out/'setup.jsonl')
    save(out/'identity.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
         status=subprocess.check_output(['git','status','--short'],text=True),package=package_info(),
         environment={k:os.environ.get(k) for k in ['ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY','ROS_DISTRO']},mode=mode))
    provider_metadata(out,protocol)
    commands=[
        ['ros2','run','turtlesim','turtlesim_node','--ros-args','-r','__ns:=/diag_turtle','-r','__node:=palette',
         '-p','background_r:=37','-p','background_g:=83','-p','background_b:=129'],
        ['ros2','run','demo_nodes_cpp','talker','--ros-args','-r','__ns:=/diag_demo','-r','__node:=source'],
        ['ros2','run','demo_nodes_cpp','listener','--ros-args','-r','__ns:=/diag_demo','-r','__node:=listener'],
        ['ros2','run','demo_nodes_cpp','add_two_ints_server','--ros-args','-r','__ns:=/diag_demo','-r','__node:=calculator']]
    processes=[];handles=[];graph=None
    try:
        p=subprocess.run(['ros2','node','list','--no-daemon','--spin-time','2'],capture_output=True,text=True,timeout=15)
        journal.add('collision_check',stdout=p.stdout,stderr=p.stderr,returncode=p.returncode)
        assert p.returncode==0 and not p.stdout.strip(),'Disposable domain occupied'
        graph=OracleGraph()
        journal.add('oracle_graph_opened')
        for index,command in enumerate(commands):
            handle=(out/f'fixture-{index}.log').open('w');handles.append(handle)
            p=subprocess.Popen(command,stdout=handle,stderr=subprocess.STDOUT,start_new_session=True,
                               env=dict(os.environ,QT_QPA_PLATFORM='offscreen'))
            processes.append(p);journal.add('fixture_start',command=command,pid=p.pid)
        time.sleep(5)
        snapshot(out/'oracle-before.json',graph)
        if mode=='activation':schedule=[('openai','A','activation'),('ollama','A','activation')]
        else:
            schedule=[(provider,arm,task['id']) for provider in ['openai','ollama']
                      for task in protocol['tasks'] for arm in ['A','B']]
            schedule += [(provider,'V','d1_recovery') for provider in ['openai','ollama']]
            random.Random(protocol['order_seed']).shuffle(schedule)
        save(out/'schedule.json',schedule)
        started=time.perf_counter()
        attempted=0
        for index,(provider,arm,task) in enumerate(schedule):
            if time.perf_counter()-started>2400:
                journal.add('budget_stop',unattempted=len(schedule)-index);break
            assert all(p.poll() is None for p in processes),'Fixture process exited'
            destination=out/f'{index:02d}-{provider}-{task}-{arm}'
            attempted+=1
            code=worker(destination,provider,arm,task,journal)
            print(json.dumps(dict(index=index,provider=provider,arm=arm,task=task,returncode=code)),flush=True)
            if mode=='activation':
                assert code==0,'Activation worker failed'
                events=[json.loads(l) for l in (destination/'trace.jsonl').read_text().splitlines()]
                models=[e for e in events if e['kind']=='model_end']
                assert models and not models[-1]['message'].get('tool_calls'),'No final turn'
                assert any(len(e['message'].get('tool_calls',[]))>=2 for e in models),'No native multicall'
                assert sum(e['kind']=='ros_end' and e['returncode']==0 for e in events)>=3,'Native activation failed'
                assert any(e['kind']=='tool_start' and len(e['arguments'].get('nodes',[]))==2 for e in events),'List argument not used'
                assert not any(e['kind']=='model_error' for e in events),'Model activation error'
                if provider=='ollama':
                    with urllib.request.urlopen(protocol['providers']['ollama']['base_url']+'/api/ps',timeout=10) as response:
                        active=json.load(response)
                    save(out/'ollama-active-context.json',active)
                    assert any(m['name']==protocol['providers']['ollama']['model'] and m['context_length']==16384 for m in active['models']),'Context repair not active'
                journal.add('activation_passed',provider=provider)
            if (index+1)%2==0:snapshot(out/f'oracle-after-{index+1:02d}.json',graph)
        snapshot(out/'oracle-after.json',graph)
        provider_metadata(out/'metadata-after',protocol)
        journal.add('study_closed' if attempted==len(schedule) else 'study_incomplete',
                    cells_attempted=attempted,cells_scheduled=len(schedule))
    except Exception as error:
        journal.add('study_error',error=repr(error));raise
    finally:
        for p in processes:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGINT)
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(p.pid,signal.SIGKILL);p.wait()
            journal.add('fixture_stop',pid=p.pid,returncode=p.returncode)
        if graph:
            graph.close();journal.add('oracle_graph_closed')
        for handle in handles:handle.close()
        p=subprocess.run(['ros2','daemon','stop'],capture_output=True,text=True,timeout=15)
        journal.add('daemon_stop',returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=['activation','primary'],default='activation')
    p.add_argument('--episode',action='store_true');p.add_argument('--provider',choices=['openai','ollama'])
    p.add_argument('--arm',choices=['A','B','V']);p.add_argument('--task')
    args=p.parse_args();protocol=json.loads((HERE/'cases.json').read_text())
    if args.episode:
        task=previous.ACTIVATION if args.task=='activation' else next(t for t in protocol['tasks'] if t['id']==args.task)
        asyncio.run(episode(args.output,args.provider,args.arm,task,protocol))
    else:run(args.output,protocol,args.mode)
