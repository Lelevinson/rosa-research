"""Explicit sensitivity to FQN assembly, separate from the literal recount."""
import json
import re
from pathlib import Path

OUT = Path(__file__).parent
ROOT = OUT.parents[2]
rows = json.loads((OUT / "episode_recount.json").read_text())
sensitivity = []
for row in rows:
    names = set()
    for line in (ROOT / row["trace"]).read_text().splitlines():
        event = json.loads(line)
        if event["kind"] != "tool_end":
            continue
        # Traverse actual output strings, not model content or tool arguments.
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for item in value.values():
                    yield from strings(item)
            elif isinstance(value, list):
                for item in value:
                    yield from strings(item)
        for text in strings(event["output"]):
            for name, namespace in re.findall(r"Node name: ([^\n]+)\nNode namespace: ([^\n]+)", text):
                names.add(namespace.rstrip("/") + "/" + name)
    supported = all(s["holds"] or (s["requirement"][0] == "text" and s["requirement"][1] in names)
                    for s in row["support"])
    sensitivity.append({"episode": row["episode"], "arm": row["arm"], "model": row["model"],
                        "depth": row["depth"], "supported_complete": row["exact"] and supported,
                        "names_assembled": sorted(names)})
with (OUT / "endpoint_assembly_sensitivity_v2.json").open("x") as handle:
    json.dump(sensitivity, handle, indent=2)
for arm, model in [("A1", "ollama"), ("A1", "openai"), ("A2", "ollama")]:
    supported = [r for r, s in zip(rows, sensitivity)
                 if (r["arm"], r["model"]) == (arm, model) and s["supported_complete"]]
    print(arm, model, "supported", len(supported), "excess/floor",
          sum(r["excess"] for r in supported), sum(r["floor"] for r in supported),
          "duplicate requests", sum(r["duplicate_requests"] for r in supported))
