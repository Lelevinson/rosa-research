#!/usr/bin/env python3
"""Read-only retrospective audit of archived ROSA model events.

No ROSA/ROS execution, no inference, no semantic source maps, no model prompt mutation.
Requires only Python standard library and the original baseline-diagnostic ZIP.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import zipfile


def audit(path: Path) -> dict:
    sums = Counter()
    categories = defaultdict(lambda: Counter())
    arms = defaultdict(lambda: Counter())
    contexts = defaultdict(lambda: Counter())
    model_turns = 0
    episodes = 0
    for_member = []
    with zipfile.ZipFile(path) as zipf:
        assert zipf.testzip() is None, "ZIP CRC failure"
        for member in zipf.namelist():
            if not (member.startswith("evidence/primary-v1/") and member.endswith("/trace.jsonl")):
                continue
            if "/oracle/" in member:
                continue
            events = [json.loads(line) for line in zipf.read(member).decode("utf-8").splitlines() if line.strip()]
            eps = next((e for e in events if e.get("kind") == "episode_start"), None)
            if not eps:
                continue
            episodes += 1
            arm = eps.get("arm", "unknown")
            last_end = -1
            ep_turns = 0
            for i, e in enumerate(events):
                if e.get("kind") != "model_end":
                    continue
                m = e.get("message") or {}
                meta = m.get("response_metadata") or {}
                usage = m.get("usage_metadata") or {}
                content = m.get("content") or ""
                if not isinstance(content, str):
                    # In this corpus all assistant texts are plain strings.
                    raise AssertionError(f"non-string model content: {member}")
                is_tool = bool(m.get("tool_calls"))
                action_type = "tool" if is_tool else "final"
                class_type = "tool_plus_text" if is_tool and content.strip() else (
                    "tool_only" if is_tool else "final")
                intervening = events[last_end+1:i]
                if last_end < 0:
                    previous_state = "initial"
                elif any(x.get("kind") == "ros_end" and x.get("returncode", 0) != 0 for x in intervening):
                    previous_state = "after_native_error"
                elif any(x.get("kind") == "tool_end" for x in intervening):
                    previous_state = "after_tool_result"
                else:
                    previous_state = "other"
                metrics = {
                    "output_tokens": (meta.get("eval_count") or 0),
                    "input_tokens": (meta.get("prompt_eval_count") or 0),
                    "decode_ns": (meta.get("eval_duration") or 0),
                    "prefill_ns": (meta.get("prompt_eval_duration") or 0),
                    "total_ns": (meta.get("total_duration") or 0),
                    "load_ns": (meta.get("load_duration") or 0),
                    "visible_words": len(content.split()),
                    "turns": 1,
                }
                for k, val in metrics.items():
                    sums[k] += val
                    categories[class_type][k] += val
                    arms[arm][k] += val
                    contexts[previous_state][k] += val
                contexts[previous_state][action_type + "_turns"] += 1
                arms[arm][action_type + "_turns"] += 1
                categories[class_type]["tool_calls"] += len(m.get("tool_calls") or [])
                if "prompt_eval_cached_count" in meta:
                    sums["reported_cached_count"] += meta["prompt_eval_cached_count"]
                    sums["reported_cached_events"] += 1
                model_turns += 1
                ep_turns += 1
                last_end = i
            assert ep_turns > 0, member
            for_member.append({"member": member, "turns": ep_turns, "arm": arm})
    assert episodes == 36 and model_turns == 227, (episodes, model_turns)
    assert sums["input_tokens"] == 1585055 and sums["output_tokens"] == 27132, "Mismatch against original report"
    assert categories["tool_plus_text"]["turns"] == 174
    assert categories["tool_only"]["turns"] == 17
    assert categories["final"]["turns"] == 36
    assert sum(c["turns"] for c in contexts.values()) == 227
    result = {
        "source_archive": str(path),
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "episodes": episodes,
        "model_turns": model_turns,
        "units": "duration in nanoseconds; tokens from Ollama model_end metadata; words are whitespace-separated surface text, not tokens",
        "totals": dict(sums),
        "by_model_response_type": {k: dict(v) for k,v in sorted(categories.items())},
        "by_baseline_arm": {k: dict(v) for k,v in sorted(arms.items())},
        "by_predecision_tool_status": {k: dict(v) for k,v in sorted(contexts.items())},
        "trace_index": for_member,
        "limitations": [
            "Baseline prompts contain the historical sequential-tool-call instruction; no fully activated deconflicted strong control was observed here.",
            "Tool-call narration is not proved dispensable merely because content co-occurs with structured tool calls.",
            "No model inference, semantic correctness scoring, or before/after intervention was executed by this script.",
            "Provider token counts are not independently tokenized; prompt_eval_cached_count is absent in these events.",
            "No hidden task contracts or semantic adapters are used by this analysis.",
        ],
    }
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument("archive", type=Path)
    p.add_argument("--out", type=Path)
    a=p.parse_args()
    data=audit(a.archive)
    if a.out:
        a.out.write_text(json.dumps(data, indent=2) + "\n")
    s=data["totals"]
    for name in ("decode_ns", "prefill_ns", "load_ns", "total_ns"):
        print(f"{name}: {s[name]/1e9:.3f} seconds")
    print("model_turns", data["model_turns"], "episodes", data["episodes"])
    print("response-types",{k:(v['turns'],v['output_tokens'],v['visible_words']) for k,v in data['by_model_response_type'].items()})
    print("previous-state",{k:(v['turns'],v.get('tool_turns',0),v.get('final_turns',0)) for k,v in data['by_predecision_tool_status'].items()})

if __name__ == "__main__":
    main()
