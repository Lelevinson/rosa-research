"""Standard-library verification of frozen source, raw closure and review ZIP."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data):return hashlib.sha256(data).hexdigest()


def verify_directory(root):
    frozen=json.loads((root/'freeze.json').read_text())
    for name,h in frozen['sha256'].items():assert sha((root/'source'/name).read_bytes())==h,name
    schedule=json.loads((root/'schedule.json').read_text())
    summaries=[];schema_hashes=set()
    for path in sorted(root.glob('[0-9][0-9]-*/trace.jsonl')):
        events=[json.loads(line) for line in path.read_text().splitlines()]
        first=events[0];assert first['kind']=='episode_start'
        assert sum(e['kind']=='episode_end' for e in events)==1,'Episode lacks closure'
        starts=[e for e in events if e['kind']=='model_start']
        ends=[e for e in events if e['kind']=='model_end']
        errors=[e for e in events if e['kind']=='model_error']
        records=[e['record'] for e in events if e['kind']=='provider_record']
        assert len(starts)==len(ends)+len(errors)
        assert len(starts)==len(records),'Missing provider attempt record'
        for e in starts:
            schemas=e['schemas'];h=sha(json.dumps(schemas,sort_keys=True,default=str).encode())
            assert h==e['schema_hash'];schema_hashes.add(h)
            calls=set()
            for message in e['messages']:
                if message['type']=='ai':calls.update(c['id'] for c in message.get('tool_calls',[]))
                if message['type']=='tool':assert message['tool_call_id'] in calls
            assert not any('CRITICAL - SEQUENTIAL TOOL EXECUTION' in m['content']
                           for m in e['messages'] if m['type']=='system')
        for record in records:
            wire=record.get('native',{}).get('request')
            assert wire is not None,'No wire request captured'
            assert not any(k.lower() in {'authorization','access_token','refresh_token','api_key'} for k in wire)
            if first['provider']=='openai':
                assert wire['model']=='gpt-6-luna' and wire['store'] is False and wire['stream'] is True
                assert not any(k in wire for k in ['temperature','seed','max_output_tokens','truncation'])
                assert wire.get('parallel_tool_calls') is True
            else:
                assert wire['model']=='qwen3.5:9b' and wire['think'] is False
                assert wire['options']['num_ctx']==16384
                assert wire['options']['temperature']==0 and wire['options']['seed']==42
        native_starts={e['request_id']:e for e in events if e['kind']=='ros_start'}
        native_ends=[e for e in events if e['kind']=='ros_end']
        assert len(native_starts)==len(native_ends),'Unclosed native attempt'
        for e in native_ends:assert e['command']==native_starts[e['request_id']]['command']
        summaries.append(dict(episode=path.parent.name,provider=first['provider'],arm=first['arm'],
                              task=first['task']['id'],models=len(ends),provider_attempts=len(records),
                              native=len(native_ends)))
    assert [[r['provider'],r['arm'],r['task']] for r in summaries]==schedule,'Attempted cells differ from freeze'
    assert len(schema_hashes)==1
    setup=[json.loads(line) for line in (root/'setup.jsonl').read_text().splitlines()]
    closure=next(e for e in setup if e['kind']=='study_closed')
    # Activation used the earlier pre-primary closure schema; retain its raw form.
    attempted=closure.get('cells_attempted',closure.get('cells'))
    scheduled=closure.get('cells_scheduled',closure.get('cells'))
    assert attempted==scheduled==len(schedule)
    assert not any(e['kind']=='study_error' for e in setup)
    assert len([e for e in setup if e['kind']=='fixture_stop' and e['returncode']==0])==4
    assert any(e['kind']=='oracle_graph_closed' for e in setup)
    assert any(e['kind']=='daemon_stop' and e['returncode']==0 for e in setup)
    inventories={}
    for p in sorted(root.glob('oracle-*.json')):
        snapshot=json.loads(p.read_text())
        observed=[set(n for n in item['nodes'] if n.startswith(('/diag_demo/','/diag_turtle/')))
                  for item in snapshot['inventories']]
        expected={'/diag_turtle/palette','/diag_demo/source','/diag_demo/listener','/diag_demo/calculator'}
        assert len(observed)==2 and all(names==expected for names in observed)
        inventories[p.name]=True
    assert 'oracle-before.json' in inventories and 'oracle-after.json' in inventories
    return dict(frozen_source_hashes=len(frozen['sha256']),episodes=len(summaries),
                schema_hashes=sorted(schema_hashes),inventory_closure=True,owned_cleanup=True,traces=summaries,
                limits='Preservation/transport/closure contracts only; not semantic answer certification.')


def verify_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=z.namelist();assert len(names)==len(set(names))
        m=json.loads(z.read('MANIFEST.json'))
        assert set(names)==set(m['files'])|{'MANIFEST.json'}
        for name,spec in m['files'].items():
            data=z.read(name);assert len(data)==spec['size'] and sha(data)==spec['sha256'],name
    return dict(members=len(m['files']),crc=True,sha256=sha(path.read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args()
    print(json.dumps(verify_zip(a.path) if a.path.is_file() else verify_directory(a.path),indent=2))
