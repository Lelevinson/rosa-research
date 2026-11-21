"""Build persistent review/backup, check original preservation and ZIP replay."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

from replay import ART, HERE
from verify import check


def digest(data):return hashlib.sha256(data).hexdigest()


def main():
    root=HERE.parents[1]
    original=json.loads((ART/'preservation_before.json').read_text())
    changed=[]
    for relative,expected in original.items():
        if relative in ('research/ROSA_RESEARCH_CONTEXT.md','.gitignore'):
            continue
        path=root/relative
        if not path.exists() or digest(path.read_bytes())!=expected:
            changed.append(relative)
    context=root/'research/ROSA_RESEARCH_CONTEXT.md'
    assert context.read_bytes().startswith((ART/'context_before.md').read_bytes())
    assert (root/'.gitignore').read_text().replace('docs/*\n!docs/START_HERE.md\n','docs\n') == '.idea\n.vscode\nsrc/jpl_rosa.egg-info\nbuild/\ndist/\n__pycache__/\ndocs\n.DS_Store\n.venv/\n.env\n.env.*\n!.env.example\n*.py[cod]\n'
    assert not changed, changed
    preservation=dict(original_files_checked=sum(relative not in ('research/ROSA_RESEARCH_CONTEXT.md','.gitignore') for relative in original),changed_originals=changed,
                      intentional_ignore_change='Only docs/START_HERE.md unignored as AGENTS requires',
                      context_original_prefix_preserved=True,
                      git_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
                      git_status=subprocess.check_output(['git','status','--short','--branch'],cwd=root,text=True))
    (ART/'preservation_after.json').write_text(json.dumps(preservation,indent=2)+'\n')
    # Public source context needed to inspect original tool capability/prompt.
    for source in [root/'AGENTS.md',root/'.gitignore',root/'pyproject.toml',root/'uv.lock',*sorted((root/'src').rglob('*.py'))]:
        destination=ART/'repository_source'/source.relative_to(root)
        destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    files=[context,root/'docs/START_HERE.md']
    files+=sorted(p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files+=sorted(p for p in ART.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    records={str(p.relative_to(root)):{'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in files}
    # Strictly scoped credential screen; academic references to keys are harmless.
    findings=[]
    token_pattern=re.compile(rb'Bearer\s+[A-Za-z0-9_\-.]{25,}|sk-(?:proj-)?[A-Za-z0-9]{30,}|eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}')
    for path in files:
        if token_pattern.search(path.read_bytes()):findings.append(str(path.relative_to(root)))
    assert not findings, findings
    manifest=dict(files=records,self_exclusion='MANIFEST.json intentionally excludes its own hash',
                  scope='Local research review; no credentials, weights, venv or new task disclosure',
                  credential_pattern_findings=findings)
    destination=root/'research/_artifacts/ROSA_AUTOTOOL_ITERATION_REVIEW_20261112.zip'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files:archive.write(path,str(path.relative_to(root)))
        archive.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
    verification=check(destination,replay=True)
    # Corruption test modifies one member while keeping original manifest.
    import tempfile
    with tempfile.TemporaryDirectory(prefix='rosa-autotool-corrupt-') as directory:
        broken=Path(directory)/'broken.zip'
        with zipfile.ZipFile(destination) as source,zipfile.ZipFile(broken,'w') as target:
            for name in source.namelist():
                data=source.read(name)
                if name=='research/autotool_iteration_20261112/replay.py':data+=b'\n# intentional test corruption\n'
                target.writestr(name,data)
        try:
            check(broken)
        except AssertionError:
            verification['corruption_detection']='pass'
        else:
            raise AssertionError('corruption was not detected')
    backup=root/'research/_artifacts/backups/autotool_iteration_20261112'/destination.name
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(destination,backup)
    assert digest(destination.read_bytes())==digest(backup.read_bytes())
    verification.update(backup=str(backup),backup_same_host_filesystem=True,backup_hash_matches=True,
                        bytes=destination.stat().st_size)
    destination.with_suffix('.verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    destination.with_suffix('.zip.sha256').write_text(f"{verification['sha256']}  {destination.name}\n")
    shutil.copyfile(destination.with_suffix('.verification.json'),backup.with_suffix('.verification.json'))
    shutil.copyfile(destination.with_suffix('.zip.sha256'),backup.with_suffix('.zip.sha256'))
    print(json.dumps(verification,indent=2))


if __name__=='__main__':
    raise SystemExit('Historical package builder: restore the pre-migration layout in an isolated directory; do not overwrite the preserved review ZIP.')
