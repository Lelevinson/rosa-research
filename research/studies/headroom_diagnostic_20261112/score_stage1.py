"""Offline scoring for Stage 1 runs (no inference, no ROS).

  uv run python score_stage1.py validate   re-score the 36 original baseline episodes (scorer sanity check)
  uv run python score_stage1.py 1a RUN     score a Stage 1a run directory
  uv run python score_stage1.py 1b RUN     score a Stage 1b run directory

Correctness first: exact fields against the oracle (vendored baseline audit code, unchanged) AND a support
screen (every reported value must be backed by a successful tool result in the trace). The screen is
automatic; episodes where exact and support disagree, and all failures, are listed for manual reading.
"""
import ast
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'vendor'))
import baseline_audit as audit  # noqa: E402  (vendored, unchanged)

FLOOR_1A = {'t1': 4, 't2': 3, 't3': 3, 'd1': 3, 'd2': 4, 'x1': 3}
FLOOR_1B = 3
ERROR = re.compile(r"error|Unable to find|Node not found|not found|rejected|timed out", re.I)


def read_events(path):
    return [dict(json.loads(line), line=i) for i, line in enumerate(Path(path).read_text().splitlines(), 1)]


def tool_results(events):
    """Pair tool starts and ends by run id. Returns list of dict(name, args, output, ok, line)."""
    starts, rows = {}, []
    for e in events:
        key = e.get('run_id') or e.get('tool_run_id')
        if e['kind'] == 'tool_start':
            raw = e.get('input', e.get('arguments'))
            try:
                args = raw if isinstance(raw, dict) else ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                args = {}
            starts[key] = dict(name=e['name'], args=args, line=e['line'])
        elif e['kind'] == 'tool_end' and key in starts:
            output = e.get('output')
            text = json.dumps(output) if not isinstance(output, str) else output
            rows.append(dict(starts[key], output=output, text=text, ok=not ERROR.search(text)))
    return rows


def param_values(results):
    values = {}
    for r in results:
        if r['name'] == 'ros2_param_get' and r['ok'] and isinstance(r['output'], dict):
            for param, raw in r['output'].items():
                m = re.search(r'(Boolean|Integer) value is:\s*(\S+)', str(raw))
                if m:
                    value = (m[2] == 'True') if m[1] == 'Boolean' else int(m[2])
                    values[(r['args'].get('node_name'), r['args'].get('param_name', param))] = value
    return values


def assembled(text):
    text = text.replace('\\n', '\n')
    return {f"{ns.rstrip('/')}/{name}" for name, ns in re.findall(r'Node name:\s*(\S+)\s+Node namespace:\s*(\S+)', text)}


def support_screen(task, truth, results):
    """Return the list of truth leaves NOT backed by a successful tool result."""
    good = [r for r in results if r['ok']]
    text = '\n'.join(r['text'].replace('\\n', '\n') for r in good)
    known_names = assembled(text)
    params = param_values(results)
    missing = []

    def has_string(s):
        return s in text or s in known_names

    def walk(value, path, node=None):
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str) or not has_string(key):
                    if key not in ('clocks', 'topics', 'node', 'services', 'rgb', 'pose', 'topic', 'type', 'publishers',
                                   'subscribers', 'endpoints', 'role', 'use_sim_time'):
                        missing.append(f'{path}/{key}: key not seen in a tool result')
                walk(child, f'{path}/{key}', key if path.endswith('clocks') else node)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                if path.endswith('rgb'):
                    got = params.get((truth.get('node'), 'background_' + 'rgb'[i]))
                    if got != child:
                        missing.append(f'{path}/{i}: background_{"rgb"[i]} not read')
                else:
                    walk(child, f'{path}/{i}', child.get('node') if isinstance(child, dict) else node)
        elif isinstance(value, bool):
            owner = node or truth.get('node')
            if params.get((owner, 'use_sim_time')) is not value:
                missing.append(f'{path}: use_sim_time of {owner} not read with this value')
        elif isinstance(value, int):
            name = path.rsplit('/', 1)[-1]
            label = {'publishers': 'Publisher count', 'subscribers': 'Subscription count'}.get(name)
            if label is None or f'{label}: {value}' not in text.replace('\\n', '\n'):
                if not (name == 'publishers' and f'Publisher count: {value}' in text):
                    missing.append(f'{path}: count {value} not seen')
        elif isinstance(value, str) and path.endswith('/role'):
            marker = {'publisher': 'Endpoint type: PUBLISHER', 'subscriber': 'Endpoint type: SUBSCRIPTION'}[value]
            if marker not in text:
                missing.append(f'{path}: {value!r} endpoint type not seen')
        elif isinstance(value, str):
            if not has_string(value):
                missing.append(f'{path}: {value!r} not seen in a tool result')

    walk(truth, '')
    return missing


