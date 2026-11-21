"""Offline evaluation and diagnostic indexing. Truth is never sent to the agent."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import yaml


def load(path):
    return json.loads(path.read_text())


def node_topics(text, section):
    match = re.search(r'^  '+section+r':\n(.*?)(?=^  \S|\Z)', text, re.M|re.S)
    if not match:
        raise ValueError('Missing node-info section: '+section)
    return dict(re.findall(r'^    (\S+): (\S+)\s*$', match[1], re.M))


def expected(snapshot):
    def raw(key):
        return snapshot[key]['stdout']
    # Direct node-info identities corroborate values even if enumeration is incomplete.
    # Enumeration validity is tracked separately and never silently repaired.
    nodes = [record['stdout'].splitlines()[0] for key,record in snapshot.items()
             if key.endswith(':info') and record['command'][1:3]==['node','info']
             and record['returncode']==0 and record['stdout'].startswith('/')]
    nodes = sorted(set(nodes))
    params = {n:yaml.safe_load(raw(n+':params'))[n]['ros__parameters'] for n in nodes}
    turtle = '/diag_turtle/palette'
    calculator = '/diag_demo/calculator'
    pose = '/diag_turtle/turtle1/pose'
    chatter = '/diag_demo/chatter'
    def topic(name):
        text = raw(name+':info')
        return {'type':re.search(r'^Type: (.+)$',text,re.M)[1],
                'publishers':int(re.search(r'^Publisher count: (\d+)$',text,re.M)[1])}
    def services(names):
        return {s:raw(s+':type').strip() for s in names}
    endpoints = []
    role = None
    for block in raw(chatter+':info').split('\n\n'):
        if 'Endpoint type: PUBLISHER' in block:
            role='publisher'
        elif 'Endpoint type: SUBSCRIPTION' in block:
            role='subscriber'
        else:
            continue
        name = re.search(r'^Node name: (.+)$',block,re.M)[1]
        namespace = re.search(r'^Node namespace: (.+)$',block,re.M)[1]
        node = namespace.rstrip('/')+'/'+name
        endpoints.append({'node':node,'role':role,'use_sim_time':params[node]['use_sim_time']})
    # Endpoint fields often share one block with header; each is still native truth.
    if len(endpoints) != 2:
        endpoints=[]
        for name, namespace, role in re.findall(r'Node name: ([^\n]+)\nNode namespace: ([^\n]+).*?Endpoint type: (PUBLISHER|SUBSCRIPTION)',raw(chatter+':info'),re.S):
            node=namespace.rstrip('/')+'/'+name
            endpoints.append({'node':node,'role':'publisher' if role=='PUBLISHER' else 'subscriber',
                              'use_sim_time':params[node]['use_sim_time']})
    standard = {'describe_parameters','get_parameter_types','get_parameters','list_parameters','set_parameters','set_parameters_atomically'}
    info = raw(calculator+':info')
    calc_services = node_topics(info,'Service Servers')
    calc_services = {s:t for s,t in calc_services.items() if s.rsplit('/',1)[-1] not in standard}
    return {
      't1':{'node':turtle,'rgb':[params[turtle][p] for p in ['background_r','background_g','background_b']],
            'pose':{'topic':pose,**topic(pose)}},
      't2':{'node':turtle,'services':services(['/diag_turtle/clear','/diag_turtle/reset']),
            'use_sim_time':params[turtle]['use_sim_time']},
      't3':{'node':turtle,**{key:{s:t for s,t in node_topics(raw(turtle+':info'),section).items()
                                  if s not in ['/rosout','/parameter_events']}
                            for key,section in [('publishers','Publishers'),('subscribers','Subscribers')]}},
      'd1':{'topic':chatter,**topic(chatter),
            'subscribers':int(re.search(r'^Subscription count: (\d+)$',raw(chatter+':info'),re.M)[1]),
            'endpoints':endpoints},
      'd2':{'node':calculator,'services':calc_services,'use_sim_time':params[calculator]['use_sim_time']},
      'x1':{'clocks':{n:params[n]['use_sim_time'] for n in nodes},'topics':{t:topic(t) for t in [pose,chatter]}}
    }


def first_object(answer):
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{',answer or ''):
        try:
            value,end = decoder.raw_decode(answer[match.start():])
            return value,answer[:match.start()]+answer[match.start()+end:]
        except ValueError:
            continue
    return None,answer


def canonical(value):
    if isinstance(value,dict):
        return {k:canonical(v) for k,v in sorted(value.items())}
    if isinstance(value,list):
        result=[canonical(v) for v in value]
        # Endpoints are an unordered set; RGB remains ordered.
        if result and all(isinstance(v,dict) and 'node' in v for v in result):
            return sorted(result,key=lambda v:(v['node'],v.get('role','')))
        return result
    return value


def differences(actual,truth,path=''):
    if isinstance(truth,dict):
        if not isinstance(actual,dict):
            return [path+': expected object']
        out=[]
        for key in truth:
            out += [path+'/'+key+': missing'] if key not in actual else differences(actual[key],truth[key],path+'/'+key)
        for key in actual.keys()-truth.keys():
            out.append(path+'/'+key+': extra field')
        return out
    if isinstance(truth,list):
        if not isinstance(actual,list) or len(actual)!=len(truth):
            return [path+': wrong list length/type']
        return [error for i,(a,t) in enumerate(zip(actual,truth)) for error in differences(a,t,path+'/'+str(i))]
    if type(actual)!=type(truth) or actual!=truth:
        return [path+': '+repr(actual)+' != '+repr(truth)]
    return []


def audit(out):
    snapshots={p.parent.name:load(p) for p in sorted((out/'oracle').glob('*/snapshot.json'))}
    truths={label:expected(data) for label,data in snapshots.items()}
    initial_nodes=set(snapshots['before']['nodes']['stdout'].splitlines())
    enumeration_stable={label:set(data['nodes']['stdout'].splitlines())==initial_nodes
                        for label,data in snapshots.items()}
    initial=truths['before']
    stability={label:canonical(truth)==canonical(initial) for label,truth in truths.items()}
    records=[]
    for attempt in (out/'attempts.jsonl').read_text().splitlines():
        row=json.loads(attempt)
        directory=out/row['directory']
        trace=directory/'trace.jsonl'
        events=[dict(json.loads(line),line=i) for i,line in enumerate(trace.read_text().splitlines(),1)] if trace.exists() else []
        answer=load(directory/'answer.json') if (directory/'answer.json').exists() else {'answer':None,'error':'no final answer'}
        parsed,extra=first_object(answer['answer'])
        issues=differences(canonical(parsed),canonical(initial[row['task']]))
        model=[e for e in events if e['kind']=='model_end']
        native=[e for e in events if e['kind'] in ['ros_end','ros_error']]
        starts=[e for e in events if e['kind']=='tool_start']
        repeats=[]
        prior={}
        for e in native:
            key=json.dumps(e['command'])
            if key in prior:
                repeats.append({'line':e['line'],'prior_line':prior[key]['line'],
                                'command':e['command'],'prior_success':prior[key].get('returncode')==0,
                                'current_success':e.get('returncode')==0,'seconds':e.get('seconds')})
            prior[key]=e
        block_end='after-'+str(((row['index']//6)+1)*6).zfill(2)
        inventory_indeterminate=row['task']=='x1' and not enumeration_stable.get(block_end,False)
        row.update(inventory_indeterminate=inventory_indeterminate,answer=answer['answer'],error=answer['error'] or row['error'],issues=issues,
                   semantic_exact=not issues and all(canonical(truth[row['task']])==canonical(initial[row['task']]) for truth in truths.values()),
                   pure_json=parsed is not None and not (extra or '').strip(),
                   model_calls=sum(e['kind']=='model_start' for e in events),model_completed=len(model),
                   model_errors=sum(e['kind']=='model_error' for e in events),
                   token_usage_complete=all(e.get('usage') for e in model) and len(model)==sum(e['kind']=='model_start' for e in events),
                   input_tokens=sum((e.get('usage') or {}).get('input_tokens',0) for e in model),
                   output_tokens=sum((e.get('usage') or {}).get('output_tokens',0) for e in model),
                   model_seconds=sum(e['seconds'] for e in model),tools=len(starts),
                   batch_dispatches=sum(e['kind']=='batch_dispatch' for e in events),
                   native_attempts=sum(e['kind']=='ros_start' for e in events),native_completed=len(native),
                   native_unresolved=sum(e['kind']=='ros_start' for e in events)-len(native),native_failures=sum(e.get('returncode',1)!=0 for e in native),
                   native_seconds=sum(e.get('seconds',0) for e in native),repeats=repeats,
                   tool_errors=[{'line':e['line'],'error':e.get('error')} for e in events if e['kind']=='tool_error'])
        records.append(row)
    results={'oracle_stable':stability,'enumeration_stable':enumeration_stable,
             'closeout_failure':('after-36 discovery incomplete despite successful direct reads; final after snapshot absent'
                                 if not enumeration_stable.get('after-36',False) and 'after' not in snapshots else None),
             'truth':initial,'episodes':records}
    (out/'automatic-audit.json').write_text(json.dumps(results,indent=2))
    print(json.dumps({'oracle_stable':stability,'episodes':len(records),
          'arms':{a:{'episodes':sum(r['arm']==a for r in records),
                     'exact':sum(r['semantic_exact'] for r in records if r['arm']==a),
                     'models':sum(r['model_calls'] for r in records if r['arm']==a)} for a in ['A','B','C']}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    audit(parser.parse_args().output)
