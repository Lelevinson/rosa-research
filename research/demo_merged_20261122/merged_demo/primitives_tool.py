"""ARM (b) primitive action tools: read_pose, read_readiness, write_pose, verify_pose (separate tools, the MODEL sequences read -> write -> verify).
LABEL: merged-method demo, arm (b) "M + primitives", demonstration only, not evaluated, not for the paper. NEW FILE (ours); arm (a) files are unchanged.

SAME GUARDS AS THE MACRO (arm a), only the sequencing differs:
- same registered targets (the macro's own ur5e_registry; a movement can only go to a registered skill's fixed target, no free joint values);
- the transport's own validate_write bound (the real ArmTransport check) before any write;
- at most ONE write per task (max_writes), no write after a write whose outcome was not confirmed (no replay);
- same budgets as MacroLimits: 10 native operations, 16 tool attempts, 180 s, tolerance 0.025 rad;
- one primitive call per model response (arm (a): one run_skill per response);
- a write needs a successful read_pose first in the same task (the macro always reads before writing). The macro also SKIPS a write when the fresh read is
  already at the target; here the model decides, and a write at target is allowed.
Logging follows arm (a): every transport call is an `internal_read` / `internal_write` event with source, sequence numbers, times, arguments and result, with actor
`model_primitive` (arm a: `macro_program`)."""
import json
import time

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, StrictStr

from rosa_reliability.bounded_macro import MacroLimits, StateSkill
from rosa_reliability.ros_arm import JOINTS

from .skill_tool import CATALOGUE_TEXT, _safe

READ_POSE_DESCRIPTION = 'Read the current six joint positions of /ur5e now (a fresh sample). Read-only.'
READ_READINESS_DESCRIPTION = 'Read the arm readiness checks now: controllers active and joint sample fresh. Read-only.'
WRITE_POSE_DESCRIPTION = ('Move the arm to the fixed target of one registered movement skill, by exact skill id. Needs a successful read_pose first. '
                          'Allowed once per task; it does not verify the result.' + CATALOGUE_TEXT)
VERIFY_POSE_DESCRIPTION = 'Read the six joint positions again and compare them with the registered target of the given movement skill (tolerance 0.025 rad). Read-only.'
TOOL_NAMES = ('read_pose', 'read_readiness', 'write_pose', 'verify_pose')


class NoArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')


class SkillArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    skill_id: StrictStr


class PrimitiveTransport:
    """Transparent proxy that logs read / read_group / write calls (actor model_primitive)."""
    WRAPPED = ('read', 'write', 'read_group')

    def __init__(self, inner, label, log, tool, parent_seq):
        self._inner, self._label, self._log, self._tool, self._parent = inner, label, log, tool, parent_seq
        self.logged = []

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name in self.WRAPPED and callable(attr):
            return lambda *args, **kwargs: self._call(name, attr, args, kwargs)
        return attr

    def _call(self, name, function, args, kwargs):
        kind = 'internal_write' if name == 'write' else 'internal_read'
        base = dict(source='%s.%s' % (self._label, name), actor='model_primitive', tool=self._tool, parent_call_seq=self._parent, arguments=_safe(args))
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


