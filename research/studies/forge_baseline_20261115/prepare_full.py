"""Freeze the exact pilot C1 cells and reconstruct transport without inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_smoke as smoke
import httpx
from langchain_core.messages import messages_from_dict


def prepare():
    pilot = smoke.PILOT
    excluded = {rid for group in json.loads((pilot / "INFRA_EXCLUDED.json").read_text()).values()
                for rid in group.get("run_ids", [])}
    original = [json.loads(line) for line in (pilot / "RESULTS_LOG.jsonl").read_text().splitlines()]
    rows = [row for row in original if row["arm"] in ("A1", "C1") and row["run_id"] not in excluded]
    assert len(rows) == 160
    models = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b"]
    plans, transport = {}, {}
    for model in models:
        selected = [row for row in rows if row["model"] == model and row["arm"] == "C1"]
        assert len(selected) == 20
        for env in ("stage3", "e1h"):
            cells = [dict(env=env, task=row["task"], model=model, seed=row["seed"], temperature=row["temperature"])
                     for row in selected if row["env"] == env]
            assert len(cells) == (8 if env == "stage3" else 12)
            assert len({(c["task"], c["seed"]) for c in cells}) == len(cells)
            random.Random(f"20261115-forge-matched-{model}-{env}").shuffle(cells)
            plans[f"{model}-{env}"] = cells
        first = selected[0]
        events = [json.loads(line) for line in Path(first["trace_path"]).read_text().splitlines()]
        start = next(e for e in events if e["kind"] == "model_start")
        messages = messages_from_dict([dict(type=m["type"], data=m) for m in start["messages"]])
        chat = smoke.pilot.build_chat_model(model, first["temperature"], first["seed"])
        captured = []

        def capture(request):
            captured.append(json.loads(request.content))
            return httpx.Response(200, json={"model": model, "message": {"role": "assistant", "content": "offline"},
                                             "done": True, "prompt_eval_count": 1, "eval_count": 1})

        # Run the installed SDK's exact request serialization against a mock
        # transport. No HTTP request reaches Ollama and no model is invoked.
        chat._client._client.close()
        chat._client._client = httpx.Client(base_url=smoke.pilot.S1.OLLAMA, transport=httpx.MockTransport(capture))
        params = chat._chat_params(messages, tools=start["schemas"], **start["options"])
        list(chat._client.chat(**params))
        chat._client._client.close()
        assert len(captured) == 1
        body = captured[0]
        assert body["think"] is False
        assert body["options"] == dict(smoke.OPTIONS, seed=first["seed"])
        transport[model] = dict(think=body["think"], reconstructed_sdk_request=body,
                                historical_trace_path=first["trace_path"], historical_trace_hash=first["trace_hash"],
                                evidence="logical historical trace plus current unchanged pilot factory and installed SDK; not a historical raw HTTP capture")
    for row in rows:
        path = Path(row["trace_path"])
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["trace_hash"]
    (HERE / "FULL_PLAN.json").write_text(json.dumps(dict(models=models, sessions=plans, total_cells=80), indent=2) + "\n")
    (HERE / "PILOT_TRANSPORT.json").write_text(json.dumps(transport, indent=2) + "\n")
    (HERE / "FULL_COMPARATORS_SOURCE.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps({model: transport[model]["think"] for model in models}))
    print("Frozen 80 Forge cells; verified 160 original A1/C1 trace hashes.")


if __name__ == "__main__":
    prepare()
