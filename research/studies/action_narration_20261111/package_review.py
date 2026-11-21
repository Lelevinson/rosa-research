"""Package existing evidence only; never executes ROS or a model."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from verify import verify_directory, verify_zip


ROOT=Path(__file__).resolve().parents[2]
STUDY=ROOT/'research/action_narration_20261111'
ARTIFACTS=ROOT/'research/_artifacts'
RAW=ARTIFACTS/'action_narration_20261111'
DESTINATION=ARTIFACTS/'ROSA_ACTION_NARRATION_REVIEW_20261111.zip'
BACKUP=ARTIFACTS/'backups/action_narration_20261111'


def main():
    if DESTINATION.exists() or BACKUP.exists():
        raise FileExistsError('Do not overwrite a prior review or backup identity')
    verification=verify_directory(RAW)
    (RAW/'trace_verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    files={}
    for base in [STUDY,RAW]:
        for p in base.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                files[str(p.relative_to(ROOT))]=p
    for name in ['research/ROSA_RESEARCH_CONTEXT.md','AGENTS.md','pyproject.toml','uv.lock',
                 'research/_artifacts/ROSA_NATIVE_READ_REVIEW_20261111.zip']:
        p=ROOT/name
        assert p.is_file(),name
        files[name]=p
    explanation=b'''# Offline review

This archive preserves an investigation with incomplete protocol closeout.
Read research/action_narration_20261111/REPORT.md first. The final inventory
failure and diagnostic scoring amendment are retained, not converted into a win.
All12 episode traces closed; support judgments remain conditional.

No inference is needed to check ZIP integrity:
python3 research/action_narration_20261111/verify.py /absolute/path/to/review.zip

After extraction, check trace contracts:
python3 research/action_narration_20261111/verify.py research/_artifacts/action_narration_20261111

The original pre-execution scorer is in the primary source freeze; it fails the
final empty inventory. Current score.py --diagnostic is postexecution analysis,
not protocol-valid scoring. See PROTOCOL.md and INDEPENDENT_ANSWER_REVIEW.md.
The nested native-review ZIP is historical evidence, not a fresh replication.
Its internal manifest uses bytes rather than size; preserve that schema.
No credentials, model weights, virtual environment or Git internals are included.
'''
    manifest={'files':{name:{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                       for name,p in sorted(files.items())},
              'limits':'Preservation/contracts only; final inventory closure failed. Source-supported judgments conditional; no algorithm claim.'}
    manifest['files']['VERIFY.md']={'size':len(explanation),'sha256':hashlib.sha256(explanation).hexdigest()}
    with zipfile.ZipFile(DESTINATION,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(files.items()):z.write(p,name)
        z.writestr('VERIFY.md',explanation)
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    result=verify_zip(DESTINATION)
    DESTINATION.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+DESTINATION.name+'\n')
    DESTINATION.with_suffix('.verification.json').write_text(json.dumps(result,indent=2)+'\n')
    # A separate persistent recovery copy, on the same filesystem. Excludes no raw events.
    BACKUP.mkdir(parents=True,exist_ok=False)
    shutil.copytree(RAW,BACKUP/'raw')
    shutil.copytree(STUDY,BACKUP/'source',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(DESTINATION,BACKUP/DESTINATION.name)
    shutil.copy2(DESTINATION.with_suffix('.zip.sha256'),BACKUP/(DESTINATION.name+'.sha256'))
    for base,copy in [(RAW,BACKUP/'raw'),(STUDY,BACKUP/'source')]:
        for p in base.rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                assert p.read_bytes()==(copy/p.relative_to(base)).read_bytes(),str(p)
    assert DESTINATION.read_bytes()==(BACKUP/DESTINATION.name).read_bytes()
    result['persistent_backup_verified']=str(BACKUP)
    (BACKUP/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    raise SystemExit('Historical package builder: restore the pre-migration layout in an isolated directory; do not overwrite the preserved review ZIP.')