class PrimitiveRunner:
    def __init__(self, registry, transports, log, *, limits=None, max_writes=1, request_of=None):
        """transports: {'state': movement transport, 'inspection': read_group transport} (same as SkillRunner)."""
        self.registry, self.transports, self.log = registry, transports, log
        self.limits = limits or MacroLimits()
        self.max_writes, self.writes_total, self.unconfirmed_write = max_writes, 0, False
        self.request_of, self._last_request = request_of, None
        self.calls = self.attempts = self.operations = 0     # calls = accepted primitive calls; attempts includes refused ones
        self.max_calls = self.limits.tool_attempts
        self.read_done, self._started = False, None

    # ------------------------------------------------------------ tools
    def tools(self):
        def make(name, desc, schema, func):
            return StructuredTool(name=name, description=desc, args_schema=schema, func=func)
        return [make('read_pose', READ_POSE_DESCRIPTION, NoArgs, self.read_pose), make('read_readiness', READ_READINESS_DESCRIPTION, NoArgs, self.read_readiness),
                make('write_pose', WRITE_POSE_DESCRIPTION, SkillArgs, self.write_pose), make('verify_pose', VERIFY_POSE_DESCRIPTION, SkillArgs, self.verify_pose)]

    # ------------------------------------------------------------ guards
    def _enter(self, tool, **fields):
        self.attempts += 1
        if self._started is None:
            self._started = time.monotonic()
        parent = self.log.add('primitive_call_start', tool=tool, attempt_number=self.attempts, **fields)
        if self.attempts > self.limits.tool_attempts:
            return parent, self._refuse(parent, tool, 'tool_attempt_budget_exhausted', 'at most %d tool attempts per task' % self.limits.tool_attempts)
        if time.monotonic() - self._started > self.limits.seconds:
            return parent, self._refuse(parent, tool, 'time_budget_exhausted', 'at most %d s per task' % self.limits.seconds)
        request = self.request_of() if self.request_of else None
        if request is not None and request == self._last_request:
            return parent, self._refuse(parent, tool, 'one_primitive_per_response', 'call one primitive tool per response and wait for its result')
        self._last_request = request
        return parent, None

    def _refuse(self, parent, tool, code, reason):
        self.log.add('primitive_call_end', tool=tool, parent_call_seq=parent, outcome='REJECTED_BEFORE_ANY_IO', code=code, reason=reason, writes_dispatched=0)
        return json.dumps({'rejected': True, 'code': code, 'reason': reason, 'available_skills': sorted(self.registry.catalogue())})

    def _definition(self, skill_id, parent, tool):
        definition = self.registry._definitions.get(skill_id)
        if definition is None:
            return None, self._refuse(parent, tool, 'skill_not_authorized', 'unknown skill id; use one of the registered ids exactly')
        if not isinstance(definition, StateSkill):
            return None, self._refuse(parent, tool, 'not_a_movement_skill', '%s is not a movement skill; use read_readiness for inspection' % skill_id)
        return definition, None

    def _ops(self, n):
        if self.operations + n > self.limits.native_operations:
            return False
        self.operations += n
        return True

    def _budget(self, parent, tool):
        return self._refuse(parent, tool, 'native_operation_budget_exhausted', 'at most %d native operations per task' % self.limits.native_operations)

    def _proxy(self, kind, tool, parent):
        return PrimitiveTransport(self.transports[kind], kind, self.log, tool, parent)

    def _end(self, parent, tool, proxy, outcome, writes, **extra):
        self.log.add('primitive_call_end', tool=tool, parent_call_seq=parent, outcome=outcome, writes_dispatched=writes, transport_calls=len(proxy.logged), **extra)

    # ------------------------------------------------------------ primitives
    def read_pose(self):
        parent, refused = self._enter('read_pose')
        if refused:
            return refused
        if not self._ops(1):
            return self._budget(parent, 'read_pose')
        self.calls += 1
        proxy = self._proxy('state', 'read_pose', parent)
        try:
            values = proxy.read('/ur5e', list(JOINTS))
        except Exception as error:
            self._end(parent, 'read_pose', proxy, 'STOPPED', 0, reason='%s: %s' % (type(error).__name__, error))
            return json.dumps({'stopped': True, 'reason': '%s: %s' % (type(error).__name__, error)})
        self.read_done = True
        self._end(parent, 'read_pose', proxy, 'COMPLETED', 0)
        return json.dumps({'observed_values': {'/ur5e': _safe(values)}}, sort_keys=True)

    def read_readiness(self):
        parent, refused = self._enter('read_readiness')
        if refused:
            return refused
        checks = self.registry._definitions['ur5e.inspect_readiness'].checks
        if not self._ops(len(checks)):
            return self._budget(parent, 'read_readiness')
        self.calls += 1
        proxy, evidence = self._proxy('inspection', 'read_readiness', parent), {}
        try:
            for source, names in checks.items():
                evidence[source] = _safe(proxy.read_group(source, list(names)))
        except Exception as error:
            self._end(parent, 'read_readiness', proxy, 'STOPPED', 0, reason='%s: %s' % (type(error).__name__, error))
            return json.dumps({'stopped': True, 'reason': '%s: %s' % (type(error).__name__, error), 'partial': evidence})
        self._end(parent, 'read_readiness', proxy, 'COMPLETED', 0)
        return json.dumps({'checks': evidence, 'all_true': all(v is True for g in evidence.values() for v in g.values())}, sort_keys=True)

    def write_pose(self, skill_id):
        parent, refused = self._enter('write_pose', skill_id=skill_id)
        if refused:
            return refused
        definition, refused = self._definition(skill_id, parent, 'write_pose')
        if refused:
            self.attempts -= 1            # same as arm (a): an unknown id does not count against the budget
            return refused
        if self.unconfirmed_write:
            return self._refuse(parent, 'write_pose', 'no_replay_after_unconfirmed_write', 'a previous movement was not confirmed; it must not be replayed')
        if self.writes_total >= self.max_writes:
            return self._refuse(parent, 'write_pose', 'episode_write_budget_exhausted', '%d movement(s) per task' % self.max_writes)
        if not self.read_done:
            return self._refuse(parent, 'write_pose', 'read_required_before_write', 'call read_pose successfully before write_pose')
        node, target = next(iter(definition.targets.items()))
        problem = self.transports['state'].validate_write(node, dict(target))
        if problem:
            return self._refuse(parent, 'write_pose', 'target_rejected', str(problem))
        if not self._ops(1):
            return self._budget(parent, 'write_pose')
        self.calls += 1
        proxy = self._proxy('state', 'write_pose', parent)
        self.writes_total += 1
        self.unconfirmed_write = True                  # confirmed only by a verify_pose that reaches the target
        try:
            proxy.write(node, dict(target))
        except Exception as error:
            self._end(parent, 'write_pose', proxy, 'STOPPED', 1, skill_id=skill_id, reason='%s: %s' % (type(error).__name__, error))
            return json.dumps({'stopped': True, 'reason': '%s: %s' % (type(error).__name__, error),
                               'requirement': 'Do not replay a dispatched command; report what was observed or stop.'})
        self._end(parent, 'write_pose', proxy, 'COMPLETED', 1, skill_id=skill_id)
        return json.dumps({'write_dispatched': True, 'skill_id': skill_id, 'verified': False, 'next': 'call verify_pose to confirm'}, sort_keys=True)

    def verify_pose(self, skill_id):
        parent, refused = self._enter('verify_pose', skill_id=skill_id)
        if refused:
            return refused
        definition, refused = self._definition(skill_id, parent, 'verify_pose')
        if refused:
            self.attempts -= 1
            return refused
        if not self._ops(1):
            return self._budget(parent, 'verify_pose')
        self.calls += 1
        proxy = self._proxy('state', 'verify_pose', parent)
        node, target = next(iter(definition.targets.items()))
        try:
            values = proxy.read(node, list(JOINTS))
        except Exception as error:
            self._end(parent, 'verify_pose', proxy, 'STOPPED', 0, skill_id=skill_id, reason='%s: %s' % (type(error).__name__, error))
            return json.dumps({'stopped': True, 'reason': '%s: %s' % (type(error).__name__, error)})
        reached = all(abs(values[k] - v) <= self.limits.tolerance for k, v in target.items())
        if reached:
            self.unconfirmed_write = False
        self._end(parent, 'verify_pose', proxy, 'COMPLETED', 0, skill_id=skill_id, goal_reached=reached)
        return json.dumps({'skill_id': skill_id, 'goal_reached': reached, 'tolerance': self.limits.tolerance, 'observed_values': {node: _safe(values)},
                           'target': {node: _safe(target)}}, sort_keys=True)
