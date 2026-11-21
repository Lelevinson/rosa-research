"""Recompute measured tables from raw events; no ROS/model execution."""
from collections import defaultdict
import json
from pathlib import Path
import statistics

ROOT=Path(__file__).resolve().parent

def main():
    groups=defaultdict(list)
    runs={}
    for version in ('native_v2','native_v3'):
        events=[json.loads(x) for x in (ROOT/'evidence'/version/'traces.jsonl').read_text().splitlines()]
        runs[version]={e['kind']:e for e in events if e['kind'] in ('run_end','setup_wait','persistent_setup','fixture_cleanup','daemon_cleanup','rmw')}
        for event in events:
            if event['kind']=='batch':
                batch=event['batch']
                groups['/'.join([batch['phase'],batch['family'],batch['policy']])].append(batch)
    result={key:{'batches':len(rows),'reads':sum(len(r['results']) for r in rows),
                 'wall_sum_seconds':sum(r['wall_seconds'] for r in rows),
                 'wall_median_seconds':statistics.median(r['wall_seconds'] for r in rows),
                 'policy_update_sum_seconds':sum(r.get('policy_seconds',0) for r in rows),
                 'failures':sum(x['returncode']!=0 for r in rows for x in r['results'])}
            for key,rows in groups.items()}
    (ROOT/'evidence/measurements.json').write_text(json.dumps({'groups':result,'runs':runs},indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    main()
