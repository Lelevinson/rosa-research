"""Offline preservation and trace-contract verifier. Standard library only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile


def sha(data): return hashlib.sha256(data).hexdigest()


def verify_trace(path):
    events = [json.loads(line) for line in path.read_text().splitlines()]
    schemas = set()
    starts = {e['request_id']:e for e in events if e['kind']=='ros_start'}
    ends = [e for e in events if e['kind']=='ros_end']
    for e in ends:
        assert e['request_id'] in starts
        assert starts[e['request_id']]['command'] == e['command']
    assert len(starts) == len(ends), 'Unclosed native attempt'
    for e in events:
        if e['kind'] != 'model_start': continue
        schemas.add(e['schema_hash'])
        assert sha(json.dumps(e['schemas'],sort_keys=True,default=str).encode())==e['schema_hash']
        assert e['envelope']['think'] is False
        assert not e['envelope']['format']
        assert e['envelope']['options']['seed']==42
        assert e['envelope']['options']['num_predict']==1600
        calls = set()
        for message in e['messages']:
            if message['type']=='ai':
                calls.update(c['id'] for c in message.get('tool_calls',[]))
            if message['type']=='tool':
                assert message['tool_call_id'] in calls, 'Unbound tool message'
        system = [m['content'] for m in e['messages'] if m['type']=='system']
        assert not any('CRITICAL - SEQUENTIAL TOOL EXECUTION' in m for m in system)
        assert any('MAY be issued together' in m for m in system)
    assert len(schemas)==1
    assert sum(e['kind']=='episode_start' for e in events)==1
    assert sum(e['kind']=='episode_end' for e in events)==1
    assert sum(e['kind']=='model_start' for e in events)==sum(e['kind']=='model_end' for e in events)+sum(e['kind']=='model_error' for e in events)
    return dict(path=path.parent.name, schemas=sorted(schemas), models=sum(e['kind']=='model_end' for e in events),
                native=len(ends), native_failures=sum(e['returncode']!=0 for e in ends))


def verify_directory(root):
    primary=root/'primary-v1'
    frozen=json.loads((primary/'freeze.json').read_text())
    for name,h in frozen['sha256'].items(): assert sha((primary/'source'/name).read_bytes())==h, name
    rows=[verify_trace(p) for p in sorted(primary.glob('[0-9][0-9]-*/trace.jsonl'))]
    assert len(rows)==12
    assert len({s for r in rows for s in r['schemas']})==1
    actual=[]
    for p in sorted(primary.glob('[0-9][0-9]-*/trace.jsonl')):
        start=json.loads(p.read_text().splitlines()[0])
        actual.append([start['task']['id'],start['arm']])
    assert actual==json.loads((primary/'schedule.json').read_text())
    assert (primary/'oracle-before.json').exists() and (primary/'oracle-after.json').exists()
    return dict(primary_episodes=len(rows), source_hashes=len(frozen['sha256']), traces=rows)


def verify_zip(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        names=z.namelist()
        assert len(names)==len(set(names))
        manifest=json.loads(z.read('MANIFEST.json'))
        assert set(names)==set(manifest['files'])|{'MANIFEST.json'}
        for name,v in manifest['files'].items():
            data=z.read(name)
            assert len(data)==v['size'] and sha(data)==v['sha256'], name
        return dict(members=len(manifest['files']),crc=True,sha256=sha(path.read_bytes()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('path',type=Path);a=p.parse_args()
    print(json.dumps(verify_zip(a.path) if a.path.is_file() else verify_directory(a.path),indent=2))
