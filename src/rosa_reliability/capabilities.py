"""Additive v0.2 capability contracts: bounded state change and read-only checks.

M1 APIs and historical sources stay unchanged. Inspection never calls write,
and each source acquisition reserves a native operation before I/O.
"""
from copy import deepcopy
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .bounded_macro import StateSkill, MacroLimits, MacroInvocation, _RegisteredSession
from .reference import make_reference_tools
from .terminal import coordination_span

__version__ = '0.2.0'


class InspectionSkill(BaseModel):
    """Check named Boolean conditions; SUCCESS means all are freshly true.

    FAILURE means observed unready, UNKNOWN means an observation is unavailable.
    These distinguish inspection outcome from successful acquisition itself.
    """
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    skill_id: str = Field(min_length=1, max_length=128)
    subject: str
    checks: dict[str, list[str]]

    @model_validator(mode='after')
    def validate_contract(self):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', self.skill_id):
            raise ValueError('invalid_skill_identifier')
        if not _RegisteredSession.canonical(self.subject) or not self.checks:
            raise ValueError('canonical_inspection_subject_and_checks_required')
        fields = []
        for source, names in self.checks.items():
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', source) or not names:
                raise ValueError('named_nonempty_inspection_sources_required')
            if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', name) for name in names):
                raise ValueError('invalid_inspection_check_name')
            fields.extend(names)
        if len(set(fields)) != len(fields):
            raise ValueError('inspection_check_names_must_be_unique')
        return self


class CapabilityRegistry:
    """Explicit definitions and transport boundary; one selected skill per task."""

    def __init__(self):
        self._definitions = {}

    def register(self, skill: StateSkill | InspectionSkill):
        if not isinstance(skill, (StateSkill, InspectionSkill)):
            raise TypeError('validated_StateSkill_or_InspectionSkill_required')
        stored = type(skill).model_validate(deepcopy(skill.model_dump()))
        if stored.skill_id in self._definitions:
            raise ValueError('duplicate_skill_identifier')
        self._definitions[stored.skill_id] = stored
        return self

    def catalogue(self):
        return {name: ({'kind': 'state_change', 'targets': deepcopy(skill.targets), 'max_writes': 1}
            if isinstance(skill, StateSkill) else {'kind': 'read_only_inspection', 'subject': skill.subject,
                'required_checks': deepcopy(skill.checks), 'max_writes': 0,
                'success_means': 'every required readiness check freshly observed true',
                'evidence_encoding': 'true=1.0, false=0.0, unavailable=null'})
            for name, skill in self._definitions.items()}

    def open(self, transports, *, limits=None, mode: Literal['macro', 'primitives'] = 'macro',
             allowed_skills=None, tracer=None):
        if mode not in ('macro', 'primitives'):
            raise ValueError('mode_must_be_macro_or_primitives')
        limits = MacroLimits() if limits is None else limits
        if not isinstance(limits, MacroLimits): raise TypeError('limits_requires_MacroLimits')
        limits = MacroLimits.model_validate(limits.model_dump())
        definitions = deepcopy(self._definitions)
        if allowed_skills is not None:
            if isinstance(allowed_skills, (str, bytes)):
                raise ValueError('allowed_skills_requires_identifiers')
            names = tuple(allowed_skills)
            if not names or len(set(names)) != len(names) or any(n not in definitions for n in names):
                raise ValueError('allowed_skills_requires_registered_subset')
            definitions = {name: definitions[name] for name in names}
        if not definitions: raise ValueError('nonempty_capability_registry_required')
        for skill in definitions.values():
            kind = 'state' if isinstance(skill, StateSkill) else 'inspection'
            transport = transports.get(kind)
            methods = ('read', 'write') if kind == 'state' else ('read_group',)
            if not all(callable(getattr(transport, name, None)) for name in methods):
                raise TypeError('missing_bounded_transport_for_' + kind)
        return CapabilityInvocation(definitions, dict(transports), limits, mode, tracer)


