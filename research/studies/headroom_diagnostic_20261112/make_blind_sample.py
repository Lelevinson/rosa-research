"""Build the blind relabeling input: a seeded random 20% of labeled requests, WITHOUT labels.

Usage: python3 make_blind_sample.py <repo_root> <out_dir>
Writes input.json (what the independent labeler sees) and key.json (episode#index list, no labels).
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from label_requests import load_all  # noqa: E402

SEED = 20261112


def excerpt(text, n=220):
    return (text or "").replace("\\n", " ").replace("\n", " ")[:n]


def main():
    repo_root, out_dir = Path(sys.argv[1]).resolve(), Path(sys.argv[2])
    items = []
    for info, requests, task_text in load_all(repo_root):
        for request in requests[1:]:
            history = []
            for earlier in requests[: request["request_index"] - 1]:
                history.append({
                    "request": earlier["request_index"],
                    "model_comment": excerpt(earlier["content"], 160),
                    "calls": [{"tool": c["name"], "args": str(c["args"])[:160], "result_excerpt": excerpt(c["result"])}
                              for c in earlier["calls"]],
                })
            items.append({
                "id": f"{info['episode']}#{request['request_index']}",
                "task_text": task_text,
                "history": history,
                "request_to_label": {
                    "model_comment": excerpt(request["content"], 300),
                    "calls": [{"tool": c["name"], "args": str(c["args"])[:200], "result_excerpt": excerpt(c["result"])}
                              for c in request["calls"]],
                },
            })
    random.Random(SEED).shuffle(items)
    sample = items[: round(0.2 * len(items))]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "input.json").write_text(json.dumps(sample, indent=1))
    print(len(items), "labeled requests;", len(sample), "in blind sample")


if __name__ == "__main__":
    main()
