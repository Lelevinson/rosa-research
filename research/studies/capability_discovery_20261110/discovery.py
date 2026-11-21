"""Passive capability hypotheses. No executor, semantic adapters, or equivalence oracle.

Only the collector may authorize an invocation. Evidence here concerns JSON fields
in supplied snapshots, not unobserved inputs or the meaning of coincident values.
"""
from __future__ import annotations

import copy
import hashlib
import inspect
import itertools
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Callable


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def require_json(value: Any) -> None:
    if value is None or type(value) in {str, bool, int}:
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for child in value:
            require_json(child)
        return
    if type(value) is dict and all(type(k) is str for k in value):
        for child in value.values():
            require_json(child)
        return
    raise ValueError("not finite parsed JSON")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def structural(schema: Any) -> Any:
    """Ignore documentation only; preserve argument names, defaults and constraints."""
    if isinstance(schema, dict):
        result = {}
        for key, value in schema.items():
            if key in {"title", "description"}:
                continue
            if key in {"properties", "$defs", "definitions", "patternProperties", "dependentSchemas"}:
                result[key] = {name: structural(child) for name, child in value.items()}
            elif key in {"items", "additionalProperties", "not", "if", "then", "else",
                         "contains", "propertyNames", "unevaluatedProperties"}:
                result[key] = structural(value)
            elif key in {"allOf", "anyOf", "oneOf", "prefixItems"}:
                result[key] = [structural(child) for child in value]
            else:
                # enum/const/default objects are DATA, not schemas.
                result[key] = copy.deepcopy(value)
        return result
    if isinstance(schema, list):
        return [structural(v) for v in schema]
    return schema


def fields(value: Any, path: tuple[str, ...] = ()) -> dict[tuple[str, ...], Any]:
    # Null/empty data, root text and acknowledgements do not describe capabilities.
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("non-string JSON key")
            if key.lower() in {"error", "errors", "success", "status", "message"}:
                continue
            result.update(fields(item, path + (key,)))
        return result
    if value is None or isinstance(value, bool):
        return {}
    if isinstance(value, str):
        return {}
    if isinstance(value, list) and not value:
        return {}
    if isinstance(value, list) and contains_text(value):
        return {}
    return {path: value}


def contains_text(value: Any) -> bool:
    """A string payload might be opaque CLI text; never guess a parser for it."""
    if isinstance(value, str):
        return True
    if isinstance(value, list):
        return any(contains_text(v) for v in value)
    if isinstance(value, dict):
        return any(contains_text(v) for v in value.values())
    return False


def json_type(value: Any) -> Any:
    # Python equality would conflate True, 1 and 1.0. Keep exact JSON/Python types.
    if isinstance(value, list):
        return ("array", tuple(json_type(v) for v in value))
    if isinstance(value, dict):
        return ("object", tuple((k, json_type(v)) for k, v in sorted(value.items())))
    return type(value).__name__


def has_error(value: Any) -> bool:
    if isinstance(value, dict):
        if any(k.lower() in {"error", "errors"} for k in value):
            return True
        if value.get("success") is False:
            return True
        return any(has_error(v) for v in value.values())
    if isinstance(value, list):
        return any(has_error(v) for v in value)
    return False


def declared_paths(schema: dict, path: tuple[str, ...] = ()) -> set:
    # Resolve no references/unions speculatively; unknown schema means unknown.
    if schema.get("type") == "object":
        result = set()
        for key, child in schema.get("properties", {}).items():
            result.update(declared_paths(child, path + (key,)))
        return result
    if schema.get("type") in {"number", "integer", "string", "array"}:
        return {path}
    return set()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9]+", text.lower())) - {
        "the", "of", "and", "to", "for", "from", "returns", "return", "get", "a",
        "tool", "information", "this", "input", "on", "in", "with", "is"}


@dataclass
class Descriptor:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    fingerprint: str


@dataclass
class Observation:
    tool: str
    snapshot: str
    arguments: dict
    values: dict


