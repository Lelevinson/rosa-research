"""Revision-aware verification of the Stage 1 freeze: FREEZE.json (original, 2026-11-21 17:52) overlaid with FREEZE_REV1.json (revision 1). Exit 1 and a list of mismatches if anything differs.
  python3 verify_freeze.py [OLLAMA_URL]
Checks: every file hash of FREEZE.json, except that the files listed under `changed_files` of FREEZE_REV1.json must have their NEW hash; every `added_files` hash; scorer v2.0; the digests of the 7 models;
the Ollama version recorded in FREEZE_REV1.json (a different version is a mismatch: the exam stops and reports)."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def sha(path):
    return hashlib.sha256((REPO / path).read_bytes()).hexdigest()


def ollama(url, endpoint):
    return json.load(urllib.request.urlopen(url.rstrip("/") + endpoint, timeout=15))


def problems_found(url):
    original = json.loads((HERE / "FREEZE.json").read_text())
    revision = json.loads((HERE / "FREEZE_REV1.json").read_text())
    problems = []
    expected = dict(original["sha256"])
    for path, change in revision["changed_files"].items():
        if path in expected:
            expected[path] = change["new_sha256"]
    expected.update({path: digest for path, digest in revision["added_files"].items()})
    for path, digest in expected.items():
        if not (REPO / path).exists() or sha(path) != digest:
            problems.append(f"{path}: hash differs or file missing")
    if sha("research/studies/residual_failures_20261115/scorer_v2.py") != original["scorer_v2_sha256"]:
        problems.append("scorer v2.0 differs")
    if url:
        try:
            have = {m["name"]: m["digest"] for m in ollama(url, "/api/tags")["models"]}
            problems += [f"model {m} digest differs or model missing" for m, digest in original["model_digests"].items() if have.get(m) != digest]
            version = ollama(url, "/api/version")["version"]
            if version != revision["ollama_version"]:
                problems.append(f"Ollama version {version} differs from the recorded {revision['ollama_version']}")
        except Exception as error:  # noqa: BLE001  an unreachable Ollama is a stop condition too
            problems.append(f"Ollama check failed: {type(error).__name__}")
    return problems


if __name__ == "__main__":
    found = problems_found(sys.argv[1] if len(sys.argv) > 1 else "http://172.30.80.1:11434")
    print("VERIFIED (FREEZE.json + FREEZE_REV1.json): all frozen files, digests and the Ollama version match" if not found else "\n".join(found))
    sys.exit(1 if found else 0)
