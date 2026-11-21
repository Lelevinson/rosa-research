"""Build a review ZIP with hashes and a second durable same-host copy."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parent

def main():
    output=ROOT.parent/'_artifacts/ROSA_NATIVE_READ_REVIEW_20261111.zip'
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    ignore=output.parent/'.gitignore'
    if not ignore.exists():
        ignore.write_text('*\n!.gitignore\n')
    paths=[p for p in ROOT.rglob('*') if p.is_file() and
           not any(part in ('backup','__pycache__') for part in p.relative_to(ROOT).parts) and
           p.name not in ('MANIFEST.json','SHA256SUMS')]
    files={str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,
           'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(paths)}
    (ROOT/'MANIFEST.json').write_text(json.dumps({'algorithm':'sha256','files':files,
        'self_exclusions':['MANIFEST.json','SHA256SUMS'],
        'limits':'Same-host backup; no complete preexecution runtime closure; original failed attempts retained.'},indent=2)+'\n')
    (ROOT/'SHA256SUMS').write_text(''.join(f"{spec['sha256']}  {name}\n" for name,spec in files.items()))
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted(paths+[ROOT/'MANIFEST.json',ROOT/'SHA256SUMS']):
            archive.write(path,str(Path(ROOT.name)/path.relative_to(ROOT)))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        expected={str(Path(ROOT.name)/name) for name in files}|{
            str(Path(ROOT.name)/'MANIFEST.json'),str(Path(ROOT.name)/'SHA256SUMS')}
        assert set(archive.namelist())==expected
        for name,spec in files.items():
            assert hashlib.sha256(archive.read(str(Path(ROOT.name)/name))).hexdigest()==spec['sha256']
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(f'{digest}  {output.name}\n')
    backup=ROOT/'backup'
    backup.mkdir(exist_ok=True)
    shutil.copyfile(output,backup/output.name)
    shutil.copyfile(output.with_suffix('.zip.sha256'),backup/(output.name+'.sha256'))
    assert hashlib.sha256((backup/output.name).read_bytes()).hexdigest()==digest
    print(json.dumps({'archive':str(output),'bytes':output.stat().st_size,
                      'members':len(files)+2,'sha256':digest,'backup':str(backup/output.name)},indent=2))

if __name__=='__main__':
    main()