def episode_metrics(events):
    starts = [e for e in events if e['kind'] == 'model_start']
    ends = [e for e in events if e['kind'] == 'model_end']
    calls = [len(e['message'].get('tool_calls', [])) for e in ends]
    lengths = [e for e in ends if (e.get('response_metadata') or {}).get('done_reason') == 'length'
               or (e.get('response_metadata') or {}).get('status') not in (None, 'completed', 'stop')
               and 'done_reason' not in (e.get('response_metadata') or {})]
    final = [e for e in events if e['kind'] == 'episode_end']
    answer = final[-1].get('answer') if final else None
    return dict(requests=len(starts), completed=len(ends), calls_per_request=calls, max_calls=max(calls, default=0),
                multi_call_requests=sum(c > 1 for c in calls),
                input_tokens=sum((e.get('usage') or {}).get('input_tokens', 0) for e in ends),
                output_tokens=sum((e.get('usage') or {}).get('output_tokens', 0) for e in ends),
                model_seconds=sum(e['seconds'] for e in ends), model_errors=sum(e['kind'] == 'model_error' for e in events),
                native_ops=sum(e['kind'] == 'ros_start' for e in events), guard_rejections=sum(e['kind'] == 'guard_rejection' for e in events),
                native_failures=sum(e.get('returncode', 0) != 0 for e in events if e['kind'] == 'ros_end'),
                native_timeouts=sum(e['kind'] == 'ros_error' for e in events),
                length_events=[dict(line=e['line'], meta=(e.get('response_metadata') or {}).get('done_reason')) for e in lengths],
                iteration_cap=bool(answer) and 'iteration limit' in answer.lower(),
                episode_seconds=final[-1].get('seconds') if final else None, answer=answer,
                error=final[-1].get('error') if final else 'no episode_end')


def score_1a(run):
    run = Path(run)
    snapshots = {p.parent.name: json.loads(p.read_text()) for p in sorted((run / 'oracle').glob('*/snapshot.json'))}
    truths = {label: audit.expected(data) for label, data in snapshots.items()}
    initial = truths['before']
    rows = []
    for line in (run / 'attempts.jsonl').read_text().splitlines():
        attempt = json.loads(line)
        directory = run / attempt['directory']
        if not (directory / 'trace.jsonl').exists():
            rows.append(dict(attempt, status='no trace'))
            continue
        events = read_events(directory / 'trace.jsonl')
        start = next(e for e in events if e['kind'] == 'episode_start')
        task, arm = start['task']['id'], start['arm']
        metrics = episode_metrics(events)
        parsed, _ = audit.first_object(metrics['answer'])
        issues = audit.differences(audit.canonical(parsed), audit.canonical(initial[task]))
        stable = all(audit.canonical(t[task]) == audit.canonical(initial[task]) for t in truths.values())
        missing = support_screen(task, initial[task], tool_results(events))
        exact = not issues and stable
        supported = exact and not missing
        rows.append(dict(episode=directory.name, task=task, arm=arm, repeat=start['repeat'], exact=exact, support_missing=missing,
                         supported_complete=supported, needs_manual=(exact != (not missing)) or not exact,
                         issues=issues, floor=FLOOR_1A[task], **metrics))
    return dict(truth=initial, oracle_stable={k: audit.canonical(v) == audit.canonical(initial) for k, v in truths.items()}, episodes=rows)