class _CapabilitySession(_RegisteredSession):
    def __init__(self, definitions, transports, **kwargs):
        self.definitions, self.transports = definitions, transports
        compiled = {name: deepcopy(skill.targets) if isinstance(skill, StateSkill) else
            {skill.subject: {field: 1.0 for fields in skill.checks.values() for field in fields}}
            for name, skill in definitions.items()}
        # No I/O at construction. select() binds the selected authorized transport.
        super().__init__(next(iter(transports.values())), compiled, **kwargs)

    def select(self, skill_id):
        if self.selected_skill is None and skill_id in self.definitions:
            kind = 'state' if isinstance(self.definitions[skill_id], StateSkill) else 'inspection'
            self.transport = self.transports[kind]
        return super().select(skill_id)

    def _inspection(self):
        skill = self.definitions.get(self.selected_skill)
        return skill if isinstance(skill, InspectionSkill) else None

    def write(self, node_name, values):
        if self._inspection() is not None:
            return self.feedback('read_only_skill_forbids_write', {'max_writes': 0})
        return super().write(node_name, values)

    def read(self, nodes, actor='model'):
        skill = self._inspection()
        if skill is None: return super().read(nodes, actor)
        if nodes != [skill.subject]:
            return self.feedback('invalid_node_scope', {'allowed_nodes': [skill.subject]})
        actor = self._actor if actor == 'model' else actor
        values, evidence, checks = {}, [], {}
        for source, names in skill.checks.items():
            unavailable = None
            try:
                observed, operation = self.native('read_' + source, actor,
                    lambda: self.transport.read_group(source, list(names)))
            except TimeoutError:
                observed = {name: None for name in names}
                operation = self.budget.events[-1]['operation_id']
                unavailable = 'observation_timeout'
            if (not isinstance(observed, dict) or set(observed) != set(names) or
                    any(value is not None and type(value) is not bool for value in observed.values())):
                raise RuntimeError('invalid_boolean_inspection_observation')
            checks[source] = deepcopy(observed)
            values.update({name: None if value is None else float(value) for name, value in observed.items()})
            evidence.append({'node': skill.subject, 'fields': list(names), 'source': source,
                'operation_id': operation, 'after_write': self.last_write, 'actor': actor,
                'unavailable': unavailable})
        identifier = f'obs-{self._observation_namespace}-{len(self.observations) + 1}'
        observation = {'observed_values': {skill.subject: values}, 'evidence': evidence,
            'observation_id': identifier, 'readiness_checks': checks,
            'capability_kind': 'read_only_inspection', 'evidence_encoding': 'boolean_as_0_1_or_null'}
        self.observations.append(deepcopy(observation))
        return observation

    def run_workflow(self):
        if self._inspection() is None: return super().run_workflow()
        with self.owner('program'), coordination_span(self, 'macro.read_only_inspection'):
            try:
                verified = self.tools_by_name['verify_outcome'].invoke({})
                if not isinstance(verified, dict): return self.escalate('inspection_rejected', verified)
                if verified['goal_reached'] is not True:
                    reason = 'inspection_unknown' if verified['goal_reached'] is None else 'inspection_conditions_not_met'
                    return self.escalate(reason, verified)
                self.workflow_state = 'AWAITING_REPORT'
                return {'selected_skill': self.selected_skill, 'capability_kind': 'read_only_inspection',
                    'workflow_state': self.workflow_state, 'verification': verified, 'next_step_owner': 'model'}
            except BaseException:
                self.transition('STOPPED', 'inspection_exception_no_write_or_replay')
                raise


class CapabilityInvocation(MacroInvocation):
    def __init__(self, definitions, transports, limits, mode, tracer):
        self.limits, self.mode = limits, mode
        registry = CapabilityRegistry()
        for skill in definitions.values(): registry.register(skill)
        self._catalogue = registry.catalogue()
        self.session = _CapabilitySession(definitions, transports, program_managed=mode == 'macro',
            structured_feedback=True, operation_limit=limits.native_operations,
            tool_limit=limits.tool_attempts, validation_limit=limits.corrections,
            seconds=limits.seconds, tolerance=limits.tolerance, tracer=tracer)
        self._tools = make_reference_tools(self.session)

    def snapshot(self):
        snapshot = super().snapshot()
        return {**snapshot, 'module_version': __version__, 'base_macro_version': snapshot['module_version'],
            'selected_max_writes': 0 if self.session._inspection() is not None else 1}


__all__ = ['InspectionSkill', 'CapabilityRegistry', 'CapabilityInvocation']
