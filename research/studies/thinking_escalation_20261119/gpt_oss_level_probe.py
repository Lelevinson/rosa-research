"""gpt-oss:20b thinking-level probe (owner's plan of 2026-11-19, to run in the gap after part A). DIAGNOSTIC, no bars, nothing is tuned from it.
Plan, frozen here before it runs: for each setting in [false, "low", "medium", "high"] send 8 requests (seeds 1-8) of each of 2 fixed prompts (a plain two-sentence question; a tool-use question with
one tool schema attached), temperature 0.7, num_ctx 65536, num_predict 4096 (the dev settings), via /api/chat with stream false. Settings are interleaved (seed by seed) so a drift in the machine
hits all settings alike. Record per request: eval_count (output tokens, thinking included), whether message.thinking is non-empty, its characters, content characters, tool calls, done_reason.
Report per setting: median, min, max of eval_count and thinking characters; the share of requests that returned thinking text; and where `false` sits against low / medium / high.
  python3 gpt_oss_level_probe.py"""
import json
import os
import statistics
import time
import urllib.request
from pathlib import Path

OLLAMA = os.environ.get("ROSA_OLLAMA_URL", "http://172.30.80.1:11434")  # lab container sets ROSA_OLLAMA_URL
MODEL = "gpt-oss:20b"
SETTINGS = [False, "low", "medium", "high"]
PROMPTS = {"plain": "A node list returned an empty result. What is 17*23, and what should I check next? Answer in two sentences.",
           "tool": "Which ROS 2 nodes are running? Use the tool if you need it."}
TOOL = [{"type": "function", "function": {"name": "ros2_node_list", "description": "List the running ROS 2 nodes", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}}}}]
HERE = Path(__file__).resolve().parent


def chat(setting, prompt_name, seed):
    body = dict(model=MODEL, stream=False, think=setting, messages=[{"role": "user", "content": PROMPTS[prompt_name]}], keep_alive="10m",
                options=dict(temperature=0.7, num_ctx=65536, num_predict=4096, seed=seed))
    if prompt_name == "tool":
        body["tools"] = TOOL
    started = time.time()
    request = urllib.request.Request(OLLAMA + "/api/chat", json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(request, timeout=300))
    except Exception as error:  # noqa: BLE001
        return dict(setting=str(setting), prompt=prompt_name, seed=seed, error=f"{type(error).__name__}: {error}"[:160])
    m = r["message"]
    return dict(setting=str(setting), prompt=prompt_name, seed=seed, eval_count=r.get("eval_count"), thinking_returned=bool(m.get("thinking")), thinking_chars=len(m.get("thinking") or ""),
                content_chars=len(m.get("content") or ""), tool_calls=len(m.get("tool_calls") or []), done_reason=r.get("done_reason"), seconds=round(time.time() - started, 1))


def main():
    rows = []
    for seed in range(1, 9):
        for prompt in PROMPTS:
            for setting in SETTINGS:
                rows.append(chat(setting, prompt, seed))
        print("seed", seed, "done", flush=True)
    summary = {}
    for setting in SETTINGS:
        for prompt in PROMPTS:
            sel = [r for r in rows if r["setting"] == str(setting) and r["prompt"] == prompt and "error" not in r]
            if sel:
                tokens, chars = [r["eval_count"] for r in sel], [r["thinking_chars"] for r in sel]
                summary[f"{setting}|{prompt}"] = dict(n=len(sel), eval_median=statistics.median(tokens), eval_min=min(tokens), eval_max=max(tokens), thinking_chars_median=statistics.median(chars),
                                                       share_with_thinking_text=round(sum(r["thinking_returned"] for r in sel) / len(sel), 2), errors=sum("error" in r for r in rows if r["setting"] == str(setting) and r["prompt"] == prompt))
    (HERE / "gpt_oss_level_probe.json").write_text(json.dumps(dict(rows=rows, summary=summary), indent=1))
    print(json.dumps(summary, indent=1))
    try:
        urllib.request.urlopen(urllib.request.Request(OLLAMA + "/api/generate", json.dumps(dict(model=MODEL, keep_alive=0)).encode(), {"Content-Type": "application/json"}), timeout=60).read()
    except Exception:
        pass


if __name__ == "__main__":
    main()