def score_1b(run):
    run = Path(run)
    rows = []
    for directory in sorted(p for p in run.iterdir() if p.is_dir() and p.name.startswith('N')):
        if not (directory / 'trace.jsonl').exists():
            continue
        events = read_events(directory / 'trace.jsonl')
        start = next(e for e in events if e['kind'] == 'episode_start')
        n = start['task']['n']
        truth = {f'/scale/n{i:02d}': (i % 3 == 0) for i in range(n)}
        metrics = episode_metrics(events)
        parsed, _ = audit.first_object(metrics['answer'])
        format_ok = isinstance(parsed, dict) and isinstance(parsed.get('clocks'), dict)
        if format_ok:
            clocks = parsed['clocks']
        elif isinstance(parsed, dict):  # revision 5: a flat node->bool object still reports the values; format is scored separately
            clocks = {k: v for k, v in parsed.items() if isinstance(k, str) and k.startswith('/scale/')}
        else:
            clocks = {}
        params = param_values(tool_results(events))
        correct = [k for k, v in truth.items() if clocks.get(k) is v]
        supported = [k for k in correct if params.get((k, 'use_sim_time')) is truth[k]]
        extra = [k for k in clocks if k not in truth]
        parallel_ok = any(c >= n for c in metrics['calls_per_request'])
        listed = set()  # nodes that appeared in any successful node_list result the agent received
        for r in tool_results(events):
            if r['name'] == 'ros2_node_list' and r['ok']:
                listed |= set(re.findall(r'/scale/n\d\d', r['text']))
        supported_of_listed = [k for k in supported if k in listed]
        rows.append(dict(episode=directory.name, n=n, provider=start['provider'], label=directory.name.split('-')[-1],
                         format_ok=format_ok, coverage_correct=len(correct), coverage_supported=len(supported), listed_by_agent=len(listed), never_listed=sorted(set(truth) - listed),
                         coverage_supported_of_listed=len(supported_of_listed), extra_nodes=extra, floor=FLOOR_1B,
                         requests_over_floor=metrics['requests'] - FLOOR_1B, all_in_one_request=parallel_ok, **metrics))
    return rows


def validate():
    """Re-score the original 36 baseline episodes with the Stage 1 scorer."""
    base = Path.home() / 'project/rosa-research-previous-20261108/research/_artifacts/baseline-diagnostic/primary-v1'
    judgments = {j['episode']: j['strict_correct'] for j in json.loads(
        (Path.home() / 'project/rosa-research-previous-20261108/research/baseline_diagnostic/independent-judgments.json').read_text())['episodes']}
    run_rows = []
    snapshots = {p.parent.name: json.loads(p.read_text()) for p in sorted((base / 'oracle').glob('*/snapshot.json'))}
    initial = audit.expected(snapshots['before'])
    for line in (base / 'attempts.jsonl').read_text().splitlines():
        attempt = json.loads(line)
        events = read_events(base / attempt['directory'] / 'trace.jsonl')
        start = next(e for e in events if e['kind'] == 'episode_start')
        task, arm = start['task']['id'], start['arm']
        answer = next(e for e in events if e['kind'] == 'episode_end').get('answer')
        parsed, _ = audit.first_object(answer)
        exact = not audit.differences(audit.canonical(parsed), audit.canonical(initial[task]))
        missing = support_screen(task, initial[task], tool_results(events))
        run_rows.append((attempt['directory'], arm, exact, not missing, judgments[attempt['directory']]))
    agree_exact = sum(r[2] == r[4] for r in run_rows)
    agree_both = sum((r[2] and r[3]) == r[4] for r in run_rows)
    print(f'{len(run_rows)} baseline episodes; exact==independent judgment: {agree_exact}; exact&support==judgment: {agree_both}')
    for arm in 'ABC':
        print(arm, 'exact', sum(r[2] for r in run_rows if r[1] == arm), 'exact&support', sum(r[2] and r[3] for r in run_rows if r[1] == arm),
              'independent', sum(r[4] for r in run_rows if r[1] == arm))
    for r in run_rows:
        if (r[2] and r[3]) != r[4]:
            print('DISAGREE', r)


if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'validate':
        validate()
    else:
        result = (score_1a if command == '1a' else score_1b)(sys.argv[2])
        out = Path(sys.argv[2]) / f'scores_{command}.json'
        out.write_text(json.dumps(result, indent=1, default=str))
        print('wrote', out)
