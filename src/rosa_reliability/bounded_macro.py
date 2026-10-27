"""Public v0.1 adapter over the tested bounded state-skill policy.

No experiment imports, ROS discovery, model routing, fault labels or oracle.
Targets are authorized by the application; the caller selects and classifies.
"""
from copy import deepcopy
from contextlib import contextmanager
import math
import re
import time
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, model_validator

from .macro import MacroSession
from .reference import make_reference_tools
from .execution import ControlledStop

__version__ = '0.1.0'
Numeric = StrictInt | StrictFloat


class StateTransport(Protocol):
    """Implement bounded I/O; read returns all requested fields or raises TimeoutError."""

    def read(self, node: str, fields: list[str]) -> dict[str, float | None]: ...
    def write(self, node: str, values: dict[str, float]) -> object: ...


class StateSkill(BaseModel):
    """An application-authorized fixed numeric target, not arbitrary motion code."""

    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    skill_id: str = Field(min_length=1, max_length=128)
    targets: dict[str, dict[str, Numeric]]

    @model_validator(mode='after')
    def validate_contract(self):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*', self.skill_id):
            raise ValueError('invalid_skill_identifier')
        if len(self.targets) != 1:
            raise ValueError('v0_1_requires_one_canonical_node')
        for node, fields in self.targets.items():
            if not MacroSession.canonical(node) or not fields:
                raise ValueError('nonempty_canonical_target_required')
            if any(not name or not math.isfinite(value) for name, value in fields.items()):
                raise ValueError('finite_named_targets_required')
        return self


class MacroLimits(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True)
    native_operations: int = Field(default=10, ge=1)
    tool_attempts: int = Field(default=16, ge=1)
    corrections: int = Field(default=3, ge=0)
    seconds: float = Field(default=180.0, gt=0, allow_inf_nan=False)
    tolerance: float = Field(default=0.025, ge=0, allow_inf_nan=False)


class _RegisteredSession(MacroSession):
    """Narrow public write boundary; original frozen sessions are unchanged."""

    @contextmanager
    def tool_call(self, name, args):
        with super().tool_call(name, args) as event:
            if time.monotonic() - self.budget.started >= self.budget.seconds:
                raise ControlledStop('task_deadline_exhausted_before_tool')
            yield event

    def write(self, node_name, values):
        target = self.targets.get(node_name)
        if (target is None or set(values) != set(target) or
                any(type(v) not in (int, float) or not math.isfinite(v) or v != target[k]
                    for k, v in values.items())):
            return self.feedback('registered_target_required',
                {'requirement': 'Use every coordinate of the selected authorized target unchanged.'})
        known = next((o['observed_values'][node_name] for o in reversed(self.observations)
                      if node_name in o['observed_values']), None)
        if known is None or any(v is None for v in known.values()):
            return self.feedback('known_prerequisite_required',
                {'requirement': 'Acquire current known state before any write.'})
        return super().write(node_name, values)


class SkillRegistry:
    """Explicit allowlist, copied into each fresh invocation.

    Register only trusted definitions. Registration itself does no native I/O.
    Version 0.1 binds target parameters here; select_skill accepts only skill_id.
    """

    def __init__(self):
        self._skills = {}

    def register(self, skill: StateSkill):
        if not isinstance(skill, StateSkill):
            raise TypeError('register_requires_a_validated_StateSkill')
        # Revalidate even a model_copy/model_construct supplied by trusted code.
        stored = StateSkill.model_validate(deepcopy(skill.model_dump()))
        if stored.skill_id in self._skills:
            raise ValueError('duplicate_skill_identifier')
        self._skills[stored.skill_id] = stored
        return self

    def catalogue(self):
        return {name: deepcopy(skill.targets) for name, skill in self._skills.items()}

    def open(self, transport: StateTransport, *, limits: MacroLimits | None = None,
             mode: Literal['macro', 'primitives'] = 'macro', allowed_skills=None, tracer=None):
        if mode not in ('macro', 'primitives'):
            raise ValueError('mode_must_be_macro_or_primitives')
        if not all(callable(getattr(transport, method, None)) for method in ('read', 'write')):
            raise TypeError('transport_requires_bounded_read_and_write')
        catalogue = self.catalogue()
        if allowed_skills is not None:
            if isinstance(allowed_skills, (str, bytes)):
                raise ValueError('allowed_skills_requires_a_sequence_of_identifiers')
            names = tuple(allowed_skills)
            if not names or len(set(names)) != len(names) or any(n not in catalogue for n in names):
                raise ValueError('allowed_skills_must_be_a_nonempty_registered_subset')
            catalogue = {name: catalogue[name] for name in names}
        if not catalogue:
            raise ValueError('cannot_open_an_empty_registry')
        return MacroInvocation(transport, catalogue, MacroLimits() if limits is None else limits, mode, tracer)


class MacroInvocation:
    """One single-caller task. Construct through SkillRegistry.open().

    Tools and reports use the original tested contracts. execute() does not
    synthesize a terminal report; the caller still supplies its classification.
    The caller owns transport lifetime, external watchdogs and campaign limits.
    """

    def __init__(self, transport, catalogue, limits, mode, tracer):
        if not isinstance(limits, MacroLimits):
            raise TypeError('limits_requires_MacroLimits')
        # Revalidate bypassed model construction; copy mutable public definitions.
        limits = MacroLimits.model_validate(limits.model_dump())
        self.limits, self.mode = limits, mode
        self._catalogue = deepcopy(catalogue)
        self.session = _RegisteredSession(transport, catalogue, program_managed=mode == 'macro',
            structured_feedback=True, operation_limit=limits.native_operations,
            tool_limit=limits.tool_attempts, validation_limit=limits.corrections,
            seconds=limits.seconds, tolerance=limits.tolerance, tracer=tracer)
        self._tools = make_reference_tools(self.session)

    @property
    def tools(self):
        return list(self._tools)

    @property
    def catalogue(self):
        return deepcopy(self._catalogue)

    def execute(self, skill_id, *, config=None):
        """Select once, then execute the guarded bundle (or expose primitives)."""
        return self._tool('select_skill').invoke({'skill_id': skill_id}, config=config)

    def submit_report(self, status, observation_id, *, config=None):
        return self._tool('submit_report').invoke(
            {'status': status, 'observation_id': observation_id}, config=config)

    def _tool(self, name):
        return next(tool for tool in self._tools if tool.name == name)

    def snapshot(self):
        return {'module_version': __version__, 'mode': self.mode,
                'limits': self.limits.model_dump(), 'catalogue': self.catalogue,
                **self.session.snapshot()}


__all__ = ['StateSkill', 'StateTransport', 'SkillRegistry', 'MacroLimits', 'MacroInvocation']
