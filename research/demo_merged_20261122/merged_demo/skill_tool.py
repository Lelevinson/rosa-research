"""`run_skill`: Martin's bounded macro as ONE action tool.
Each call opens a FRESH macro invocation through the public API (CapabilityRegistry.open(..., mode='macro', allowed_skills=[skill_id])) and runs it: read, at most one write,
fresh verification (read-only skills: verification only). No `rosa_reliability` file is changed. `submit_report` and the report gate are NOT offered (his `final_answer` is the only terminal).

LAB-READY LOGGING (Levinson's L4): every transport call the macro makes is logged as `internal_read` / `internal_write` with its source, actor, skill, global sequence number,
parent tool-call sequence number, monotonic and wall times, arguments and returned values (or error), and is linked afterwards to the macro's own operation id.
`skill_call_end` records whether a write was dispatched and, if not, why (the macro skips the write when the fresh read is already within tolerance: it is LOGGED, so a scorer or
a task that requires a physical movement can see it; the demo tasks start away from their targets)."""
import json
import time

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, StrictStr

from rosa_reliability.bounded_macro import MacroLimits, StateSkill
from rosa_reliability.capabilities import CapabilityRegistry, InspectionSkill

DESCRIPTION = ('Run one user-authorized skill by exact ID. It runs the bounded routine: read the current state, at most one write when needed, then a fresh verification '
               '(read-only skills only read and verify), and returns the evidence. Use it at most twice per task; do not repeat a completed skill. '
               'Inspect the returned evidence before you answer.')   # DEMO WORDING derived from the M4 select_skill description (workflow.py:157-162); 'select once' dropped on purpose


class RunSkillArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    skill_id: StrictStr


def _safe(value):
    return json.loads(json.dumps(value, default=str))


class LoggedTransport:
    """Transparent proxy: forwards everything, logs read / read_group / write calls."""
    WRAPPED = ('read', 'write', 'read_group')

    def __init__(self, inner, label, log, skill_id, parent_seq):
        self._inner, self._label, self._log, self._skill, self._parent = inner, label, log, skill_id, parent_seq
        self.logged = []

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name in self.WRAPPED and callable(attr):
            return lambda *args, **kwargs: self._call(name, attr, args, kwargs)
        return attr

    def _call(self, name, function, args, kwargs):
        kind = 'internal_write' if name == 'write' else 'internal_read'
        base = dict(source='%s.%s' % (self._label, name), actor='macro_program', skill_id=self._skill, parent_call_seq=self._parent, arguments=_safe(args))
        started = time.monotonic()
        try:
            result = function(*args, **kwargs)
        except BaseException as error:
            self.logged.append(self._log.add(kind, **base, status='ERROR', error='%s: %s' % (type(error).__name__, error),
                                             t_start_monotonic=round(started, 6), elapsed_s=round(time.monotonic() - started, 6)))
            raise
        self.logged.append(self._log.add(kind, **base, status='RETURNED', result=_safe(result),
                                         t_start_monotonic=round(started, 6), elapsed_s=round(time.monotonic() - started, 6)))
        return result


