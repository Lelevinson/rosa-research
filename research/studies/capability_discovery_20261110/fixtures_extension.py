"""Unseen-at-engine-freeze synthetic extension; no production validity claim.

Different semantics with identical outputs are deliberately included. Their truth
labels belong only to evaluation and cannot be inferred by inspecting values.
"""
from langchain_core.tools import tool


@tool
def inventory(asset: int) -> dict:
    """Read asset processor load and nested queue depth."""
    return {"load": float(3 * asset + 1), "queue": {"depth": asset + 2}}


@tool
def processor(asset: int) -> dict:
    """Read processor load of an asset."""
    return {"load": float(3 * asset + 1)}


@tool
def queue_depth(asset: int) -> dict:
    """Read nested queue depth of an asset."""
    return {"queue": {"depth": asset + 2}}


@tool
def correlated_foreign(asset: int) -> dict:
    """Read load of a distinct device indexed by asset."""
    # Correlated outputs, but distinct device and quantity; never substitutable.
    return {"load": float(3 * asset + 1)}


@tool
def delayed_drift(asset: int) -> dict:
    """Read reference device load indexed by asset."""
    return {"load": float(3 * asset + 1 if asset < 8 else 7 * asset + 2)}


@tool
def utilization_alias(asset: int) -> dict:
    """Read processor utilization of an asset."""
    return {"utilization": float(3 * asset + 1)}


@tool
def resource_load(resource: int) -> dict:
    """Read processor load indexed by resource."""
    return {"load": float(3 * resource + 1)}


@tool
def fractional_load(asset: int) -> dict:
    """Read processor load expressed as a fraction rather than percentage points."""
    return {"load": float(3 * asset + 1) / 100}


@tool
def opaque(asset: int) -> str:
    """Read processor load of an asset."""
    return f"load={3 * asset + 1}"


@tool
def vague(asset: int) -> dict:
    """Read the current value."""
    return {"humidity": float(asset + 17)}


TOOLS = [inventory, processor, queue_depth, correlated_foreign, delayed_drift,
         utilization_alias, resource_load, fractional_load, opaque, vague]
