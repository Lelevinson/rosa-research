"""Frozen bounded native matrix. Run with Jazzy setup sourced; no model imports."""
import argparse
from collections import defaultdict
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import random
import resource
import select
import subprocess
import sys
import time
from types import SimpleNamespace

from executor import command, normalize, run_batch

ROOT = Path(__file__).resolve().parent
NAMES = {'node':[f'/nr11/n{i}' for i in range(4)],
         'topic':[f'/nr11/t{i}' for i in range(4)],
         'service':[f'/nr11/n{i}/get_parameters' for i in range(4)]}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    out=Path(args.out).resolve()
    out.mkdir(parents=True,exist_ok=False)
    os.environ.update(ROS_DOMAIN_ID='173',ROS_LOCALHOST_ONLY='1',ROS_LOG_DIR=str(out/'ros_logs'))
    started=time.perf_counter()
    deadline=started+240
    rng=random.Random(1111)
    journal=(out/'traces.jsonl').open('x')
    def log(kind,**kwargs):
        journal.write(json.dumps({'kind':kind,'time':time.perf_counter(),**kwargs})+'\n')
        journal.flush()
    files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
    files['PROTOCOL.md']=hashlib.sha256((ROOT/'PROTOCOL.md').read_bytes()).hexdigest()
    (out/'freeze.json').write_text(json.dumps({'files':files,'seed':1111,
        'environment':{k:os.environ.get(k) for k in ('ROS_DOMAIN_ID','ROS_DISTRO','RMW_IMPLEMENTATION','ROS_LOCALHOST_ONLY')},
        'python':sys.version,'executable':sys.executable,
        'packages':{name:importlib.metadata.version(name) for name in ['langchain','langchain-core','rosa-llm']}},indent=2))
    fixture=None
    owned_daemon=False
    batches=[]
    try:
        status=subprocess.run(['ros2','daemon','status'],capture_output=True,text=True,timeout=8)
        log('preexisting_daemon',stdout=status.stdout,stderr=status.stderr,returncode=status.returncode)
        if 'not running' not in status.stdout.lower():
            raise RuntimeError('Domain173 daemon may be in use; refusing fixture launch')
        fixture=subprocess.Popen([sys.executable,str(ROOT/'fixture.py')],stdout=subprocess.PIPE,
                                 stderr=(out/'fixture.stderr').open('w'),text=True)
        if not select.select([fixture.stdout],[],[],10)[0]:
            raise RuntimeError('Fixture did not become ready')
        line=fixture.stdout.readline()
        log('fixture_start',pid=fixture.pid,stdout=line)
        if 'FIXTURE_READY' not in line:
            raise RuntimeError('Fixture initialization failed')
        # Startup discovery is charged, not mixed into steady-state read timing.
        warm_start=time.perf_counter()
        owned_daemon=True
        subprocess.run(['ros2','daemon','start'],capture_output=True,text=True,timeout=8,check=True)
        time.sleep(1)
        log('setup_wait',seconds=time.perf_counter()-warm_start)
        pilot=run_batch('node',[NAMES['node'][0]],'serial')
        log('pilot',batch=pilot)
        if any(r['returncode'] for r in pilot['results']):
            raise RuntimeError('Native pilot failed')
        for family in NAMES:
            log('warmup',batch=run_batch(family,[NAMES[family][0]],'serial'))
            for repeat in range(2):
                policies=['serial','fixed2','fixed4','aimd']
                rng.shuffle(policies)
                for policy in policies:
                    if time.perf_counter()>deadline:
                        raise TimeoutError('Frozen wall cap exceeded')
                    batch=run_batch(family,NAMES[family],policy)
                    batch.update(repeat=repeat,phase='width')
                    batches.append(batch)
                    log('batch',batch=batch)
        for family in NAMES:
            names=[NAMES[family][0],'/nr11/missing',NAMES[family][0]]
            for policy in ['serial','fixed4']:
                batch=run_batch(family,names,policy)
                batch.update(phase='error_duplicate')
                batches.append(batch)
                log('batch',batch=batch)
        from ros2cli.node.strategy import NodeStrategy
        from ros2service.api import get_service_names_and_types
        import rclpy.utilities
        log('rmw',identifier=rclpy.utilities.get_rmw_implementation_identifier())
        persistent_start=time.perf_counter()
        with NodeStrategy(SimpleNamespace()) as node:
            log('persistent_setup',seconds=time.perf_counter()-persistent_start)
            def persistent(names):
                start=time.perf_counter()
                results=[]
                for i,name in enumerate(names):
                    command('service',name)
                    t=time.perf_counter()
                    pairs=get_service_names_and_types(node=node,include_hidden_services=False)
                    types=next((types for service,types in pairs if service==name),None)
                    results.append({'position':i,'name':name,'start':t,'end':time.perf_counter(),
                                    'stdout':'\n'.join(types)+'\n' if types else '',
                                    'stderr':'','returncode':0 if types else 1})
                return {'family':'service','policy':'persistent','phase':'transport',
                        'wall_seconds':time.perf_counter()-start,'results':results}
            for repeat in range(8):
                order=['serial','persistent']
                rng.shuffle(order)
                for policy in order:
                    batch=persistent(NAMES['service']) if policy=='persistent' else run_batch('service',NAMES['service'],'serial')
                    batch.update(repeat=repeat,phase='transport')
                    batches.append(batch)
                    log('batch',batch=batch)
            batch=persistent([NAMES['service'][0],'/nr11/missing',NAMES['service'][0]])
            batch['phase']='persistent_error'
            batches.append(batch)
            log('batch',batch=batch)
        log('persistent_lifetime',seconds=time.perf_counter()-persistent_start)
        # Full output equality only in this stable fixture, without answer semantics.
        comparisons=[]
        for batch in batches:
            if batch['phase']=='width' and batch['policy']!='serial':
                base=next(b for b in batches if b['phase']=='width' and b['policy']=='serial'
                          and b['family']==batch['family'] and b['repeat']==batch['repeat'])
            elif batch['phase']=='transport' and batch['policy']=='persistent':
                base=next(b for b in batches if b['phase']=='transport' and b['policy']=='serial' and b['repeat']==batch['repeat'])
            else:
                continue
            same=all(a['name']==b['name'] and a['returncode']==b['returncode']==0 and
                     normalize(a['stdout'])==normalize(b['stdout'])
                     for a,b in zip(base['results'],batch['results'])) and len(base['results'])==len(batch['results'])
            comparisons.append({'phase':batch['phase'],'family':batch['family'],'policy':batch['policy'],
                                'repeat':batch['repeat'],'equal_complete':same})
        (out/'comparisons.json').write_text(json.dumps(comparisons,indent=2))
        groups=defaultdict(lambda:{'batches':0,'wall_seconds':0.,'logical_reads':0,'failures':0,'policy_seconds':0.})
        for batch in batches:
            key='/'.join([batch['phase'],batch['family'],batch['policy']])
            group=groups[key]
            group['batches']+=1
            group['wall_seconds']+=batch['wall_seconds']
            group['policy_seconds']+=batch.get('policy_seconds',0)
            group['logical_reads']+=len(batch['results'])
            group['failures']+=sum(r['returncode']!=0 for r in batch['results'])
        (out/'summary.json').write_text(json.dumps(dict(groups),indent=2))
    except BaseException as exc:
        log('run_error',type=type(exc).__name__,error=str(exc))
        raise
    finally:
        if fixture is not None:
            fixture.terminate()
            try:
                fixture.wait(timeout=5)
            except subprocess.TimeoutExpired:
                fixture.kill()
                fixture.wait(timeout=3)
            log('fixture_cleanup',returncode=fixture.returncode)
        if owned_daemon:
            result=subprocess.run(['ros2','daemon','stop'],capture_output=True,text=True,timeout=8)
            log('daemon_cleanup',stdout=result.stdout,stderr=result.stderr,returncode=result.returncode)
        usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        log('run_end',wall_seconds=time.perf_counter()-started,
            children_user_cpu=usage.ru_utime,children_system_cpu=usage.ru_stime)
        journal.close()

if __name__=='__main__':
    main()
