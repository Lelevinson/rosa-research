"""Pure synthetic read-only tools. Labels are in the evaluator, never the engine."""
from langchain_core.tools import tool


@tool
def bundle(item: int) -> dict:
    """Read temperature, pressure and nested count for an item."""
    return {"temperature": float(2 * item + 3), "pressure": float(100 + item),
            "nested": {"count": item + 7}}


@tool
def temperature(item: int) -> dict:
    """Read temperature for an item."""
    return {"temperature": float(2 * item + 3)}


@tool
def nested_count(item: int) -> dict:
    """Read the nested item count."""
    return {"nested": {"count": item + 7}}


@tool
def unrelated(item: int) -> dict:
    """Read temperature from a separate reference source."""
    return {"temperature": float(90 - item)}


@tool
def ambiguous(item: int) -> dict:
    """Read the current value."""
    return {"voltage": float(item + 11)}


@tool
def renamed_field(item: int) -> dict:
    """Read thermal measurement for an item."""
    return {"heat": float(2 * item + 3)}


@tool
def renamed_argument(index: int) -> dict:
    """Read temperature for an item selected by index."""
    return {"temperature": float(2 * index + 3)}


@tool
def integer_temperature(item: int) -> dict:
    """Read temperature for an item as an integer."""
    return {"temperature": 2 * item + 3}


@tool
def constant_a(item: int) -> dict:
    """Read a fixed calibration temperature."""
    return {"temperature": 7.0}


@tool
def constant_b(item: int) -> dict:
    """Read a fixed calibration temperature."""
    return {"temperature": 7.0}


TOOLS = [bundle, temperature, nested_count, unrelated, ambiguous, renamed_field,
         renamed_argument, integer_temperature, constant_a, constant_b]
