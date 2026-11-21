"""Package and duplicate existing evidence; no ROS/model requests."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from verify import verify_directory, verify_zip

ROOT=Path(__file__).resolve().parents[2]
ARTIFACTS=ROOT/'research/_artifacts'
STUDY=ROOT/'research/gpt_coverage_investigation_20261111'
RAW=ARTIFACTS/'gpt_coverage_investigation_20261111'
DESTINATION=ARTIFACTS/'ROSA_GPT_COVERAGE_REVIEW_20261111.zip'
BACKUP=ARTIFACTS/'backups/gpt_coverage_investigation_20261111'


def main():
    if DESTINATION.exists() or BACKUP.exists():
        raise FileExistsError('Preserve existing review/backup identities')
    for phase in ['activation-v1','primary-v1']:
        result=verify_directory(RAW/phase)
        (RAW/(phase+'_package_verification.json')).write_text(json.dumps(result,indent=2)+'\n')
    historical=ARTIFACTS/'ROSA_ACTION_NARRATION_REVIEW_20261111.zip'
    old=verify_zip(historical)
    assert old['sha256']=='6d969491aba01dd3f4286b642565cec68b61bd1359a0c6087b74af34b3b49ef9'
    (RAW/'historical_archive_verification.json').write_text(json.dumps(old,indent=2)+'\n')
    files={}
    for base in [STUDY,RAW,ROOT/'research/action_narration_20261111',ROOT/'src/rosa']:
        for path in base.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                files[str(path.relative_to(ROOT))]=path
    for name in ['AGENTS.md','README.md','LICENSE','setup.py','pyproject.toml','uv.lock',
                 'research/ROSA_RESEARCH_CONTEXT.md',str(historical.relative_to(ROOT))]:
        path=ROOT/name;assert path.is_file(),name;files[name]=path
    explanation=b'''# GPT and coverage evidence review

Read research/gpt_coverage_investigation_20261111/REPORT.md first.
All10 new answers have acquired factual support; strict ordered-task completion
is7/10. Three correct-data answers fail requested order. No algorithm promoted.
The previous action-narration review is preserved as a complete nested ZIP,
including its failed final inventory and all historical limits. It was not rerun.

No inference is required for integrity/closure verification:
python3 research/gpt_coverage_investigation_20261111/verify.py /absolute/path/to/review.zip
python3 research/gpt_coverage_investigation_20261111/verify.py research/_artifacts/gpt_coverage_investigation_20261111/primary-v1

The new independent persistent-inventory closeout passes while original-style
CLI empty enumerations remain saved. Read protocol and independent review.
Automatic first-start screens are not final temporal/semantic judgments; inspect
manual_adjudication.json and actual native intervals. Original frozen files are
under each phase/source; postexecution analysis/report files are separate.

Credentials, authorization headers, model weights, virtual environments and Git
internals are excluded. Native reproduction needs ROS2 Jazzy, existing dependencies
and the reviewer's own authorized model access; this ZIP is not new authorization.
'''
    manifest={'files':{name:{'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                       for name,path in sorted(files.items())},
              'limits':'Preservation and experimental closure checks are separate from semantic correctness, strict task compliance and algorithmic novelty.'}
    manifest['files']['VERIFY.md']={'size':len(explanation),'sha256':hashlib.sha256(explanation).hexdigest()}
    with zipfile.ZipFile(DESTINATION,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(files.items()):z.write(path,name)
        z.writestr('VERIFY.md',explanation)
        z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    result=verify_zip(DESTINATION)
    DESTINATION.with_suffix('.zip.sha256').write_text(result['sha256']+'  '+DESTINATION.name+'\n')
    DESTINATION.with_suffix('.verification.json').write_text(json.dumps(result,indent=2)+'\n')
    BACKUP.mkdir(parents=True,exist_ok=False)
    shutil.copytree(RAW,BACKUP/'raw')
    shutil.copytree(STUDY,BACKUP/'source',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy2(DESTINATION,BACKUP/DESTINATION.name)
    shutil.copy2(DESTINATION.with_suffix('.zip.sha256'),BACKUP/(DESTINATION.name+'.sha256'))
    for base,copy in [(RAW,BACKUP/'raw'),(STUDY,BACKUP/'source')]:
        for path in base.rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                assert path.read_bytes()==(copy/path.relative_to(base)).read_bytes(),str(path)
    assert DESTINATION.read_bytes()==(BACKUP/DESTINATION.name).read_bytes()
    result['persistent_backup_verified']=str(BACKUP)
    (BACKUP/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    raise SystemExit('Historical package builder: restore the pre-migration layout in an isolated directory; do not overwrite the preserved review ZIP.')
