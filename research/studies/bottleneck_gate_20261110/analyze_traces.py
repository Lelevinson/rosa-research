"""Offline, standard-library-only evidence index. Never imports experiment code.

Run from repository root: python3 research/diagnostics/bottleneck_gate_20261110/analyze_traces.py
Identity matching below is textual prior-observation support, NOT freshness proof.
Exact repeats mean command equality, NOT proven unnecessary execution.
"""
import ast
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import zipfile

OUT = Path(__file__).resolve().parent
ARCH = Path('/home/levinsonchen/project/rosa-research-previous-20261108/research/_artifacts')
ARCHIVES = {
    'diagnostic': ARCH / 'rosa-baseline-diagnostic-review-20261107.zip',
    'codeact': ARCH / 'rosa-paper-pilot-review-20261108.zip',
    'multistep_reconstruction': ARCH / 'rosa-multistep-review-20261107-reconstructed.zip',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dump(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for value in obj.values():
            yield from strings(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from strings(value)


def schema_errors(value, schema, where='args'):
    # Only types/required fields are checked. Other constraints remain UNKNOWN.
    errors = []
    types = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
             'integer': int, 'number': (int, float), 'null': type(None)}
    if 'anyOf' in schema:
        if all(schema_errors(value, s, where) for s in schema['anyOf']):
            errors.append(where + ': no anyOf type match')
        return errors
    typ = schema.get('type')
    if typ in types and not isinstance(value, types[typ]):
        return [where + ': expected ' + typ]
    if isinstance(value, dict):
        errors += [where + ': missing ' + k for k in schema.get('required', []) if k not in value]
        for key, item in value.items():
            if key in schema.get('properties', {}):
                errors += schema_errors(item, schema['properties'][key], where + '.' + key)
    if isinstance(value, list):
        for i, item in enumerate(value):
            errors += schema_errors(item, schema.get('items', {}), where + '[' + str(i) + ']')
    return errors


def main():
    inventory, episodes, calls, natives, programs = [], [], [], [], []
    for corpus, path in ARCHIVES.items():
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            manifest = json.loads(z.read('MANIFEST.json')) if 'MANIFEST.json' in names else {}
            entries = manifest.get('files', manifest.get('members', manifest))
            if 'RECONSTRUCTION_MANIFEST.json' in names:
                reconstruction = json.loads(z.read('RECONSTRUCTION_MANIFEST.json'))
                entries = {x['path']: x for x in reconstruction['included_files']}
                dump('missing_multistep.json', reconstruction)
            verification = {'matched': 0, 'mismatched': [], 'missing': []}
            for name, spec in entries.items():
                if not isinstance(spec, (str, dict)):
                    continue
                expected = spec if isinstance(spec, str) else spec.get('sha256')
                if expected is None:
                    continue
                if name not in names:
                    verification['missing'].append(name)
                elif digest(z.read(name)) == expected:
                    verification['matched'] += 1
                else:
                    verification['mismatched'].append(name)
            members = [{'member': n, 'bytes': z.getinfo(n).file_size,
                        'sha256': digest(z.read(n))} for n in names if not n.endswith('/')]
            inventory.append({'corpus': corpus, 'path': str(path), 'sha256': digest(path.read_bytes()),
                              'members_count': len(names), 'crc_bad_member': z.testzip(),
                              'manifest_verification': verification, 'members': members})
            judgments = {}
            archived_scores = {}
            if corpus == 'diagnostic':
                obj = json.loads(z.read('review/independent-judgments.json'))
                rows = obj if isinstance(obj, list) else next(v for v in obj.values() if isinstance(v, list))
                judgments = {r['episode']: r for r in rows}
            if corpus == 'codeact':
                for score_member in ('research/_artifacts/paper-pilot-analysis-20261108/continuation-audit.json',
                                     'research/_artifacts/paper-pilot-analysis-20261108/original-before-only.json'):
                    for row in json.loads(z.read(score_member))['episodes']:
                        if 'path' in row:
                            archived_scores[row['path'] + '/trace.jsonl'] = dict(row, score_member=score_member)
                        elif 'index' in row:
                            prefix = 'research/_artifacts/paper-pilot-evaluation-20261107/'
                            archived_scores[prefix + f"{row['index']:02d}-{row['task']}-{row['arm']}/trace.jsonl"] = dict(row, score_member=score_member)
            for member in names:
                if not member.endswith('/trace.jsonl'):
                    continue
                events, bad = [], []
                for line, raw in enumerate(z.read(member).splitlines(), 1):
                    try:
                        events.append(dict(json.loads(raw), _line=line))
                    except (ValueError, TypeError):
                        bad.append(line)
                if not events:
                    continue
                first = events[0]
                group = ('oracle' if '/oracle/' in member else 'primary' if '/primary-v1/' in member else 'replay') if corpus == 'diagnostic' else (
                    'continuation' if '/paper-pilot-continuation-' in member else
                    'evaluation' if '/paper-pilot-evaluation-' in member else 'development')
                ep = member.split('/')[-2]
                record = {'corpus': corpus, 'group': group, 'member': member, 'episode': ep,
                          'task': first.get('task'), 'arm': first.get('arm'), 'bad_json_lines': bad,
                          'model_starts': sum(e.get('kind') == 'model_start' for e in events),
                          'model_ends': sum(e.get('kind') == 'model_end' for e in events),
                          'episode_end': any(e.get('kind') in ('episode_end', 'replay_end') for e in events),
                          'usage': dict(Counter()), 'frozen_judgment': judgments.get(ep),
                          'archived_automatic_score': archived_scores.get(member),
                          'freshness': 'unknown: no continuous graph/incarnation log'}
                if member[:-len('trace.jsonl')] + 'answer.json' in names:
                    record['answer'] = json.loads(z.read(member[:-len('trace.jsonl')] + 'answer.json'))
                prior_outputs, prior_native, schema, turn = [], {}, {}, 0
                starts = {e.get('run_id'): e for e in events if e.get('kind') == 'tool_start'}
                finishes = {e.get('run_id'): e for e in events if e.get('kind') in ('tool_end', 'tool_error')}
                claimed_starts = set()
                for e in events:
                    kind, line = e.get('kind'), e['_line']
                    if kind == 'model_start':
                        schema = {s['function']['name']: s['function'].get('parameters', {})
                                  for s in e.get('schemas', []) if 'function' in s}
                    if kind == 'model_end':
                        turn += 1
                        for k, v in (e.get('usage') or {}).items():
                            if isinstance(v, (int, float)):
                                record['usage'][k] = record['usage'].get(k, 0) + v
                        msg = e.get('message', {})
                        for proposal in msg.get('tool_calls', []):
                            name, args = proposal.get('name'), proposal.get('args', {})
                            matching_start, matching_finish = None, None
                            for candidate in events:
                                if candidate.get('kind') != 'tool_start' or candidate['_line'] <= line or candidate['_line'] in claimed_starts or candidate.get('name') != name:
                                    continue
                                try:
                                    observed_args = ast.literal_eval(candidate.get('input', '{}')) if isinstance(candidate.get('input'), str) else candidate.get('input')
                                except (ValueError, SyntaxError):
                                    continue
                                if observed_args == args:
                                    matching_start = candidate
                                    matching_finish = finishes.get(candidate.get('run_id'))
                                    claimed_starts.add(candidate['_line'])
                                    break
                            entities = []
                            for key in ('node_name', 'nodes', 'topics', 'topic_name', 'topic'):
                                if key in args:
                                    for entity in strings(args[key]):
                                        matches = [(ln, tm) for ln, tm, output in prior_outputs
                                                   if entity.startswith('/') and re.search(
                                                       r'(?<![\w/])' + re.escape(entity) + r'(?![\w/])', output)]
                                        entities.append({'argument': key, 'identity': entity,
                                                         'prior_output_matches': matches,
                                                         'latest_age_seconds': e.get('monotonic', 0) - matches[-1][1] if matches else None,
                                                         'status': 'textually observed; freshness unknown' if matches else 'no prior textual observation found'})
                            calls.append({'corpus': corpus, 'group': group, 'episode': ep, 'member': member,
                                          'line': line, 'turn': turn, 'time': e.get('monotonic'),
                                          'name': name, 'args': args, 'id': proposal.get('id'),
                                          'tool_start_line': matching_start['_line'] if matching_start else None,
                                          'tool_finish': matching_finish,
                                          'output_bytes': len(json.dumps(matching_finish.get('output')).encode()) if matching_finish else None,
                                          'grounding': entities,
                                          'legality': schema_errors(args, schema[name]) if name in schema else ['tool absent from recorded schema'],
                                          'semantic_source': 'unknown: requires task-level review',
                                          'freshness': 'unknown', 'avoidable_model_turn': 'unproven'})
                        for invalid in msg.get('invalid_tool_calls', []):
                            calls.append({'corpus': corpus, 'group': group, 'episode': ep, 'member': member,
                                          'line': line, 'turn': turn, 'invalid_tool_call': invalid})
                    if kind in ('tool_end', 'tool_error'):
                        output = json.dumps(e.get('output', e.get('error')), ensure_ascii=False)
                        prior_outputs.append((line, e.get('monotonic', 0), output))
                        start = starts.get(e.get('run_id'), {})
                        if start.get('name') == 'run_read_program':
                            programs.append({'corpus': corpus, 'group': group, 'episode': ep, 'member': member,
                                             'line': line, 'input': start.get('input'), 'event': e,
                                             'native_calls': sum(x.get('kind') in ('ros_end', 'ros_error') and
                                                                 start.get('_line', line) < x['_line'] < line for x in events)})
                    if kind in ('ros_end', 'ros_error'):
                        command = e.get('command')
                        key = json.dumps(command, sort_keys=True)
                        previous = prior_native.get(key)
                        native = {'corpus': corpus, 'group': group, 'episode': ep, 'member': member,
                                  'line': line, 'time': e.get('monotonic'), 'command': command,
                                  'tool_run_id': e.get('tool_run_id'), 'returncode': e.get('returncode'),
                                  'stdout': e.get('stdout'), 'stderr': e.get('stderr'), 'error': e.get('error'),
                                  'seconds': e.get('seconds'), 'transport': 'process_success' if e.get('returncode') == 0 else 'process_failure_or_exception',
                                  'empty_stdout': e.get('returncode') == 0 and not (e.get('stdout') or '').strip(),
                                  'prior_identical_command_line': previous['_line'] if previous else None,
                                  'same_stdout_as_prior': e.get('stdout') == previous.get('stdout') if previous else None,
                                  'same_observation_time': False if previous else None,
                                  'proven_redundant': 'unknown: equality across different times is insufficient'}
                        natives.append(native)
                        prior_native[key] = e
                episodes.append(record)
    summary = {}
    for corpus, group in sorted({(e['corpus'], e['group']) for e in episodes}):
        es = [e for e in episodes if (e['corpus'], e['group']) == (corpus, group)]
        cs = [e for e in calls if (e['corpus'], e['group']) == (corpus, group)]
        ns = [e for e in natives if (e['corpus'], e['group']) == (corpus, group)]
        ps = [e for e in programs if (e['corpus'], e['group']) == (corpus, group)]
        summary[corpus + '/' + group] = {
            'episodes': len(es), 'model_starts': sum(e['model_starts'] for e in es),
            'model_ends': sum(e['model_ends'] for e in es), 'proposals': len(cs),
            'native_ends_or_errors': len(ns), 'native_nonzero_or_exception': sum(e['returncode'] != 0 for e in ns),
            'exact_repeated_commands': sum(e['prior_identical_command_line'] is not None for e in ns),
            'repeated_same_stdout': sum(e['prior_identical_command_line'] is not None and e['same_stdout_as_prior'] for e in ns),
            'empty_success_stdout': sum(e['empty_stdout'] for e in ns),
            'schema_errors': sum(bool(e.get('legality', [])) for e in cs),
            'usage': dict(sum((Counter(e['usage']) for e in es), Counter())),
            'program_attempts': len(ps), 'program_output_samples': [p['event'] for p in ps],
            'bad_json_lines': sum(len(e['bad_json_lines']) for e in es),
            'frozen_judgments': dict(Counter(str(e['frozen_judgment'].get('strict_correct')) for e in es if e['frozen_judgment'])),
        }
    dump('inventory.json', inventory)
    dump('episodes.json', episodes)
    dump('programs.json', programs)
    dump('summary.json', summary)
    for name, rows in [('calls.jsonl', calls), ('native_calls.jsonl', natives)]:
        with (OUT / name).open('w') as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'program_output_samples'} for k, v in summary.items()}, indent=2))


if __name__ == '__main__':
    main()
