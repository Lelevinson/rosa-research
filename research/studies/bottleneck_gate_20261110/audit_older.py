"""Read preserved ZIP bytes only; never import historical experiment modules."""
import json, zipfile, hashlib, collections
from pathlib import Path
OUT=Path(__file__).parent
ARCH=Path('/home/levinsonchen/project/rosa-research-archive/research/raw/rosa-round28-external-review.zip')
def sha(b):return hashlib.sha256(b).hexdigest()
summary={};manifest=[];calls=[];episodes=[];models=[];proposals=[]
with zipfile.ZipFile(ARCH) as z:
 for rnd in (27,28):
  prefix=f'research/raw/round{rnd}-mission-v1/heldout-v1/episodes/'
  score=f'research/results/round{rnd}_heldout'+('_adjudicated' if rnd==28 else '')+'_audit.json'
  scorebytes=z.read(score);manifest.append({'member':score,'sha256':sha(scorebytes)})
  scores=json.loads(scorebytes)['rows'];scores={(r['task_id'],r['repeat'],r['arm']):r for r in scores}
  ss=[]
  for n in z.namelist():
   if not(n.startswith(prefix) and n.endswith('.json')):continue
   b=z.read(n);d=json.loads(b);manifest.append({'member':n,'sha256':sha(b)})
   score=scores[(d['task_id'],d['repeat'],d['arm'])]
   e={'round':rnd,'member':n,'task_id':d['task_id'],'arm':d['arm'],'request':d['request'],'answer':d.get('answer'),'errors':d.get('errors'),'model_records':len(d['models']),'model_tokens':sum((m.get('usage') or {}).get('total_tokens',0) for m in d['models'])}
   for k in ['native_complete','factual_complete','strict_supported_answer','exact_scope','missing_fields','unsupported_fields','compiled_fields','compiled_scope_exact','native_failed','tool_validation_errors','feasible']:e[k]=score.get(k)
   e['score_origin']='saved frozen automatic audit' if rnd==27 else 'saved post-closure adjudicated audit; automatic retained separately'
   episodes.append(e);ss.append(e)
   for mi,m in enumerate(d['models']):
    models.append({'round':rnd,'episode_member':n,'task_id':d['task_id'],'arm':d['arm'],'request':d['request'],'model_index':mi,'json_pointer':f'/models/{mi}','raw_record':m})
    for pi,p in enumerate(m.get('tool_calls',[])):
     args=p.get('args',p.get('arguments',{}))
     matches=[c.get('index') for c in d['calls'] if c.get('name')==p.get('name') and c.get('arguments',{})==args and c.get('started',float('-inf'))>=m.get('finished',float('inf'))]
     proposals.append({'round':rnd,'episode_member':n,'task_id':d['task_id'],'request':d['request'],'model_index':mi,'json_pointer':f'/models/{mi}/tool_calls/{pi}','raw_proposal':p,'model_finished':m.get('finished'),'usage':m.get('usage'),'later_exact_dispatch_candidates':matches,'match_boundary':'name/arguments/time screening only; compiler selection need not dispatch natively and matching does not prove causal identity'})
   seen=set();graph=[]
   for ci,c in enumerate(d['calls']):
    args=c.get('arguments',{});key=json.dumps([c.get('name'),args],sort_keys=True);out=c.get('output');native=out.get('native',{}) if isinstance(out,dict) else {};target=args.get('endpoint',args.get('topic'))
    grounds=[g for g in graph if target and any(x[0]==target for x in g[1].get('services',[])+g[1].get('topics',[]))]
    cr={'round':rnd,'episode_member':n,'index':c.get('index'),'tool':c.get('name'),'arguments':args,'started':c.get('started'),'finished':c.get('finished'),'allowed':c.get('allowed'),'same_arguments_previously_seen':key in seen,'same_time_equivalence':'unknown; distinct observations never equated','prior_graph_target_membership':bool(grounds) if target else None,'prior_graph_time':grounds[-1][0] if grounds else None,'incarnation_and_current_freshness':'unverifiable','native_ok':native.get('ok'),'native_error':native.get('error'),'error':c.get('error'),'accepted_fields':out.get('accepted_fields') if isinstance(out,dict) else None,'output_type':type(out).__name__}
    cr.update(request=d['request'],task_id=d['task_id'],json_pointer=f'/calls/{ci}',raw_dispatch=c,output=out,native=native)
    calls.append(cr);seen.add(key)
    if c.get('name')=='ros2_graph' and isinstance(native.get('response'),dict):graph.append((c.get('finished'),native['response']))
  arms={}
  for arm in sorted({e['arm'] for e in ss}):
   es=[e for e in ss if e['arm']==arm];arms[arm]={'episodes':len(es),'native_complete':sum(bool(e['native_complete']) for e in es),'factual_complete':sum(bool(e['factual_complete']) for e in es),'exact_scope':sum(bool(e['exact_scope']) for e in es),'strict_supported_answer':sum(bool(e['strict_supported_answer']) for e in es) if rnd==28 else None,'feasible':sum(e['feasible'] is True for e in es) if rnd==28 else None,'native_failed':sum(e['native_failed'] or 0 for e in es),'tool_validation_errors':sum(e['tool_validation_errors'] or 0 for e in es)}
   if rnd==28:arms[arm]['strict_supported_feasible']=sum(bool(e['strict_supported_answer']) and bool(e['factual_complete']) for e in es if e['feasible'])
  cs=[c for c in calls if c['round']==rnd];summary[str(rnd)]={'episodes':len(ss),'arms':arms,'calls':len(cs),'prior_same_arguments':sum(c['same_arguments_previously_seen'] for c in cs),'allowed_false':sum(c['allowed'] is False for c in cs),'native_ok_false':sum(c['native_ok'] is False for c in cs),'grounded_endpoint_calls':sum(c['prior_graph_target_membership'] is True for c in cs),'endpoint_calls':sum(c['prior_graph_target_membership'] is not None for c in cs)}
 for n in ['research/experiments/round27/heldout_tasks.json','research/experiments/round28/heldout_tasks.json','research/experiments/round27/audit_study.py','research/experiments/round28/audit_study.py','research/results/round28_answer_adjudication.json','research/results/round28_heldout_audit.json']:
  if n in z.namelist():manifest.append({'member':n,'sha256':sha(z.read(n))})
(OUT/'older_summary.json').write_text(json.dumps(summary,indent=2))
(OUT/'older_episodes.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in episodes))
(OUT/'older_calls.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in calls))
(OUT/'older_models.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in models))
(OUT/'older_model_proposals.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in proposals))
(OUT/'older_manifest.json').write_text(json.dumps({'archive':str(ARCH),'archive_sha256':hashlib.file_digest(ARCH.open('rb'),'sha256').hexdigest(),'members':manifest},indent=2))
print(json.dumps(summary,indent=2))
