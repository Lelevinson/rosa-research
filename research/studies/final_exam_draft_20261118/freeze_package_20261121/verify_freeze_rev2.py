"""Revision-aware verification of the Stage 1 freeze with THREE records: FREEZE.json (original) + FREEZE_REV1.json + FREEZE_REV2.json. It replaces verify_freeze.py in the start script once revision 2 is applied.
  python3 verify_freeze_rev2.py [OLLAMA_URL]
Exit 0: everything verifies (revision 2 applied). Exit 2: revision 2 is PREPARED but not applied (only the files listed under `apply` still have their revision-1 content and their candidates match the recorded hashes); the run must not start.
Exit 1: anything else (an unknown change, a wrong chain hash, a missing file, a scorer / model digest / Ollama version difference).
Checks: the chain (REV1 records the original's SHA-256; REV2 records the SHA-256 of the original and of REV1); for every revision-2 changed file the recorded old hash equals what the earlier records expect; every expected file hash;
scorer v2.0; the 7 model digests; the Ollama version recorded by revision 2 (a different version stops the exam)."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
file_sha = lambda path: hashlib.sha256((REPO / path).read_bytes()).hexdigest() if (REPO / path).exists() else None
ollama = lambda url, endpoint: json.load(urllib.request.urlopen(url.rstrip("/") + endpoint, timeout=15))


def check(url):
    problems, unapplied = [], []
    original_bytes, rev1_bytes = (HERE / "FREEZE.json").read_bytes(), (HERE / "FREEZE_REV1.json").read_bytes()
    original, rev1 = json.loads(original_bytes), json.loads(rev1_bytes)
    rev2_path = HERE / "FREEZE_REV2.json"
    if not rev2_path.exists():
        return ["FREEZE_REV2.json does not exist"], []
    rev2 = json.loads(rev2_path.read_text())
    if hashlib.sha256(original_bytes).hexdigest() != rev1["original_freeze_sha256"]:
        problems.append("FREEZE.json is not the original recorded by revision 1")
    if rev2.get("original_freeze_sha256") != hashlib.sha256(original_bytes).hexdigest() or rev2.get("rev1_sha256") != hashlib.sha256(rev1_bytes).hexdigest():
        problems.append("the chain hashes recorded in FREEZE_REV2.json do not match FREEZE.json / FREEZE_REV1.json")
    expected = dict(original["sha256"])
    for path, change in rev1["changed_files"].items():
        if path in expected and expected[path] != change["old_sha256"]:
            problems.append(f"{path}: revision 1 records a different old hash than the original")
        expected[path] = change["new_sha256"]
    expected.update(rev1["added_files"])
    for path, change in rev2["changed_files"].items():
        if expected.get(path) != change["old_sha256"]:
            problems.append(f"{path}: revision 2's old hash is not what the earlier records expect")
        expected[path] = change["new_sha256"]
    for path, digest in rev2["added_files"].items():
        if path in expected and expected[path] != digest:
            problems.append(f"{path}: added by revision 2 but already expected with another hash")
        expected[path] = digest
    for path, digest in expected.items():
        have = file_sha(path)
        if have == digest:
            continue
        change = rev2["changed_files"].get(path)
        candidate = rev2.get("apply", {}).get(path)
        if change and have == change["old_sha256"] and candidate and file_sha(candidate) == digest:
            unapplied.append(path)
        else:
            problems.append(f"{path}: hash differs or file missing")
    if file_sha("research/studies/residual_failures_20261115/scorer_v2.py") != original["scorer_v2_sha256"]:
        problems.append("scorer v2.0 differs")
    if url:
        try:
            have = {m["name"]: m["digest"] for m in ollama(url, "/api/tags")["models"]}
            problems += [f"model {m} digest differs or model missing" for m, digest in original["model_digests"].items() if have.get(m) != digest]
            version = ollama(url, "/api/version")["version"]
            if version != rev2["ollama_version"]:
                problems.append(f"Ollama version {version} differs from the recorded {rev2['ollama_version']}")
        except Exception as error:  # noqa: BLE001  an unreachable Ollama is a stop condition too
            problems.append(f"Ollama check failed: {type(error).__name__}")
    return problems, unapplied


if __name__ == "__main__":
    problems, unapplied = check(sys.argv[1] if len(sys.argv) > 1 else "http://172.30.80.1:11434")
    if problems:
        print("\n".join(problems))
        sys.exit(1)
    if unapplied:
        print("PREPARED, NOT APPLIED: revision 2 awaits `make_freeze_rev2.py apply` for " + ", ".join(unapplied) + ". Every other hash, the scorer, the model digests and the Ollama version verify. Do not start the run.")
        sys.exit(2)
    print("VERIFIED (FREEZE.json + FREEZE_REV1.json + FREEZE_REV2.json): all frozen files, digests and the Ollama version match")
