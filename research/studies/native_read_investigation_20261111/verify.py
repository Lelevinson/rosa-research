"""Verify declared file hashes and sizes before running optional replay commands."""
import hashlib
import json
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/'MANIFEST.json').read_text())
    for name,spec in manifest['files'].items():
        path=root/name
        assert path.is_relative_to(root)
        data=path.read_bytes()
        assert len(data)==spec['bytes'],name
        assert hashlib.sha256(data).hexdigest()==spec['sha256'],name
    print(f"PASS: {len(manifest['files'])} declared file hashes and sizes")

if __name__=='__main__':
    main()
