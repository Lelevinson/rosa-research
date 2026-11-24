"""Read-only: what the exam worker's model object puts into every Ollama chat request (num_ctx, num_predict, think, seed, temperature, keep_alive), per model. No network call, no model call.
The worker builds the model with run_pilot.build_chat_model(model, temperature, seed) (queue_bridge.episode), then ArmTracedModel adds only the tool list.
  uv run --no-sync python research/studies/exam_dress_rehearsal_20261122/request_params_check.py"""
import inspect, json, sys
from pathlib import Path
STUDIES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(STUDIES / "exam_arms_20261121"))
import exam_arms  # noqa: E402  (puts the pilot on sys.path)
import run_pilot  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
print(inspect.getsource(run_pilot.build_chat_model))
models = ["lfm3:1.7b", "qwen3.5:9b", "gpt-oss:20b", "bonsai-2:4b", "ministral-3:8b", "granite4.2:8b", "llama3.1:8b"]
for m in models:
    llm = run_pilot.build_chat_model(m, 0.7, 1)
    p = llm._chat_params([HumanMessage("x")])
    print(m, json.dumps({k: p[k] for k in ("think", "keep_alive") if k in p}), json.dumps(p["options"], sort_keys=True))
