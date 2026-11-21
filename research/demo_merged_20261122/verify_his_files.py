"""Verify his files byte for byte against the SHA-256 table in M_FILES.md. Zero model calls. Stdlib only.
Usage: python verify_his_files.py [--root <dir extracted with git archive>] [--commit e233cf5...] [--git-dir <repo>]
Checks (a) the git BLOB at the commit and (b) if --root is given, the extracted file on disk. Prints OK/MISMATCH per row and writes HIS_FILES_VERIFY.json."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMIT = 'e233cf51389885d0aaffa5453687f57437551764'


def table():
    rows = []
    for line in (HERE / 'M_FILES.md').read_text(encoding='utf-8').splitlines():
        m = re.match(r'\| `([^`]+)` \| .* \| `([0-9a-f]{64})` \| (.+?) \|$', line)
        if m:
            rows.append((m.group(1), m.group(2), m.group(3)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root')
    ap.add_argument('--commit', default=COMMIT)
    ap.add_argument('--git-dir', default=str(HERE.parent.parent))
    args = ap.parse_args()
    out, bad = [], 0
    for path, expected, status in table():
        blob = subprocess.run(['git', '-C', args.git_dir, 'show', '%s:%s' % (args.commit, path)], capture_output=True).stdout
        blob_hash = hashlib.sha256(blob).hexdigest() if blob else None
        disk_hash = None
        if args.root and (Path(args.root) / path).is_file():
            disk_hash = hashlib.sha256((Path(args.root) / path).read_bytes()).hexdigest()
        ok_blob = blob_hash == expected
        ok_disk = disk_hash == expected if args.root else None
        crlf_note = None
        if not ok_blob and blob:
            normalized = hashlib.sha256(blob.replace(b'\r\n', b'\n')).hexdigest()
            crlf_note = 'matches after CRLF->LF' if normalized == expected else None
        bad += 0 if ok_blob and ok_disk in (True, None) else 1
        out.append(dict(path=path, expected=expected, frozen_status=status, blob_sha256=blob_hash, disk_sha256=disk_hash, blob_ok=ok_blob, disk_ok=ok_disk, note=crlf_note))
        print('%-8s %s %s' % ('OK' if ok_blob and ok_disk in (True, None) else 'MISMATCH', path, crlf_note or ''))
    (HERE / 'HIS_FILES_VERIFY.json').write_text(json.dumps({'commit': args.commit, 'rows': out, 'mismatches': bad}, indent=1), encoding='utf-8')
    print('rows', len(out), 'mismatches', bad)


if __name__ == '__main__':
    main()
