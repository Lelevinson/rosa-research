"""CPU-only: effect of the compaction rule on the real ROSA tool schemas (characters; no model). uv run python measure_rule.py"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "small_model_harness_20261115")); sys.path.insert(0, str(HERE.parent / "headroom_diagnostic_20261112"))
import harness
import compaction
from langchain_core.utils.function_calling import convert_to_openai_tool
from rosa.tools import ROSATools
tools = {t.name: convert_to_openai_tool(t) for t in ROSATools(2, blacklist=[]).get_tools()}
for name, (description, model) in harness.EXTRA_TOOLS.items():
    pass
rows, tot_a, tot_b = [], 0, 0
for name in harness.DOMAIN_TOOLS:
    s = tools[name]; c = compaction.compact_schema(s)
    assert c["function"]["name"] == s["function"]["name"] and c["function"]["parameters"] == s["function"]["parameters"]
    a, b = len(s["function"]["description"]), len(c["function"]["description"])
    tot_a += a; tot_b += b
    rows.append((name, a, b))
    print(f"--- {name}: {a} -> {b}\n{c['function']['description']}")
print("domain tools total description chars", tot_a, "->", tot_b, f"({1 - tot_b / tot_a:.0%} fewer)")
