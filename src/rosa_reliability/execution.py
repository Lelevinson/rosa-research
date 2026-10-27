"""Shared contracts, operation bounds and provenance; no model or ROS dependency."""
from contextlib import contextmanager
from copy import deepcopy
import json
import math
import threading
import time


class ControlledStop(Exception):
    """A normal Exception so LangChain emits its terminal tool-error callback."""


class OperationBudget:
    def __init__(self, limit=10, seconds=180):
        if type(limit) is not int or limit < 1 or seconds <= 0:
            raise ValueError('positive operation/time limits required')
        self.limit, self.seconds = limit, seconds
        self.started = time.monotonic()
        self.events = []
        self.lock = threading.Lock()

    def reserve(self, kind, actor):
        with self.lock:
            if time.monotonic() - self.started >= self.seconds:
                raise ControlledStop('trial_deadline_exhausted_before_dispatch')
            if len(self.events) >= self.limit:
                raise ControlledStop('native_operation_budget_exhausted_before_dispatch')
            event = {'operation_id': len(self.events) + 1, 'kind': kind,
                     'actor': actor, 'status': 'DISPATCHING', 'started': time.monotonic()}
            self.events.append(event)
            return event


class ExecutionSession:
    """Transport methods are bounded read(node,names) and write(node,values).

    Reports never cause hidden oracle reads or automatic value/identifier repairs.
    Fresh verification uses the same public transport available to all agents.
    """

    def __init__(self, transport, targets, *, structured_feedback=False,
                 automatic_verification=False, operation_limit=10, seconds=180,
                 validation_limit=3, tool_limit=16, tolerance=0.01, write_limit=None, tracer=None):
        if not targets or any(not self.canonical(n) or not v for n, v in targets.items()):
            raise ValueError('nonempty node-keyed targets with canonical IDs required')
        if tolerance < 0 or not math.isfinite(tolerance):
            raise ValueError('finite nonnegative tolerance required')
        self.transport, self.targets = transport, deepcopy(targets)
        self.structured_feedback = structured_feedback
        self.automatic_verification = automatic_verification
        self.budget = OperationBudget(operation_limit, seconds)
        self.validation_limit, self.tool_limit = validation_limit, tool_limit
        self.write_limit, self.write_count = write_limit, 0
        self.tolerance, self.tracer = tolerance, tracer
        self.events, self.observations, self.reports = [], [], []
        self.validation_errors = self.tool_calls = 0
        self.last_write = 0
        self.verification = None

    @staticmethod
    def canonical(node):
        import re
        return isinstance(node, str) and re.fullmatch(r'/[A-Za-z_][A-Za-z_0-9]*(?:/[A-Za-z_][A-Za-z_0-9]*)*', node) is not None

    @contextmanager
    def span(self, name, attributes=None):
        if self.tracer is None:
            yield None
            return
        from opentelemetry.trace import Status, StatusCode
        span = self.tracer.start_span(name)
        from opentelemetry.trace import use_span
        span.set_attribute('openinference.span.kind', 'TOOL')
        for key, value in (attributes or {}).items():
            span.set_attribute(key, value)
        try:
            with use_span(span, end_on_exit=False):
                yield span
        except BaseException as error:
            span.set_status(Status(StatusCode.ERROR, type(error).__name__))
            span.record_exception(error)
            raise
        finally:
            span.end()

    @contextmanager
    def tool_call(self, name, args):
        self.tool_calls += 1
        event = {'type': 'tool', 'call_index': self.tool_calls, 'name': name,
                 'input': deepcopy(args), 'status': 'STARTED'}
        self.events.append(event)
        with self.span('reliability.tool.' + name, {'reliability.call_index': self.tool_calls}) as span:
            if span:
                event['span_id'] = format(span.get_span_context().span_id, '016x')
            try:
                if self.tool_calls > self.tool_limit:
                    raise ControlledStop('tool_attempt_budget_exhausted')
                yield event
                event['status'] = 'RETURNED'
            except BaseException as error:
                event.update(status='ERROR', error_type=type(error).__name__)
                raise

    def feedback(self, code, details):
        from langchain_core.tools import ToolException
        self.validation_errors += 1
        self.events.append({'type': 'validation', 'code': code, 'details': deepcopy(details),
                            'attempt': self.validation_errors, 'native_dispatch_for_rejected_call': False})
        if self.validation_errors > self.validation_limit:
            raise ControlledStop('validation_retry_budget_exhausted')
        facts = {'code': code, 'details': details, 'rejected': True,
                 'corrections_remaining': self.validation_limit - self.validation_errors}
        text = json.dumps(facts, sort_keys=True) if self.structured_feedback else '; '.join(
            f'{key}={json.dumps(value, sort_keys=True)}' for key, value in facts.items())
        raise ToolException(text)

    def native(self, kind, actor, function):
        event = self.budget.reserve(kind, actor)
        with self.span('reliability.native.' + kind, {'reliability.operation_id': event['operation_id'],
                                                   'reliability.actor': actor}):
            try:
                result = function()
                event.update(status='RETURNED', result=deepcopy(result))
                return result, event['operation_id']
            except BaseException as error:
                event.update(status='ERROR', error_type=type(error).__name__)
                raise
            finally:
                event['finished'] = time.monotonic()

    def read(self, nodes, actor='model'):
        if not nodes or len(set(nodes)) != len(nodes) or any(n not in self.targets for n in nodes):
            return self.feedback('invalid_node_scope', {'allowed_nodes': sorted(self.targets), 'submitted': nodes})
        values, provenance = {}, []
        for node in nodes:
            names = sorted(self.targets[node])
            unavailable = None
            try:
                observed, op = self.native('read', actor, lambda: self.transport.read(node, names))
            except TimeoutError:
                # Missing evidence is explicit null, never an invented sentinel.
                observed, op = {k: None for k in names}, self.budget.events[-1]['operation_id']
                unavailable = 'observation_timeout'
            if set(observed) != set(names) or any(v is not None and (type(v) not in (int, float) or not math.isfinite(v)) for v in observed.values()):
                raise RuntimeError('transport_returned_invalid_observation')
            values[node] = observed
            provenance.append({'node': node, 'operation_id': op, 'after_write': self.last_write,
                               'acquired_monotonic': time.monotonic(), 'actor': actor,
                               'unavailable': unavailable})
        observation = {'observed_values': values, 'evidence': provenance}
        self.observations.append(deepcopy(observation))
        return observation

    def write(self, node_name, values):
        if self.write_limit is not None and self.write_count >= self.write_limit:
            return self.feedback('write_prerequisite_rejected', {'reason': 'task command-request limit reached'})
        if node_name not in self.targets or not values or any(k not in self.targets.get(node_name, {}) for k in values):
            return self.feedback('invalid_write_scope', {'allowed': self.targets, 'node_name': node_name, 'fields': sorted(values)})
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in values.values()):
            return self.feedback('invalid_value_type', {'required': 'finite numeric values'})
        validator = getattr(self.transport, 'validate_write', None)
        if validator:
            error = validator(node_name, values)
            if error:
                return self.feedback('write_prerequisite_rejected', {'reason': error})
        if getattr(self.transport, 'requires_observation', False):
            known = next((o['observed_values'][node_name] for o in reversed(self.observations)
                          if node_name in o['observed_values']), None)
            if known is None or any(v is None for v in known.values()):
                return self.feedback('write_prerequisite_rejected', {'reason': 'read current state first; unavailable observations cannot authorize a write'})
        # Invalidate before dispatch: even an exception may follow a partial write.
        self.verification = None
        self.write_count += 1
        receipt, op = self.native('write', 'model', lambda: self.transport.write(node_name, values))
        self.last_write = op
        response = {'command_receipt': receipt, 'goal_verified': False}
        if self.automatic_verification:
            response['verification'] = self.verify(actor='orchestrator')
        return response

    def verify(self, actor='model'):
        # Mark this check only after a complete successful fresh acquisition.
        self.verification = None
        observation = self.read(sorted(self.targets), actor)
        unknown = any(v is None for group in observation['observed_values'].values() for v in group.values())
        attained = None if unknown else all(abs(observation['observed_values'][n][k] - value) <= self.tolerance
                                            for n, group in self.targets.items() for k, value in group.items())
        self.verification = {'after_write': self.last_write, 'goal_reached': attained,
                             'actor': actor, **deepcopy(observation)}
        self.events.append({'type': 'verification', 'actor': actor, 'goal_reached': attained,
                            'after_write': self.last_write})
        return deepcopy(self.verification)

    def report(self, status, observed_values):
        raw = {'status': status, 'observed_values': deepcopy(observed_values), 'actor': 'model'}
        self.reports.append({**raw, 'accepted': False})
        if set(observed_values) != set(self.targets) or any(set(observed_values[n]) != set(self.targets[n]) for n in self.targets):
            return self.feedback('report_scope_mismatch', {'required_nodes_and_fields': {n: sorted(v) for n, v in self.targets.items()}})
        recent = self.verification
        if recent is None or recent['after_write'] != self.last_write:
            return self.feedback('fresh_verification_required', {'available_tool': 'verify_outcome'})
        if any((observed_values[n][k] is not None if value is None else
                type(observed_values[n][k]) not in (int, float) or
                not math.isfinite(observed_values[n][k]) or
                abs(observed_values[n][k] - value) > self.tolerance)
               for n, values in recent['observed_values'].items() for k, value in values.items()):
            return self.feedback('report_observation_mismatch', {'requirement': 'report the fresh observed values without alteration'})
        if status == 'SUCCESS' and not recent['goal_reached']:
            return self.feedback('unsupported_success', {'goal_reached': recent['goal_reached']})
        expected_status = 'UNKNOWN' if recent['goal_reached'] is None else 'SUCCESS' if recent['goal_reached'] else 'FAILURE'
        if status != expected_status:
            return self.feedback('outcome_classification_mismatch', {'observed_outcome': expected_status})
        self.reports[-1].update(accepted=True, verification_actor=recent['actor'], after_write=self.last_write)
        return {'report_accepted': True, **raw, 'verification_actor': recent['actor']}

    def snapshot(self):
        return deepcopy({'events': self.events, 'operations': self.budget.events,
                         'observations': self.observations, 'reports': self.reports,
                         'verification': self.verification, 'last_write': self.last_write,
                         'validation_errors': self.validation_errors, 'tool_calls': self.tool_calls})
