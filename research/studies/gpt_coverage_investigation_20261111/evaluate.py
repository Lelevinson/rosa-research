"""Independent evaluation only; this module is never imported by the agent driver."""
import argparse
import importlib.util
import json
from pathlib import Path

spec=importlib.util.spec_from_file_location('nov11_field_scorer',Path(__file__).resolve().parents[1]/'action_narration_20261111/score.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
NODES={'/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator'}


def analyze(root):
    snapshots={p.name:json.loads(p.read_text()) for p in sorted(root.glob('oracle-*.json'))}
    assert snapshots and 'oracle-before.json' in snapshots and 'oracle-after.json' in snapshots
    inventories={name:all({n for n in obs['nodes'] if n.startswith(('/diag_demo/','/diag_turtle/'))}==NODES
                         for obs in value['inventories']) for name,value in snapshots.items()}
    truth={name:legacy.expected(value['records'],require_enumeration=False) for name,value in snapshots.items()}
    reference=next(iter(truth.values()))
    stable=all(legacy.normalize(value)==legacy.normalize(reference) for value in truth.values())
    oracle_valid=all(inventories.values()) and stable
    rows=[]
    for path in sorted(root.glob('[0-9][0-9]-*/trace.jsonl')):
        events=[json.loads(line) for line in path.read_text().splitlines()]
        start=next(e for e in events if e['kind']=='episode_start')
        end=next((e for e in events if e['kind']=='episode_end'),{})
        task=start['task']['id'];models=[e for e in events if e['kind']=='model_end']
        receipts=[e for e in events if e['kind']=='ros_end']
        successful={tuple(e['command']) for e in receipts if e['returncode']==0}
        actual,remainder=legacy.first_object(end.get('answer'))
        want=legacy.normalize(reference[task]);got=legacy.normalize(actual)
        wanted=legacy.leaves(want);delivered=legacy.leaves(got) if isinstance(got,dict) else {}
        fields={}
        for name,value in wanted.items():
            supported=True
            if task=='d1_recovery' and name.endswith('/use_sim_time'):
                endpoint=want['endpoints'][int(name.split('/')[2])]['node']
                supported=('ros2','param','get',endpoint,'use_sim_time') in successful
            elif task=='x1' and name.startswith('/clocks/'):
                endpoint=name[len('/clocks/'):]
                supported=('ros2','param','get',endpoint,'use_sim_time') in successful
            # Counts require actual verbose topic evidence; node interface names are insufficient.
            elif task=='d1_recovery':
                supported=('ros2','topic','info',want['topic'],'--verbose') in successful
            elif task=='x1':
                topic=name[len('/topics/'):].rsplit('/',1)[0]
                supported=('ros2','topic','info',topic,'--verbose') in successful
            correct=name in delivered and type(delivered[name]) is type(value) and delivered[name]==value
            fields[name]=dict(expected=value,actual=delivered.get(name),present=name in delivered,
                              value_correct=correct,acquisition_observed=supported,supported=correct and supported)
        stale=[e for e in receipts if e['command']==['ros2','node','info','/diag_demo/retired_source']]
        native_starts=[e for e in events if e['kind']=='ros_start']
        procedure=(task!='d1_recovery' or (len(stale)==1 and native_starts and
                    native_starts[0]['command']==['ros2','node','info','/diag_demo/retired_source']))
        actions=[e for e in models if e['message'].get('tool_calls')]
        finals=[e for e in models if not e['message'].get('tool_calls')]
        provider=[e['record'] for e in events if e['kind']=='provider_record']
        row=dict(episode=path.parent.name,provider=start['provider'],arm=start['arm'],task=task,
                 closed=bool(end),error=end.get('error'),answer=end.get('answer'),remainder=remainder,
                 fields=fields,oracle_valid=oracle_valid,procedure_satisfied=bool(procedure),
                 strict_value_match=got==want and all(v['value_correct'] for v in fields.values()),
                 supported_screen=got==want and all(v['supported'] for v in fields.values()) and bool(procedure) and oracle_valid,
                 manual_review_required=True,episode_seconds=end.get('seconds'),
                 model_attempts=sum(e['kind']=='model_start' for e in events),model_completions=len(models),
                 model_errors=sum(e['kind']=='model_error' for e in events),action_turns=len(actions),final_turns=len(finals),
                 action_words=sum(len(e['message']['content'].split()) for e in actions),
                 final_words=sum(len(e['message']['content'].split()) for e in finals),
                 proposed_tools=sum(len(e['message'].get('tool_calls',[])) for e in models),
                 tool_starts=sum(e['kind']=='tool_start' for e in events),tool_returns=sum(e['kind']=='tool_end' for e in events),
                 invalid_tool_calls=sum(len(e['message'].get('invalid_tool_calls',[])) for e in models),
                 native_attempts=sum(e['kind']=='ros_start' for e in events),native_completions=len(receipts),
                 native_successes=sum(e['returncode']==0 for e in receipts),
                 guard_rejections=sum(e['kind']=='guard_rejection' for e in events),
                 budget_rejections=sum(e['kind']=='budget_rejection' for e in events),
                 provider_attempts=len(provider),provider_completed=sum(e['status']=='completed' for e in provider),
                 http_seconds=sum(e.get('inference_http_elapsed_seconds',0) for e in provider),
                 provider_setup_seconds=sum(e.get('setup_elapsed_seconds',0) for e in provider),
                 stale_attempts=len(stale))
        for key in ['input_tokens','output_tokens']:
            row[key]=sum((e.get('usage') or {}).get(key,0) for e in models)
            row['action_'+key]=sum((e.get('usage') or {}).get(key,0) for e in actions)
            row['final_'+key]=sum((e.get('usage') or {}).get(key,0) for e in finals)
        row['reasoning_tokens']=sum((e['metadata'].get('usage',{}).get('output_tokens_details') or {}).get('reasoning_tokens',0) for e in models)
        row['cached_input_tokens']=sum((e['metadata'].get('usage',{}).get('input_tokens_details') or {}).get('cached_tokens',0) for e in models)
        row['reasoning_detail_reported']=all('reasoning_tokens' in (e['metadata'].get('usage',{}).get('output_tokens_details') or {}) for e in models)
        row['cache_detail_reported']=all('cached_tokens' in (e['metadata'].get('usage',{}).get('input_tokens_details') or {}) for e in models)
        row['ollama_durations_ns']={key:sum(e['metadata'].get(key,0) for e in models) for key in
            ['eval_duration','prompt_eval_duration','load_duration','total_duration']} if start['provider']=='ollama' else None
        rows.append(row)
    result=dict(oracle_valid=oracle_valid,inventory_checks=inventories,direct_values_stable=stable,
                cli_enumerations={name:value['records']['nodes']['stdout'] for name,value in snapshots.items()},
                episodes=rows,limits='Supported screen requires independent narrative/source adjudication; token reasoning details absent are not proof of zero hidden reasoning.')
    (root/'automatic_evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ['episode','strict_value_match','supported_screen','procedure_satisfied',
          'model_completions','output_tokens','native_attempts','episode_seconds']} for r in rows],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);analyze(p.parse_args().root)
