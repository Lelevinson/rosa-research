"""Reconstruct list-read incidence from original archived events, without inference."""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ARCH = Path('/home/levinsonchen/project/rosa-research-previous-20261108/research/_artifacts')
SOURCES = {'diagnostic': 'rosa-baseline-diagnostic-review-20261107.zip',
           'codeact': 'rosa-paper-pilot-review-20261108.zip'}
FIELDS = {'ros2_node_info': 'nodes', 'ros2_topic_info': 'topics',
          'ros2_service_info': 'services'}

def main():
    rows, archives, excerpts = [], [], []
    for corpus, filename in SOURCES.items():
        path = ARCH / filename
        with zipfile.ZipFile(path) as archive:
            archives.append({'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                             'crc_bad': archive.testzip()})
            for member in archive.namelist():
                if not member.endswith('/trace.jsonl'):
                    continue
                events = [json.loads(line) for line in archive.read(member).splitlines() if line.strip()]
                native = [e for e in events if e.get('kind') in ('ros_end', 'ros_error')]
                starts = [e for e in events if e.get('kind') == 'tool_start']
                calls = []
                for e in starts:
                    if e.get('name') not in FIELDS:
                        continue
                    args = e.get('input', {})
                    if isinstance(args, str):
                        try:
                            args = ast.literal_eval(args)
                        except (ValueError, SyntaxError):
                            args = json.loads(args)
                    names = args.get(FIELDS[e['name']], [])
                    uid = e.get('run_id', e.get('tool_run_id'))
                    reads = [r for r in native if r.get('tool_run_id') == uid]
                    durations = [r['seconds'] for r in reads if 'seconds' in r]
                    serial = sum(durations)
                    calls.append({'name': e['name'], 'n': len(names), 'args': args,
                                  'start': e.get('monotonic'), 'native_seconds': serial,
                                  'native_count': len(reads), 'native_durations': durations,
                                  'ideal_unlimited_saving_seconds': serial-max(durations, default=0)})
                    if len(names) >= 2 and len(excerpts) < 3:
                        excerpts.append({'archive': filename, 'member': member, 'event': e})
                times = [e['monotonic'] for e in events if 'monotonic' in e]
                primary = '/primary-v1/' in member and '/oracle/' not in member
                rows.append({'corpus': corpus, 'member': member, 'primary': primary,
                             'list_calls': calls, 'tool_starts': len(starts), 'native_completions': len(native),
                             'event_span_seconds': max(times)-min(times) if times else None,
                             'native_events': native})
    groups = {}
    for label, subset in [('diagnostic_primary', [r for r in rows if r['corpus']=='diagnostic' and r['primary']]),
                          ('diagnostic_other', [r for r in rows if r['corpus']=='diagnostic' and not r['primary']]),
                          ('codeact_all', [r for r in rows if r['corpus']=='codeact'])]:
        calls = [c for r in subset for c in r['list_calls']]
        groups[label] = {'episodes':len(subset), 'tool_starts':sum(r['tool_starts'] for r in subset),
                         'list_calls':len(calls), 'multi_calls':sum(c['n']>=2 for c in calls),
                         'multi_episodes':sum(any(c['n']>=2 for c in r['list_calls']) for r in subset),
                         'size_histogram':dict(Counter(c['n'] for c in calls)),
                         'native_completions':sum(r['native_completions'] for r in subset),
                         'multi_native_seconds':sum(c['native_seconds'] for c in calls if c['n']>=2),
                         'ideal_unlimited_saving_seconds':sum(c['ideal_unlimited_saving_seconds'] for c in calls if c['n']>=2),
                         'event_span_sum_seconds':sum(r['event_span_seconds'] or 0 for r in subset)}
    result = {'groups':groups, 'archives':archives, 'episodes':rows, 'representative_multi_events':excerpts,
              'limits':'Observed tool_start events only; nested custom-program list reads may lack tool_start. Event span is not certified episode latency.'}
    (ROOT/'evidence/inventory.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(groups, indent=2))

if __name__ == '__main__':
    main()
