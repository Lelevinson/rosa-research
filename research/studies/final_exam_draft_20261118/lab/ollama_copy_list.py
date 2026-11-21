"""List the Ollama files that make up the four study models, so they can be copied between machines with IDENTICAL digests (read-only; nothing is changed).
  python3 ollama_copy_list.py MODELS_DIR            prints paths relative to MODELS_DIR (for `rsync -a --files-from=LIST MODELS_DIR/ DEST/`) and the total size
MODELS_DIR is the Ollama models directory (laptop: /mnt/c/Users/user/.ollama/models under WSL). Layout: manifests/<registry>/<namespace>/<name>/<tag> (JSON) and blobs/sha256-<hex>."""
import json
import sys
from pathlib import Path

MODELS = {"lfm3:1.7b", "bonsai-2:4b", "gpt-oss:20b", "qwen3.5:9b"}
root = Path(sys.argv[1])
paths, total = [], 0
for manifest in sorted((root / "manifests").rglob("*")):
    if not manifest.is_file():
        continue
    name, tag = manifest.parent.name, manifest.name
    if f"{name}:{tag}" not in MODELS:
        continue
    data = json.loads(manifest.read_text())
    paths.append(str(manifest.relative_to(root)))
    digests = [data["config"]["digest"]] + [layer["digest"] for layer in data["layers"]]
    for digest in digests:
        blob = root / "blobs" / digest.replace(":", "-")
        if not blob.exists():
            sys.exit(f"missing blob {blob.name} for {name}:{tag}")
        paths.append(str(blob.relative_to(root)))
        total += blob.stat().st_size
    print(f"# {name}:{tag}: {len(digests)} blobs", file=sys.stderr)
paths = sorted(set(paths))
print("\n".join(paths))
print(f"# {len(paths)} files, {total / 1e9:.1f} GB (blobs shared between models counted once per model here)", file=sys.stderr)
found = {f"{Path(p).parent.name}:{Path(p).name}" for p in paths if p.startswith("manifests")}
missing = MODELS - found
if missing:
    sys.exit(f"models not found in {root}: {sorted(missing)}")
