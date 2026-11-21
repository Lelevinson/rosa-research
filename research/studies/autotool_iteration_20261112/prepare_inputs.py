"""Preserve public study inputs and inventory original bytes; no experiment imports."""
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if p.name == 'research').parent
ART = ROOT/'research/_artifacts'/HERE.name
OLD = ROOT.parent/'rosa-research-previous-20261108'
ARCH = ROOT.parent/'rosa-research-archive'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (ART/'INPUTS_FROZEN.json').exists():
        raise SystemExit('Inputs already frozen: refusing to replace.')
    records, sources = [], []
    roots = [('baseline', OLD/'research/_artifacts/baseline-diagnostic/primary-v1'),
             ('narration', ROOT/'research/_artifacts/action_narration_20261111/primary-v1'),
             ('coverage', ROOT/'research/_artifacts/gpt_coverage_investigation_20261111/primary-v1')]
    for corpus, base in roots:
        for path in sorted(base.rglob('trace.jsonl')):
            if 'oracle' in path.relative_to(base).parts:
                continue
            events = [json.loads(line) for line in path.read_text().splitlines()]
            initial = next((e for e in events if e.get('kind') == 'episode_start'), {})
            task = initial.get('task', {})
            if isinstance(task, str):
                task = {'id': task}
            app = task.get('application')
            split = ('train' if app == 'turtlesim' else 'dev' if app == 'demo_nodes_cpp'
                     else 'historical_validation') if corpus == 'baseline' else 'temporal_validation'
            destination = ART/'inputs'/corpus/path.parent.name/'trace.jsonl'
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            records.append({'original': str(path), 'copy': str(destination.relative_to(ART)),
                            'sha256': digest(path), 'bytes': path.stat().st_size,
                            'corpus': corpus, 'episode': path.parent.name, 'task': task.get('id'),
                            'family': app, 'request': task.get('request', ''), 'split': split})
    assert len([r for r in records if r['corpus'] == 'baseline']) == 36
    # Historical context is copied for review, never fed into the predictor.
    documents = list((ARCH/'research/internal').glob('round*_experimental_results.md'))
    documents = [p for p in documents if any(f'round{i}_' in p.name for i in range(19, 29))]
    documents += [p for p in (ROOT/'research/studies/design_investigations_20261108_20261110').glob('*.md')]
    documents += [OLD/'research/multistep'/n for n in ['baseline-findings-review.md', 'independent-results-review.md', 'report.md']]
    documents += [OLD/'research/paper_pilot'/n for n in ['report.md', 'independent-results-review.md']]
    documents += [ROOT/'research'/n/'REPORT.md' for n in ['cpaw_prototype', 'native_read_investigation_20261111', 'action_narration_20261111', 'gpt_coverage_investigation_20261111']]
    documents += [ROOT/'research/studies/gpt_coverage_investigation_20261111/ALGORITHM_ASSESSMENT.md', ROOT/'src/rosa/prompts.py', ROOT/'src/rosa/tools/ros2.py']
    for i, path in enumerate(documents):
        if not path.exists():
            sources.append({'original': str(path), 'available': False})
            continue
        destination = ART/'history'/f'{i:02d}-{path.name}'
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
        sources.append({'original': str(path), 'copy': str(destination.relative_to(ART)),
                        'sha256': digest(path), 'bytes': path.stat().st_size, 'available': True,
                        'kind': 'historical source/report; not replay input'})
    # Inspect actual raw historical records; each schema remains separate.
    raw = []
    for rnd in range(19, 29):
        directory = ARCH/f'research/raw/round{rnd}-mission-v1'
        if rnd == 19:
            directory = ARCH/'research/raw/round19-comparison-v1'
        candidates = sorted(p for p in directory.rglob('*.json') if 'episode' in str(p) or p.name == 'runs.json')
        if not candidates:
            candidates = sorted(directory.rglob('*.json'))[:3]
        selected = candidates[:2]
        if rnd in (27, 28):
            selected = sorted((directory/'heldout-v1/episodes').glob('*.json'))
        for path in selected:
            obj = json.loads(path.read_text())
            destination = ART/'history_raw'/f'round{rnd}'/path.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            raw.append({'round': rnd, 'original': str(path), 'copy': str(destination.relative_to(ART)),
                        'sha256': digest(path), 'top_keys': list(obj)[:20] if isinstance(obj, dict) else 'list',
                        'model_records': len(obj.get('models', [])) if isinstance(obj, dict) else None,
                        'call_records': len(obj.get('calls', [])) if isinstance(obj, dict) else None,
                        'role': 'continuity only; historical arm schemas/semantic adapters excluded from predictor'})
    # Inspect ZIP identities without reconstructing the lost original archive.
    archives = []
    for path in [OLD/'research/_artifacts/rosa-baseline-diagnostic-review-20261107.zip',
                 OLD/'research/_artifacts/rosa-paper-pilot-review-20261108.zip',
                 OLD/'research/_artifacts/rosa-multistep-review-20261107-reconstructed.zip',
                 ARCH/'research/raw/rosa-round28-external-review.zip']:
        with zipfile.ZipFile(path) as z:
            archives.append({'path': str(path), 'sha256': digest(path), 'members': len(z.namelist()),
                             'crc_failure': z.testzip()})
    versions = {}
    for name in ['rosa-llm', 'ollama', 'langchain', 'langchain-core']:
        versions[name] = importlib.metadata.version(name)
    manifest = {'traces': records, 'sources': sources, 'historical_raw': raw, 'archives': archives,
                'versions': versions, 'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                'protocol_sha256': digest(HERE/'PROTOCOL_FROZEN.md'), 'split_counts': dict(Counter(r['split'] for r in records)),
                'fresh_heldout': False, 'missing64': 'Not reconstructed; lost structured-dependency original traces remain missing'}
    (ART/'INPUTS_FROZEN.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'traces': len(records), 'splits': manifest['split_counts'], 'historical_raw': len(raw), 'documents': len(sources), 'versions': versions}, indent=2))


if __name__ == '__main__':
    main()
