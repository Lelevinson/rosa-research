"""File-only shadow replay. No ROS, HTTP, model, evaluator or experiment imports.

Predictions consume Boundary.state only. The following observed action is compared
after every policy result has been frozen. Equality is not permission or necessity.
Run with uv run --no-sync python .../replay.py after prepare_inputs.py.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ART = next(p for p in HERE.parents if p.name == 'research') / '_artifacts' / HERE.name
STOP = 'STOP'
UNKNOWN = 'UNKNOWN'
# Source-inspected informational operations only. Names alone never authorize
# execution; this set merely refines a retrospective upper bound.
READ_INTERFACE_NAMES = {'ros2_node_list', 'ros2_node_info', 'ros2_topic_list',
                        'ros2_topic_info', 'ros2_topic_echo', 'ros2_service_list',
                        'ros2_service_info', 'ros2_param_list', 'ros2_param_get'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def shape(value):
    if isinstance(value, dict):
        return {k: shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return type(value).__name__


def paths(value, path=()):
    """Include containers: list-valued public arguments can bind as one value."""
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from paths(item, path + (index,))


def lookup(value, path):
    for component in path:
        value = value[component]
    return value


def wilson_lower(correct, total, z=1.645):
    if total == 0:
        return 0.0
    p = correct / total
    return (p + z*z/(2*total) - z*math.sqrt(p*(1-p)/total + z*z/(4*total*total))) / (1+z*z/total)


def action(message):
    if message.get('invalid_tool_calls'):
        return UNKNOWN
    meta = message.get('response_metadata', {})
    if meta.get('done_reason', meta.get('finish_reason')) in ('length', 'max_tokens'):
        return UNKNOWN
    calls = message.get('tool_calls', [])
    if not calls:
        return STOP
    if any(not isinstance(c.get('args', c.get('arguments', {})), dict) for c in calls):
        return UNKNOWN
    return [{'name': c['name'], 'args': c.get('args', c.get('arguments', {}))} for c in calls]


def names(value):
    return value if isinstance(value, str) else canonical([c['name'] for c in value])


@dataclass
class Boundary:
    state: dict
    observed: object
    source: dict


def parse_trace(path, provenance):
    events = [dict(json.loads(line), source_line=i) for i, line in enumerate(path.read_text().splitlines(), 1)]
    history, receipts, errors, pending_start = [], [], [], None
    pending_state, starts = None, {}
    rows, incomplete = [], 0
    for event in events:
        kind = event.get('kind')
        if kind == 'model_start':
            if pending_start is not None:
                incomplete += 1
            pending_start = event
            pending_state = copy.deepcopy({'history': history, 'receipts': receipts,
                'error': any(errors), 'registry': event.get('schemas', []),
                'request': provenance.get('request', '')})
        elif kind == 'tool_start':
            args = event.get('arguments', event.get('input', {}))
            if isinstance(args, str):
                try:
                    args = ast.literal_eval(args)
                except (ValueError, SyntaxError):
                    args = None
            starts[event.get('tool_id', event.get('run_id'))] = {
                'name': event.get('name'), 'arguments': args, 'line': event['source_line']}
        elif kind in ('tool_end', 'tool_error'):
            origin = starts.get(event.get('tool_id', event.get('run_id')), {})
            receipts.append({'name': event.get('name', origin.get('name')), 'output': event.get('output'),
                             'source_arguments': origin.get('arguments'), 'call_line': origin.get('line'),
                             'line': event['source_line'], 'error': kind == 'tool_error'})
            errors.append(kind == 'tool_error')
        elif kind in ('ros_end', 'cli_end', 'native_end'):
            if event.get('returncode', 0) != 0:
                errors.append(True)
        elif kind in ('ros_error', 'guard_rejection', 'budget_rejection', 'tool_validation_error'):
            errors.append(True)
        elif kind == 'model_end':
            if pending_start is None:
                incomplete += 1
                continue
            state = pending_state
            # No current model output, episode ID, task ID or scorer enters state.
            rows.append(Boundary(state, action(event.get('message', {})),
                        dict(provenance, line=event['source_line'],
                             state_cutoff_line=pending_start['source_line'],
                             model_seconds=event.get('monotonic', 0)-pending_start.get('monotonic', 0))))
            history.append(names(rows[-1].observed))
            receipts, errors, pending_start = [], [], None
    return rows, incomplete + (pending_start is not None)


def state_key(state, mode, ignore_outcome=False):
    history = state['history']
    k = 2 if mode in ('ngram2', 'candidate2') else 1
    context = history[-k:]
    if not context or (k == 2 and len(context) < 2):
        return None
    key = [context]
    if mode in ('conditional', 'candidate1', 'candidate2', 'no_provenance', 'no_cost', 'no_outcome'):
        if mode != 'no_outcome' and not ignore_outcome:
            key.append(state['error'])
        key.append(sha(canonical(state['registry']).encode()))
        key.append([(r['name'], shape(r['output'])) for r in state['receipts']])
    return canonical(key)


def available_origins(state):
    origins = []
    for i, receipt in enumerate(state['receipts']):
        if 'call_line' in receipt and receipt['call_line'] is None:
            continue  # Unmatched real receipt has no certified causal origin.
        # Text is not silently parsed as a structured response.
        if isinstance(receipt['output'], (dict, list)) and not receipt['error']:
            for path, value in paths(receipt['output']):
                origins.append(({'receipt': i, 'path': list(path), 'shape': shape(receipt['output']),
                                 'source_tool': receipt['name'],
                                 'source_arguments': copy.deepcopy(receipt.get('source_arguments'))}, value))
    return origins


def learn_template(observed, state):
    if isinstance(observed, str):
        return observed
    origins = available_origins(state)
    result = []
    for call in observed:
        bindings = {}
        for key, value in call['args'].items():
            matches = [ref for ref, item in origins if type(item) is type(value) and item == value]
            # Keep every alternative: equal values from distinct sources are ambiguous.
            bindings[key] = {'origins': matches, 'type': type(value).__name__}
        result.append({'name': call['name'], 'bindings': bindings})
    return result


def instantiate(template, state):
    if isinstance(template, str):
        return template, []
    result, problems = [], []
    for call in template:
        arguments = {}
        for key, spec in call['bindings'].items():
            refs = spec['origins']
            if len(refs) != 1:
                problems.append('ambiguous_origin' if refs else 'missing_origin')
                continue
            ref = refs[0]
            try:
                receipt = state['receipts'][ref['receipt']]
                if receipt['name'] != ref['source_tool'] or receipt.get('source_arguments') != ref['source_arguments']:
                    problems.append('source_identity_changed')
                    continue
                if receipt['error'] or shape(receipt['output']) != ref['shape']:
                    problems.append('changed_schema_or_error')
                    continue
                value = lookup(receipt['output'], ref['path'])
                if type(value).__name__ != spec['type']:
                    problems.append('invalid_type')
                    continue
                # Uniqueness must hold in the CURRENT context, not only training.
                matches = [r for r, v in available_origins(state) if type(v) is type(value) and v == value]
                if len(matches) != 1:
                    problems.append('ambiguous_current_origin')
                    continue
                arguments[key] = value
            except (IndexError, KeyError, TypeError):
                problems.append('missing_current_path')
        result.append({'name': call['name'], 'args': arguments})
    return result, sorted(set(problems))


class Predictor:
    """Ordinary conditional counts; candidate adds supported variable-order backoff.

    The constrained parent score reuses only frequency*support confidence. It
    deliberately omits SimCSE/domain fill and is NOT a faithful parent replication.
    """
    def __init__(self, mode):
        self.mode = mode
        self.counts = defaultdict(Counter)
        self.templates = defaultdict(Counter)
        self.parent_paths = Counter()
        self.parent_templates = defaultdict(Counter)
        self.calibration = defaultdict(Counter)

    def fit(self, rows):
        episodes = defaultdict(list)
        for row in rows:
            if row.observed == UNKNOWN:
                episodes[row.source['copy']].append(UNKNOWN)
            if row.observed != UNKNOWN:
                episodes[row.source['copy']].append(names(row.observed))
                self.parent_templates[names(row.observed)][canonical(learn_template(row.observed, row.state))] += 1
        segments = []
        for sequence in episodes.values():
            segment = []
            for label in sequence + [UNKNOWN]:
                if label == UNKNOWN:
                    if segment:
                        segments.append(tuple(segment))
                    segment = []
                else:
                    segment.append(label)
        self.parent_paths = Counter(segments)
        modes = ['candidate2', 'candidate1'] if self.mode in ('candidate', 'conditional_backoff', 'no_outcome', 'no_provenance', 'no_cost') else [self.mode]
        for row in rows:
            if row.observed == UNKNOWN:
                continue
            for mode in modes:
                key = state_key(row.state, mode, self.mode == 'no_outcome')
                if key is None:
                    continue
                self.counts[(mode, key)][names(row.observed)] += 1
                signature = canonical(learn_template(row.observed, row.state))
                self.templates[(mode, key, names(row.observed))][signature] += 1

    def calibrate(self, development):
        """Frozen development-only exact behavioral labels, never need labels."""
        for row in development:
            if row.observed == UNKNOWN or not row.state['history']:
                continue
            result = self.predict(row.state)
            if result['prediction'] is not None:
                cell = self.calibration[(result['state_key'], result['prediction'])]
                cell['total'] += 1
                cell['correct'] += canonical(result.get('proposed')) == canonical(row.observed)

    def predict(self, state):
        modes = ['candidate2', 'candidate1'] if self.mode in ('candidate', 'conditional_backoff', 'no_outcome', 'no_provenance', 'no_cost') else [self.mode]
        mode, key, counts = modes[-1], None, Counter()
        for proposed_mode in modes:
            proposed_key = state_key(state, proposed_mode, self.mode == 'no_outcome')
            proposed_counts = self.counts.get((proposed_mode, proposed_key), Counter())
            if sum(proposed_counts.values()) >= 3:
                mode, key, counts = proposed_mode, proposed_key, proposed_counts
                break
        if self.mode == 'parent_constrained':
            # Parent source uses first contiguous chain match, not generic subsequence.
            counts = Counter()
            query = tuple(state['history'][-2:])
            for path, frequency in self.parent_paths.items():
                for position in range(len(path)-len(query)+1):
                    if path[position:position+len(query)] == query:
                        if position+len(query) < len(path):
                            counts[path[position+len(query)]] += frequency
                        break
            key = canonical(query)
        if not counts:
            return {'prediction': None, 'support': 0, 'reason': 'insufficient_support', 'admission': False, 'execute': False}
        predicted, count = counts.most_common(1)[0]
        total = sum(counts.values())
        template_counts = (self.parent_templates[predicted] if self.mode == 'parent_constrained'
                           else self.templates[(mode, key, predicted)])
        signature, template_count = template_counts.most_common(1)[0]
        proposed, problems = instantiate(json.loads(signature), state)
        probability = count / total
        parent_score = probability * (1-1.1**(-total))
        reasons = []
        if self.mode == 'parent_constrained':
            if parent_score <= 0.4:
                reasons.append('parent_score_threshold')
        elif probability < 0.9:
            reasons.append('empirical_threshold')
        if state['error']:
            reasons.append('previous_error')
        reasons.extend(problems)
        if predicted == STOP:
            reasons.append('STOP_handoff')
        elif predicted == UNKNOWN:
            reasons.append('unknown_prediction')
        else:
            # No trace-only estimate can certify action need or permitted flow.
            reasons.extend(['needed_unlabeled', 'readonly_permission_not_certified'])
            if any(c.get('args') for c in proposed):
                reasons.extend(['permitted_flow_unknown', 'freshness_unknown'])
        calibration = self.calibration[(key, predicted)]
        lower = wilson_lower(calibration['correct'], calibration['total'])
        if self.mode in ('candidate', 'conditional_backoff', 'no_outcome', 'no_cost') and lower < 0.95:
            reasons.append('development_complete_action_lower_bound')
        if self.mode in ('candidate', 'conditional_backoff', 'no_outcome', 'no_provenance'):
            reasons.append('net_benefit_unidentified')
        return {'prediction': predicted, 'proposed': proposed, 'support': total,
                'probability': probability, 'parent_score': parent_score,
                'template_support': template_count, 'behavioral_template_lcb': lower,
                'development_calibration': dict(calibration),
                'bindings': json.loads(signature), 'problems': problems,
                'reason': sorted(set(reasons)), 'execute': False,
                'admission': not reasons,
                'state_key': key, 'state_order': mode}


def main():
    manifest = json.loads((ART/'INPUTS_FROZEN.json').read_text())
    all_rows, incomplete = [], 0
    for entry in manifest['traces']:
        path = ART/entry['copy']
        assert sha(path.read_bytes()) == entry['sha256'], path
        rows, missing = parse_trace(path, entry)
        all_rows.extend(rows)
        incomplete += missing
    training = [r for r in all_rows if r.source['split'] == 'train']
    modes = ['ngram1', 'ngram2', 'conditional', 'conditional_backoff', 'parent_constrained', 'candidate',
             'no_outcome', 'no_provenance', 'no_cost']
    summaries, predictions, fitting = {}, [], {}
    for mode in modes:
        policy = Predictor(mode)
        start = time.perf_counter()
        policy.fit(training)
        policy.calibrate([r for r in all_rows if r.source['split'] == 'dev'])
        fitting[mode] = time.perf_counter()-start
        summaries[mode] = {}
        for split in ['train', 'dev', 'historical_validation', 'temporal_validation']:
            counters = Counter()
            for row in (r for r in all_rows if r.source['split'] == split):
                if not row.state['history']:
                    counters['initial_decisions'] += 1
                    continue
                counters['boundaries'] += 1
                start = time.perf_counter()
                frozen = policy.predict(row.state)
                elapsed = time.perf_counter()-start
                # The next actual action is inspected ONLY AFTER prediction.
                actual = names(row.observed)
                counters['policy_seconds'] += elapsed
                counters['STOP_actual'] += actual == STOP
                counters['unknown_actual'] += actual == UNKNOWN
                counters['actual_tool_boundary_upper_bound'] += actual not in (STOP, UNKNOWN)
                counters['readonly_interface_boundary_upper_bound'] += (
                    isinstance(row.observed, list) and
                    all(c['name'] in READ_INTERFACE_NAMES for c in row.observed))
                counters['multicall_boundaries'] += isinstance(row.observed, list) and len(row.observed)>1
                counters['predictions'] += frozen['prediction'] is not None
                counters['execute_admissions'] += frozen['execute']
                counters['policy_admissions'] += frozen['admission']
                exact = canonical(frozen.get('proposed')) == canonical(row.observed)
                counters['exact_action_args_or_STOP'] += exact
                counters['exact_tool_args_without_STOP'] += exact and actual not in (STOP, UNKNOWN)
                counters['name_group_match'] += frozen['prediction'] == actual
                counters['missing_or_ambiguous_binding'] += bool(frozen.get('problems'))
                counters['missed_opportunity_diagnostic'] += exact and not frozen['execute'] and actual not in (STOP, UNKNOWN)
                counters['false_continuation_name_proposal'] += actual == STOP and frozen['prediction'] not in (STOP, UNKNOWN, None)
                counters['wrong_name_proposal'] += frozen['prediction'] is not None and frozen['prediction'] != actual and actual != UNKNOWN
                predictions.append({'mode': mode, 'source': row.source, 'prediction_frozen': frozen,
                                    'actual_after_prediction': row.observed,
                                    'exact_behavioral_match': exact, 'policy_seconds': elapsed})
            summaries[mode][split] = dict(counters)
    # Compare all paired proposals and safe admissions, not just average hit rates.
    paired = defaultdict(dict)
    for row in predictions:
        paired[(row['source']['copy'], row['source']['line'])][row['mode']] = row
    contrasts = []
    for identity, rows in paired.items():
        c, e = rows['conditional'], rows['candidate']
        if c['prediction_frozen'].get('proposed') != e['prediction_frozen'].get('proposed'):
            contrasts.append({'identity': identity, 'C': c, 'E': e})
    result = {'classification': 'shadow replay only; no causal efficiency or fresh heldout claim',
              'training_seconds': fitting, 'episodes': len(manifest['traces']),
              'incomplete_model_pairs': incomplete, 'summary': summaries,
              'candidate_vs_C_raw_contrasts': len(contrasts),
              'candidate_vs_C_backoff_raw_contrasts': sum(rows['conditional_backoff']['prediction_frozen'] != rows['candidate']['prediction_frozen'] for rows in paired.values()),
              'candidate_vs_C_execute_contrasts': 0,
              'source_manifest_sha256': sha((ART/'INPUTS_FROZEN.json').read_bytes())}
    (ART/'results/summary.json').write_text(json.dumps(result, indent=2)+'\n')
    (ART/'results/predictions.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in predictions))
    (ART/'results/contrasts.json').write_text(json.dumps(contrasts, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
