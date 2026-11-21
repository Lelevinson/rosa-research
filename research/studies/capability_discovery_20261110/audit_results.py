"""Replay saved observations without executing tools, ROS, or models."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from discovery import Discovery
import fixtures_development as dev
import fixtures_extension as ext


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    result = json.loads((args.directory / "results.json").read_text())
    records = [json.loads(line) for line in (args.directory / "observations.jsonl").read_text().splitlines()]
    for name, expected in result["sources"].items():
        path = Path(__file__).resolve().parent / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
    def replay(engine, phase):
        for r in records:
            if r["phase"] == phase:
                accepted = engine.observe(r["tool"], r["arguments"], r["output"],
                                          snapshot=r["snapshot"], successful=True)
                assert accepted == r["accepted"], (phase, r["tool"])
    def check(engine, key):
        section = result["real_rosa"]["calculation"] if key == "real_calculation" else result[key]
        assert engine.discover() == section["decisions"], key
        labels = {(r["left"], r["right"]): r["overlapping_information"] for r in section["oracle_labels"]}
        assert len(labels) == len(engine.registry) * (len(engine.registry) - 1) // 2
        # Reconstruct confusion counts independently of the study scorer.
        for field, metric in [("candidate", "proposals"), ("empirically_supported", "empirical_support")]:
            counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
            for pair in engine.discover():
                actual = labels[pair["left"], pair["right"]]
                predicted = pair[field]
                counts[("t" if actual == predicted else "f") + ("p" if predicted else "n")] += 1
                assert not pair["replacement_allowed"]
            assert all(section[metric][k] == v for k, v in counts.items()), (key, metric)
        print(f"PASS {key}: {len(section['decisions'])} pair decisions and confusion counts")
    d = Discovery()
    d.refresh(dev.TOOLS)
    check(d, "development_metadata_only")
    replay(d, "development")
    check(d, "development_observed")
    e = Discovery()
    e.refresh(ext.TOOLS)
    check(e, "extension_metadata_only")
    replay(e, "extension_initial")
    check(e, "extension_initial")
    replay(e, "extension_counterexample")
    check(e, "extension_after_counterexample")
    d.refresh(dev.TOOLS + ext.TOOLS)
    replay(d, "new_registration")
    check(d, "new_registration")
    from rosa.tools import calculation
    c = Discovery()
    c.refresh([calculation.add_all, calculation.multiply_all, calculation.mean,
               calculation.median, calculation.variance])
    replay(c, "real_pure_calculation")
    check(c, "real_calculation")
    assert result["preservation"]["before"] == result["preservation"]["after"]
    assert len(records) == 120
    assert result["costs"]["llm_calls"] == 0
    assert result["real_rosa"]["native_ros_dispatches"] == 0
    print("PASS 120 raw validation observations; preservation; zero LLM/native ROS dispatches")
    print("Replay executed zero fixture/calculation tool calls.")


if __name__ == "__main__":
    main()
