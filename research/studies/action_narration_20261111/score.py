"""Evaluation only: native snapshot truth never imported by the runtime agent."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import yaml


def node_section(text, name):
    match = re.search(r'^  '+name+r':\n(.*?)(?=^  \S|\Z)', text, re.M | re.S)
    if match is None:
        raise ValueError('Missing native node-info section: '+name)
    return dict(re.findall(r'^    (\S+): (\S+)\s*$', match[1], re.M))


def expected(snapshot, require_enumeration=True):
    nodes = ['/diag_turtle/palette', '/diag_demo/source', '/diag_demo/listener', '/diag_demo/calculator']
    if require_enumeration:
        assert all(n in snapshot['nodes']['stdout'].splitlines() for n in nodes)
    # Direct observations are independently required even in diagnostic mode.
    for node in nodes:
        assert snapshot[node+':info']['returncode']==0
        assert snapshot[node+':info']['stdout'].splitlines()[0]==node
        assert snapshot[node+':params']['returncode']==0
    params = {n:yaml.safe_load(snapshot[n+':params']['stdout'])[n]['ros__parameters'] for n in nodes}
    turtle = '/diag_turtle/palette'
    pose = '/diag_turtle/turtle1/pose'
    chatter = '/diag_demo/chatter'
    def topic(name):
        text = snapshot[name+':info']['stdout']
        return dict(type=re.search(r'^Type: (.+)$', text, re.M)[1],
                    publishers=int(re.search(r'^Publisher count: (\d+)$', text, re.M)[1]))
    text = snapshot[chatter+':info']['stdout']
    endpoints = []
    for name, namespace, role in re.findall(r'Node name: ([^\n]+)\nNode namespace: ([^\n]+).*?Endpoint type: (PUBLISHER|SUBSCRIPTION)', text, re.S):
        node = namespace.rstrip('/')+'/'+name
        endpoints.append(dict(node=node, role='publisher' if role == 'PUBLISHER' else 'subscriber',
                              use_sim_time=params[node]['use_sim_time']))
    assert len(endpoints) == 2
    return {
        't1':dict(node=turtle, rgb=[params[turtle]['background_'+c] for c in 'rgb'],
                  pose=dict(topic=pose, **topic(pose))),
        't3':dict(node=turtle, **{key:{t:v for t,v in node_section(snapshot[turtle+':info']['stdout'], section).items()
                                     if t not in ['/rosout','/parameter_events']}
                                  for key,section in [('publishers','Publishers'),('subscribers','Subscribers')]}),
        'd1_recovery':dict(topic=chatter, **topic(chatter),
                            subscribers=int(re.search(r'^Subscription count: (\d+)$', text, re.M)[1]),
                            endpoints=endpoints),
        'x1':dict(clocks={n:params[n]['use_sim_time'] for n in nodes},
                  topics={n:topic(n) for n in [pose,chatter]})}


def normalize(value):
    if isinstance(value, dict): return {k:normalize(v) for k,v in value.items()}
    if isinstance(value, list):
        values = [normalize(v) for v in value]
        return sorted(values, key=lambda v:(v['node'],v.get('role',''))) if values and all(isinstance(v,dict) and 'node' in v for v in values) else values
    return value


def leaves(value, prefix=''):
    if isinstance(value, dict):
        return {k:v for key,child in value.items() for k,v in leaves(child,prefix+'/'+key).items()}
    if isinstance(value,list):
        return {k:v for i,child in enumerate(value) for k,v in leaves(child,prefix+'/'+str(i)).items()}
    return {prefix:value}


def first_object(text):
    for match in re.finditer(r'\{', text or ''):
        try:
            value,end = json.JSONDecoder().raw_decode(text[match.start():])
            if isinstance(value,dict): return value, text[:match.start()]+text[match.start()+end:]
        except ValueError: pass
    return None, text


def analyze(root, diagnostic=False):
    raw_snapshots = {p.name:json.loads(p.read_text()) for p in sorted(root.glob('oracle-*.json'))}
    expected_nodes = {'/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator'}
    enumeration = {name: expected_nodes.issubset(set(value['nodes']['stdout'].splitlines()))
                   for name,value in raw_snapshots.items()}
    snapshots = {name:expected(value, require_enumeration=not diagnostic) for name,value in raw_snapshots.items()}
    if not snapshots: raise ValueError('No native scoring oracle')
    truth = next(iter(snapshots.values()))
    stable = all(normalize(v) == normalize(truth) for v in snapshots.values())
    records = []
    for p in sorted(root.glob('[0-9][0-9]-*/trace.jsonl')):
        events = [json.loads(line) for line in p.read_text().splitlines()]
        start = next(e for e in events if e['kind'] == 'episode_start')
        end = next((e for e in events if e['kind'] == 'episode_end'), {})
        model = [e for e in events if e['kind'] == 'model_end']
        native = [e for e in events if e['kind'] == 'ros_end']
        actual, remainder = first_object(end.get('answer'))
        want = normalize(truth[start['task']['id']])
        got = normalize(actual)
        wanted_fields = leaves(want)
        actual_fields = leaves(got) if isinstance(got,dict) else {}
        fields = {key:dict(expected=value, actual=actual_fields.get(key),
                           present=key in actual_fields,
                           correct=key in actual_fields and type(actual_fields[key]) is type(value) and actual_fields[key] == value)
                  for key,value in wanted_fields.items()}
        actions = [m for m in model if m['message'].get('tool_calls')]
        finals = [m for m in model if not m['message'].get('tool_calls')]
        row = dict(episode=p.parent.name, task=start['task']['id'], arm=start['arm'],
                   oracle_stable=stable,
                   enumeration_indeterminate=start['task']['id']=='x1' and not all(enumeration.values()),
                   strict_values=got == want and all(v['correct'] for v in fields.values()) and stable
                       and (start['task']['id']!='x1' or all(enumeration.values())),
                   fields=fields, extra_fields=sorted(set(actual_fields)-set(wanted_fields)),
                   remainder=remainder, answer=end.get('answer'), error=end.get('error'),
                   closed=bool(end), episode_seconds=end.get('seconds'),
                   model_calls=len(model), model_attempts=sum(e['kind']=='model_start' for e in events),
                   model_errors=sum(e['kind']=='model_error' for e in events),
                   action_turns=len(actions), final_turns=len(finals),
                   action_words=sum(len(m['message']['content'].split()) for m in actions),
                   final_words=sum(len(m['message']['content'].split()) for m in finals),
                   tool_calls=sum(len(m['message'].get('tool_calls',[])) for m in model),
                   tool_starts=sum(e['kind']=='tool_start' for e in events),
                   tool_returns=sum(e['kind']=='tool_end' for e in events),
                   invalid_tool_calls=sum(len(m['message'].get('invalid_tool_calls',[])) for m in model),
                   native_attempts=sum(e['kind']=='ros_start' for e in events),
                   native_completions=len(native), native_success=sum(e['returncode']==0 for e in native),
                   guard_rejections=sum(e['kind']=='guard_rejection' for e in events),
                   budget_rejections=sum(e['kind']=='budget_rejection' for e in events),
                   serialization_seconds=sum(e.get('serialization_seconds',0) for e in events),
                   schema_hashes=sorted({e['schema_hash'] for e in events if e['kind']=='model_start'}),
                   hidden_reasoning_present=any(m['message'].get('additional_kwargs',{}).get('reasoning_content') for m in model))
        for key in ['total_duration','eval_duration','prompt_eval_duration','load_duration','prompt_eval_count','eval_count']:
            row[key] = sum(m['metadata'].get(key,0) for m in model)
            row['action_'+key] = sum(m['metadata'].get(key,0) for m in actions)
            row['final_'+key] = sum(m['metadata'].get(key,0) for m in finals)
        records.append(row)
    summary = {}
    for arm in 'ABC':
        rows = [r for r in records if r['arm']==arm]
        summary[arm] = dict(episodes=len(rows), strict_values=sum(r['strict_values'] for r in rows))
        for key in ['model_calls','model_attempts','model_errors','action_turns','final_turns','action_words','final_words',
                    'tool_calls','tool_starts','tool_returns','native_attempts','native_completions','native_success',
                    'invalid_tool_calls','guard_rejections','budget_rejections','episode_seconds','serialization_seconds',
                    'eval_count','prompt_eval_count','eval_duration','prompt_eval_duration','load_duration','total_duration',
                    'action_eval_count','final_eval_count','action_eval_duration','final_eval_duration']:
            summary[arm][key] = sum(r.get(key) or 0 for r in rows)
    result = dict(oracle_stable=stable, oracle_count=len(snapshots), episodes=records, summary=summary,
                  diagnostic_mode=diagnostic, enumeration_complete=enumeration,
                  protocol_closeout_valid=all(enumeration.values()),
                  limits='Automatic values/format screen only. Semantic/source support and unsupported narrative require independent trace adjudication.')
    (root/'automatic_scores.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root',type=Path)
    parser.add_argument('--diagnostic',action='store_true',help='Postexecution amendment: preserve failed enumeration and score direct fields separately; not a protocol-complete result')
    args=parser.parse_args()
    analyze(args.root,args.diagnostic)
