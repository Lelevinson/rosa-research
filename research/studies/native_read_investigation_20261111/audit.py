"""Independent offline checks from raw journals; never launches ROS or models."""
from collections import Counter
import json
from pathlib import Path
import sys

def lines(text):
    return Counter(s.strip() for s in text.splitlines() if s.strip())

def audit(path):
    events=[json.loads(s) for s in (path/'traces.jsonl').read_text().splitlines()]
    batches=[e['batch'] for e in events if e['kind']=='batch']
    width=[b for b in batches if b['phase']=='width']
    assert len(width) in (0,24)
    if not width:
        assert sum(b['phase']=='transport' for b in batches)==16
    checks=[]
    for batch in batches:
        results=batch['results']
        assert [r['position'] for r in results]==list(range(len(results)))
        if batch['phase'] in ('error_duplicate','persistent_error'):
            assert [r['returncode']==0 for r in results]==[True,False,True]
        else:
            assert all(r['returncode']==0 for r in results)
        ticks=sorted([(r['start'],1) for r in results]+[(r['end'],-1) for r in results])
        active=peak=0
        for _,delta in ticks:
            active+=delta
            peak=max(peak,active)
        cap={'serial':1,'fixed2':2,'fixed4':4,'aimd':4,'persistent':1}[batch['policy']]
        assert peak<=cap
        checks.append({'phase':batch['phase'],'family':batch['family'],'policy':batch['policy'],
                       'repeat':batch.get('repeat'),'peak_inflight':peak})
        if batch['phase']=='width' and batch['policy']!='serial':
            base=next(b for b in width if b['policy']=='serial' and b['family']==batch['family'] and b['repeat']==batch['repeat'])
        elif batch['phase']=='transport' and batch['policy']=='persistent':
            base=next(b for b in batches if b['phase']=='transport' and b['policy']=='serial' and b['repeat']==batch['repeat'])
        else:
            continue
        assert len(base['results'])==len(results)
        for a,b in zip(base['results'],results):
            assert a['name']==b['name'] and lines(a['stdout'])==lines(b['stdout'])
    errors=[e for e in events if e['kind']=='run_error']
    if errors:
        assert len(width)==24 and len(errors)==1
        assert errors[0]['type']=='ModuleNotFoundError' and 'psutil' in errors[0]['error']
    assert any(e['kind']=='fixture_cleanup' for e in events)
    assert any(e['kind']=='daemon_cleanup' and e['returncode']==0 for e in events)
    counts=Counter()
    for event in events:
        if 'batch' in event:
            batch=event['batch']
            counts['logical_reads']+=len(batch['results'])
            counts['cli_attempts']+=sum('command' in r for r in batch['results'])
            counts['expected_missing']+=sum(r['returncode']!=0 for r in batch['results'])
    result={'status':'PASS_COMPONENT_WITH_RETAINED_IMPORT_FAILURE' if errors else 'PASS',
            'counts':dict(counts),'batch_count':len(batches),'overlap':checks,
            'limits':'No natural-language intent, consistency, dynamic graph or held-out validity is certified.'}
    (path/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='overlap'},indent=2))

if __name__=='__main__':
    audit(Path(sys.argv[1]))