class SkillRunner:
    def __init__(self, registry, transports, log, *, limits=None, max_calls=2, max_writes=1, request_of=None):
        """transports: {'state': <movement transport>, 'inspection': <read_group transport>}, labels from the dict keys.
        Each call is a FRESH macro invocation, so the per-task write bound of the macro (one write) is enforced here ACROSS calls:
        at most `max_writes` movements per episode, and no further movement after a write whose outcome was not confirmed (no replay)."""
        self.registry, self.transports, self.log = registry, transports, log
        self.limits = limits or MacroLimits()
        self.max_calls, self.calls, self.attempts = max_calls, 0, 0     # calls = accepted calls; attempts includes refused ones
        self.request_of, self._last_request = request_of, None           # request_of(): model-request number, to allow one run_skill per response
        self.max_writes, self.writes_total, self.unconfirmed_write = max_writes, 0, False

    def tool(self):
        return StructuredTool(name='run_skill', description=DESCRIPTION, args_schema=RunSkillArgs, func=self.run)

    def run(self, skill_id):
        self.attempts += 1
        parent = self.log.add('skill_call_start', skill_id=skill_id, attempt_number=self.attempts)
        if self.calls >= self.max_calls:
            return self._refuse(parent, skill_id, 'run_skill_limit_reached', 'at most %d run_skill calls per task' % self.max_calls)
        request = self.request_of() if self.request_of else None
        if request is not None and request == self._last_request:
            return self._refuse(parent, skill_id, 'one_run_skill_per_response', 'call run_skill once per response and wait for its result')
        self._last_request = request
        self.calls += 1
        definition = self.registry._definitions.get(skill_id)
        if definition is None:
            return self._refuse(parent, skill_id, 'skill_not_authorized', 'unknown skill id')
        if isinstance(definition, StateSkill):
            if self.unconfirmed_write:
                return self._refuse(parent, skill_id, 'no_replay_after_unconfirmed_write', 'a previous movement was not confirmed; it must not be replayed')
            if self.writes_total >= self.max_writes:
                return self._refuse(parent, skill_id, 'episode_write_budget_exhausted', '%d movement(s) per task' % self.max_writes)
        proxies = {kind: LoggedTransport(t, kind, self.log, skill_id, parent) for kind, t in self.transports.items()}
        try:
            invocation = self.registry.open(proxies, limits=self.limits, mode='macro', allowed_skills=[skill_id])
        except (ValueError, TypeError) as error:
            return self._refuse(parent, skill_id, 'skill_open_rejected', str(error))
        outcome, reason, text = 'COMPLETED', None, None
        try:
            result = invocation.execute(skill_id)
            text = result if isinstance(result, str) else json.dumps(result, sort_keys=True, default=str)
        except Exception as error:          # ControlledStop, uncertain write (TimeoutError), ...: never retried, returned as text
            outcome, reason = 'STOPPED', '%s: %s' % (type(error).__name__, error)
            text = json.dumps({'stopped': True, 'reason': reason, 'requirement': 'Do not replay a dispatched command; report what was observed or stop.'})
        snapshot = invocation.snapshot()
        self._link_operations(proxies, snapshot)
        writes = sum(1 for p in proxies.values() for s in p.logged if self._event(s)['kind'] == 'internal_write')
        kind = 'state' if isinstance(definition, StateSkill) else 'inspection'
        self.writes_total += writes
        if writes and snapshot.get('workflow_state') != 'AWAITING_REPORT':
            self.unconfirmed_write = True
        self.log.add('skill_call_end', skill_id=skill_id, parent_call_seq=parent, outcome=outcome, reason=reason, skill_kind=kind,
                     workflow_state=snapshot.get('workflow_state'), writes_dispatched=writes,
                     write_skipped=self._skip_reason(kind, writes, snapshot), snapshot_operations=_safe(snapshot['operations']))
        return text

    def _refuse(self, parent, skill_id, code, reason):
        self.log.add('skill_call_end', skill_id=skill_id, parent_call_seq=parent, outcome='REJECTED_BEFORE_ANY_IO', code=code, reason=reason, writes_dispatched=0)
        return json.dumps({'rejected': True, 'code': code, 'reason': reason, 'available_skills': sorted(self.registry.catalogue())})

    def _event(self, seq):
        return next(e for e in self.log.events if e['seq'] == seq)

    def _link_operations(self, proxies, snapshot):
        """Attach the macro's own operation ids to the proxy events, in order (one transport call = one native operation)."""
        seqs = sorted(s for p in proxies.values() for s in p.logged)
        operations = snapshot['operations']
        for seq, op in zip(seqs, operations):
            event = self._event(seq)
            event.update(operation_id=op['operation_id'], operation_kind=op['kind'], macro_actor=op['actor'], operation_status=op['status'])
            # the trace row of the event is already written: the link is its own row (linked_seq -> operation id)
            self.log.add('operation_link', linked_seq=seq, operation_id=op['operation_id'], operation_kind=op['kind'], macro_actor=op['actor'], operation_status=op['status'])
        if len(seqs) != len(operations):
            self.log.add('operation_link_mismatch', transport_calls=len(seqs), macro_operations=len(operations))

    @staticmethod
    def _skip_reason(kind, writes, snapshot):
        if kind != 'state' or writes:
            return None
        if snapshot.get('workflow_state') == 'AWAITING_REPORT':
            return 'already_within_tolerance (fresh read at target; macro skips the write)'
        return 'no_write_%s' % snapshot.get('workflow_state')


def ur5e_registry():
    """The frozen M4 UR5e catalogue (rosa-evaluation experiments/macro_m4/design.py registry()), rebuilt here without importing rosa-evaluation."""
    from rosa_reliability.capability_demo import CHECKS
    from rosa_reliability.ros_arm import HOME_POSE
    return (CapabilityRegistry()
            .register(StateSkill(skill_id='ur5e.home', targets={'/ur5e': dict(HOME_POSE)}))
            .register(StateSkill(skill_id='ur5e.stage_left', targets={'/ur5e': {**HOME_POSE, 'shoulder_pan_joint': -.14, 'wrist_3_joint': .20}}))
            .register(StateSkill(skill_id='ur5e.park_right', targets={'/ur5e': {**HOME_POSE, 'shoulder_pan_joint': .16, 'wrist_3_joint': -.12}}))
            .register(InspectionSkill(skill_id='ur5e.inspect_readiness', subject='/ur5e_readiness', checks=CHECKS)))