class Discovery:
    """Schema/path proposer and bounded empirical validator, opt-in and passive."""

    def __init__(self, min_contexts: int = 3, min_values: int = 2):
        if min_contexts < 3 or min_values < 2:
            raise ValueError("insufficient evidence thresholds")
        self.min_contexts = min_contexts
        self.min_values = min_values
        self.registry: dict[str, Descriptor] = {}
        self._tools: dict[str, Any] = {}
        self._observations: dict[tuple[str, str, str], Observation] = {}
        self.rejections: list[dict] = []
        self.revisions: list[dict] = []
        self._invalid_tools: set[str] = set()

    @staticmethod
    def describe(tool: Any) -> Descriptor:
        ins = tool.get_input_schema().model_json_schema()
        outs = tool.get_output_schema().model_json_schema()
        func = getattr(tool, "func", None)
        try:
            source = inspect.getsource(func) if func else ""
        except (OSError, TypeError):
            source = ""
        # Callable identity supplements source for same-source new registrations.
        # It is process-local, and does not pretend to detect mutable external state.
        fingerprint = digest([tool.name, tool.description, ins, outs, source,
                              id(func), repr(getattr(func, "__defaults__", None))])
        return Descriptor(tool.name, tool.description, ins, outs, fingerprint)

    def refresh(self, tools: list[Any]) -> None:
        new = {}
        handles = {}
        for tool in tools:
            desc = self.describe(tool)
            if desc.name in new:
                raise ValueError(f"duplicate tool name: {desc.name}")
            new[desc.name] = desc
            handles[desc.name] = tool
        changed = {name for name, desc in self.registry.items()
                   if name not in new or desc.fingerprint != new[name].fingerprint}
        if changed:
            self._observations = {key: obs for key, obs in self._observations.items()
                                  if obs.tool not in changed}
            self.revisions.append({"invalidated": sorted(changed)})
            self._invalid_tools -= changed
        self.registry = new
        self._tools = handles

    def observe(self, tool: str, arguments: dict, output: Any, *, snapshot: str,
                successful: bool) -> bool:
        """Ingest a collector's completed read-only call; never executes the tool.

        Snapshot IDs must come from a collector able to assert a common frozen
        state, not merely time proximity. Raw outputs must be parsed JSON values.
        Failure/transport success are necessary checks, not semantic or safety proof.
        """
        try:
            if tool not in self.registry or not snapshot or not successful:
                raise ValueError("unknown tool, missing snapshot or unsuccessful call")
            if not isinstance(arguments, dict):
                raise ValueError("arguments must be explicit objects")
            schema = self.registry[tool].input_schema
            if set(arguments) - set(schema.get("properties", {})):
                raise ValueError("unknown arguments")
            self._tools[tool].get_input_schema().model_validate(arguments)
            require_json(arguments)
            require_json(output)
            canonical(arguments)
            canonical(output)
            if has_error(output):
                raise ValueError("error envelope")
            extracted = fields(output)
            if not extracted:
                raise ValueError("no structured information fields")
            key = (tool, snapshot, canonical(arguments))
            if key in self._observations:
                if canonical(self._observations[key].values) != canonical(
                        {canonical(list(k)): v for k, v in extracted.items()}):
                    raise ValueError("snapshot conflict; collector must use a new snapshot")
                return True
            # String-encode paths to make saved observations unambiguous JSON.
            values = {canonical(list(k)): copy.deepcopy(v) for k, v in extracted.items()}
            self._observations[key] = Observation(tool, snapshot,
                                                 copy.deepcopy(arguments), values)
            return True
        except (TypeError, ValueError, OverflowError) as exc:
            # A conflicting snapshot removes its previous evidence as well.
            if isinstance(arguments, dict) and tool in self.registry:
                try:
                    self._observations.pop((tool, snapshot, canonical(arguments)), None)
                except (TypeError, ValueError):
                    pass
            self.rejections.append({"tool": tool, "snapshot": snapshot,
                                    "reason": str(exc)})
            self._invalid_tools.add(tool)
            return False

    def pair(self, left: str, right: str) -> dict:
        a, b = self.registry[left], self.registry[right]
        ao = {key[1:]: obs for key, obs in self._observations.items() if obs.tool == left}
        bo = {key[1:]: obs for key, obs in self._observations.items() if obs.tool == right}
        ap = {p for obs in ao.values() for p in obs.values}
        bp = {p for obs in bo.values() for p in obs.values}
        declared = declared_paths(a.output_schema) & declared_paths(b.output_schema)
        common = ap & bp
        ta, tb = tokens(a.name + " " + a.description), tokens(b.name + " " + b.description)
        score = len(ta & tb) / max(1, len(ta | tb))
        reasons = []
        if common:
            reasons.append("observed_shared_paths")
        if declared:
            reasons.append("declared_shared_paths")
        if score >= 0.2:
            reasons.append("metadata_similarity")
        compatible = structural(a.input_schema) == structural(b.input_schema)
        matched = sorted(set(ao) & set(bo)) if compatible else []
        decisions = []
        for path in sorted(common):
            contexts, distinct, witnesses, mismatches = set(), set(), [], []
            missing = 0
            for key in matched:
                av, bv = ao[key].values, bo[key].values
                if path not in av or path not in bv:
                    missing += 1
                    continue
                if json_type(av[path]) != json_type(bv[path]) or canonical(av[path]) != canonical(bv[path]):
                    mismatches.append({"snapshot": key[0], "arguments": ao[key].arguments,
                                       "left": av[path], "right": bv[path]})
                else:
                    contexts.add(key[1])  # Repeated snapshots of one input add no diversity.
                    distinct.add(canonical(av[path]))
                    witnesses.append({"snapshot": key[0], "arguments": ao[key].arguments})
            if mismatches:
                status = "contradicted"
            elif {left, right} & self._invalid_tools:
                status = "uncertain_invalid_evidence"
            elif missing:
                status = "uncertain_missing_field"
            elif len(contexts) >= self.min_contexts and len(distinct) >= self.min_values:
                status = "empirically_supported"
            else:
                status = "uncertain"
            decisions.append({"path": json.loads(path), "status": status,
                              "contexts": len(contexts), "distinct_values": len(distinct),
                              "missing": missing, "witnesses": witnesses,
                              "mismatches": mismatches})
        supported = any(d["status"] == "empirically_supported" for d in decisions)
        return {"left": left, "right": right, "candidate": bool(reasons),
                "proposal_reasons": reasons, "metadata_score": score,
                "arguments_compatible": compatible, "matched_observations": len(matched),
                "fields": decisions, "empirically_supported": supported,
                "semantic_equivalence": "unestablished", "replacement_allowed": False,
                "fallback": True}

    def discover(self) -> list[dict]:
        return [self.pair(a, b) for a, b in itertools.combinations(sorted(self.registry), 2)]

    def inventory(self) -> list[dict]:
        return [vars(d) for d in self.registry.values()]

    @staticmethod
    def ordinary_call(name: str, arguments: dict, dispatch: Callable) -> Any:
        """Explicit fallback seam: forward the original call without rewriting it.

        The provided dispatcher retains authorization/safety responsibility. It is
        not invoked by discovery; the caller must explicitly choose to execute.
        """
        return dispatch(name, copy.deepcopy(arguments))
