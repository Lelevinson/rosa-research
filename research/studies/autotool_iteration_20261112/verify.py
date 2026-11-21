"""Verify review ZIP; optionally rerun only offline standard-library programs."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


def stable(value):
    if isinstance(value, dict):
        return {k: stable(v) for k, v in value.items() if k not in ('policy_seconds', 'training_seconds')}
    if isinstance(value, list):
        return [stable(v) for v in value]
    return value


def check(path, replay=False):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        assert len(names)==len(set(names)), 'duplicate ZIP member'
        for name in names:
            p=PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'unsafe member'
        assert archive.testzip() is None, 'CRC failure'
        manifest=json.loads(archive.read('MANIFEST.json'))
        assert set(names)==set(manifest['files'])|{'MANIFEST.json'}, 'manifest coverage mismatch'
        for name,record in manifest['files'].items():
            data=archive.read(name)
            assert len(data)==record['bytes'], name
            assert hashlib.sha256(data).hexdigest()==record['sha256'], name
        result=dict(members=len(names),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                    crc='pass',exact_manifest_coverage=True,all_hashes_match=True)
        if replay:
            with tempfile.TemporaryDirectory(prefix='rosa-autotool-review-') as directory:
                archive.extractall(directory)
                root=Path(directory)
                code=root/'research/autotool_iteration_20261112'
                evidence=root/'research/_artifacts/autotool_iteration_20261112'
                for relative,expected in json.loads((evidence/'FINAL_SOURCE_FREEZE.json').read_text()).items():
                    assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==expected, relative
                before=json.loads((evidence/'results/summary.json').read_text())
                assertions=[]
                for program in ['test_replay.py','adversarial.py','replay.py']:
                    completed=subprocess.run([sys.executable,str(code/program)],cwd=root,
                        capture_output=True,text=True,timeout=60)
                    assertions.append(dict(program=program,returncode=completed.returncode,
                                           stderr=completed.stderr[-2000:]))
                    assert completed.returncode==0, assertions[-1]
                after=json.loads((evidence/'results/summary.json').read_text())
                assert stable(before)==stable(after), 'offline replay counters differ'
                result['extracted_replay']=assertions
                result['stable_counters_reproduced']=True
                result['final_source_freeze_verified']=True
        return result


if __name__=='__main__':
    print(json.dumps(check(Path(sys.argv[1]),'--replay' in sys.argv[2:]),indent=2))
