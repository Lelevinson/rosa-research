"""Tables for Stage 1 (writes STAGE1_TABLES.md from scores_1a.json / scores_1b.json).

  python3 summarize_stage1.py <study_dir> <run_1a_dir> <run_1b_dir>
"""
import json
from pathlib import Path
import statistics
import sys


def mean(values):
    return f'{statistics.mean(values):.2f}' if values else 'n/a'


def table_1a(run):
    data = json.loads((Path(run) / 'scores_1a.json').read_text())
    rows = data['episodes']
    out = ['## Stage 1a: A_orig vs A0 (qwen3.5:9b, 6 tasks x 2 repeats)\n',
           f'Oracle stable across snapshots: {all(data["oracle_stable"].values())}. Supported-complete = exact fields AND support screen.\n',
           '| arm | episodes | supported-complete | requests (all) | requests / supported ep | excess over floor (supported eps) | multi-call requests | max calls in one request | input tokens | output tokens | native ops | episode seconds |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for arm in ('A_orig', 'A0'):
        eps = [r for r in rows if r.get('arm') == arm]
        sup = [r for r in eps if r['supported_complete']]
        out.append(f"| {arm} | {len(eps)} | {len(sup)} | {sum(r['requests'] for r in eps)} | {mean([r['requests'] for r in sup])} | "
                   f"{sum(r['requests'] - r['floor'] for r in sup)} over floor {sum(r['floor'] for r in sup)} | "
                   f"{sum(r['multi_call_requests'] for r in eps)} | {max((r['max_calls'] for r in eps), default=0)} | "
                   f"{sum(r['input_tokens'] for r in eps):,} | {sum(r['output_tokens'] for r in eps):,} | {sum(r['native_ops'] for r in eps)} | "
                   f"{sum(r['episode_seconds'] or 0 for r in eps):.0f} |")
    index = {(r['task'], r['repeat'], r['arm']): r for r in rows}
    pairs, out2 = [], []
    for (task, repeat, arm), r in sorted(index.items()):
        if arm != 'A_orig':
            continue
        other = index.get((task, repeat, 'A0'))
        if other and r['supported_complete'] and other['supported_complete']:
            pairs.append((task, repeat, r['requests'], other['requests']))
    out.append('\n### Matched pairs where both arms are supported-complete\n')
    out.append('| task | repeat | A_orig requests | A0 requests | A_orig - A0 |')
    out.append('|---|---:|---:|---:|---:|')
    for task, repeat, a, b in pairs:
        out.append(f'| {task} | {repeat} | {a} | {b} | {a - b} |')
    diffs = [a - b for _, _, a, b in pairs]
    if diffs:
        out.append(f'\nPairs: {len(diffs)}; mean saving {statistics.mean(diffs):.2f}; median {statistics.median(diffs)}; range {min(diffs)} to {max(diffs)}; '
                   f'A0 fewer in {sum(d > 0 for d in diffs)}, equal in {sum(d == 0 for d in diffs)}, more in {sum(d < 0 for d in diffs)}.')
    out.append('\n### Episodes not supported-complete (read these by hand)\n')
    out.append('| episode | exact | support missing | issues | requests | error |')
    out.append('|---|---|---|---|---:|---|')
    for r in rows:
        if not r.get('supported_complete'):
            out.append(f"| {r.get('episode')} | {r.get('exact')} | {'; '.join(r.get('support_missing', []))[:120]} | {'; '.join(r.get('issues', []))[:120]} | {r.get('requests')} | {str(r.get('error'))[:60]} |")
    out.append('\n### Every episode\n')
    out.append('| episode | arm | requests | floor | calls per request | supported-complete | native ops | seconds |')
    out.append('|---|---|---:|---:|---|---|---:|---:|')
    for r in rows:
        if 'requests' in r:
            out.append(f"| {r['episode']} | {r['arm']} | {r['requests']} | {r['floor']} | {r['calls_per_request']} | {r['supported_complete']} | {r['native_ops']} | {r['episode_seconds'] or 0:.0f} |")
    return out


def table_1b(run):
    rows = json.loads((Path(run) / 'scores_1b.json').read_text())
    out = ['\n## Stage 1b: width probe (A0 only, floor = 3 requests at every N)\n',
           '| provider | N | episode | value coverage supported / N | `clocks` key present | requests | calls per request | all N in one request | input tokens | output tokens | native ops | native failures | native timeouts | seconds | capacity events |',
           '|---|---:|---|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---|']
    for r in sorted(rows, key=lambda r: (r['provider'], r['n'], r['label'])):
        capacity = []
        if r['length_events']:
            capacity.append(f"length x{len(r['length_events'])}")
        if r['iteration_cap']:
            capacity.append('iteration cap')
        if r['error']:
            capacity.append('error: ' + str(r['error'])[:50])
        out.append(f"| {r['provider']} | {r['n']} | {r['label']} | {r['coverage_supported']}/{r['n']} | {r['format_ok']} | {r['requests']} | {r['calls_per_request']} | "
                   f"{r['all_in_one_request']} | {r['input_tokens']:,} | {r['output_tokens']:,} | {r['native_ops']} | {r['native_failures']} | {r['native_timeouts']} | "
                   f"{r['episode_seconds'] or 0:.0f} | {', '.join(capacity) or '-'} |")
    out.append('\n### Decision rules at N=32\n')
    for provider in sorted({r['provider'] for r in rows}):
        eps = [r for r in rows if r['provider'] == provider and r['n'] == 32 and r['label'] != 'pilot']
        if len(eps) < 2:
            out.append(f'- {provider}: fewer than 2 usable N=32 episodes ({len(eps)}): inconclusive.')
            continue
        holds = all(r['coverage_supported'] == 32 and r['requests'] <= 4 for r in eps)  # value coverage; format reported separately
        gap = any(r['coverage_supported'] < 32 or r['requests'] >= 6 for r in eps)
        verdict = 'ordinary prompt holds' if holds else ('GAP at scale' if gap else 'in between: inconclusive')
        out.append(f"- {provider}: N=32 episodes {[(r['label'], r['coverage_supported'], r['requests']) for r in eps]} -> {verdict}; `clocks` key present in {sum(r['format_ok'] for r in eps)}/{len(eps)}.")
    return out


def main():
    study, run_1a, run_1b = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    lines = []
    if run_1a != '-':
        lines += table_1a(run_1a)
    if run_1b != '-':
        lines += table_1b(run_1b)
    (study / 'STAGE1_TABLES.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
