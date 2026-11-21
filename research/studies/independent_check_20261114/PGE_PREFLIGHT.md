# PGE_PREFLIGHT: per-request tool lists in our ROSA setup (read-only; no code changed, no model run)

Date: 2026-11-14. Method: read the ROSA source, the installed LangChain, `langchain-ollama` and `ollama` Python packages, our Stage 1 to 3b harness and saved traces; one web search for the Ollama API docs. Paths under `.venv/` are the installed packages (`.venv/lib/python3.12/site-packages/`, called `SP/` below). No Ollama server code is available locally and no request was sent to the server, so Question 2 is answered from documentation and client code, not from a live test.

## 1. Smallest change that lets the tool list differ per model request

**How the list is fixed today.**
- ROSA builds its tool registry once in `__init__` (`src/rosa/rosa.py:107-109`) and builds the agent once (`rosa.py:111`, `_get_agent` at `rosa.py:269-276`) by calling LangChain's `create_tool_calling_agent(llm=..., tools=self.__tools.get_tools(), prompt=...)`.
- That function calls `llm_with_tools = llm.bind_tools(tools)` **once** and returns the chain `assign(agent_scratchpad) | prompt | llm_with_tools | ToolsAgentOutputParser()` (`SP/langchain/agents/tool_calling_agent/base.py:97-110`, bind at line 102). So the list a model sees is baked into the chain when the agent is built.
- `AgentExecutor` holds the same list separately (`rosa.py:258-261`; field `tools` at `SP/langchain/agents/agent.py:1042`). The executor uses it only to **run** the tool the model asks for: it builds `name_to_tool_map = {tool.name: tool for tool in self.tools}` at `agent.py:1610` (`_call`), `1664` (`_acall`) and `1736` (`_get_tool_return`), and `_perform_agent_action` looks the called name up there (`agent.py:1413-1423`; an unknown name returns an `InvalidTool` observation). The model-facing list and the executable list are therefore independent.
- Each loop step calls `self._action_agent.plan(intermediate_steps, ...)` (`agent.py:1334-1356`), which runs the chain above with the episode's steps so far.

**Smallest change (harness only, no edit to `src/rosa/`).** Our own model wrapper already receives the tool schemas on every request:
- `TracedModel.bind_tools` only stores the schemas as call kwargs (`research/studies/headroom_diagnostic_20261112/run_stage1.py:94-95`), and `TracedModel._generate` pops them on **every** request (`run_stage1.py:98`: `schemas = kwargs.pop('tools', [])`) and re-binds them on the real model for that request (`run_stage1.py:102`: `self.holder['model'].bind_tools(schemas).invoke(messages, ...)`).
- So the one-line hook is between lines 98 and 102: `schemas = select_tools(schemas, messages)`, where `messages` is the full message list for this request (system prompts, task, earlier model turns and tool results) and `select_tools` returns a subset of the 47 schemas. The saved trace already records the schemas actually sent per request (`model_start.schemas`), so per-request lists would be logged without further work.
- Keep the executor's `tools` list full. A tool hidden from the model still exists for execution; a call to a hidden tool would still run, not return `InvalidTool`, which is the behaviour to decide on (log it, or reject it).

**Alternative, still without editing `src/rosa/`.** Subclass `ROSA` and override `_get_agent` (`rosa.py:269-276`) to return `RunnablePassthrough.assign(agent_scratchpad=...) | prompt | RunnableLambda(lambda x: llm.bind_tools(select_tools(x["intermediate_steps"], x["input"]))) | ToolsAgentOutputParser()` in place of the fixed `llm.bind_tools(tools)` (`base.py:102-110`). This is the same override pattern the harness already uses for prompts (`A1ROSA._get_prompts`, `run_stage3b.py:54-61`). It sees `intermediate_steps` and the task text but not the system messages; the `TracedModel` hook sees everything and is smaller.

**What does not need to change:** the `AgentExecutor` loop (`agent.py:1314-1356`), the tool functions, the prompts, and the scorer.

## 2. Does Ollama (0.40.16, HTTP API) accept a different `tools` list on each `/api/chat` request?

**Answer from documentation and client code: yes, by design; not tested live.**
- The `/api/chat` reference lists `tools` as an **optional request field** next to the required `model` and `messages`, described as the function tools the model may call during the chat ([docs.ollama.com/api/chat](https://docs.ollama.com/api/chat); tool-calling guide: [docs.ollama.com/capabilities/tool-calling](https://docs.ollama.com/capabilities/tool-calling)). Chat requests are stateless HTTP calls: the client resends the whole `messages` history each time, and there is no server-side session that stores a tool list (the API has no field that refers to a previous tool list).
- Client code does the same: the Python client builds a fresh `ChatRequest(model=..., messages=..., tools=...)` for every `chat()` call (`SP/ollama/_client.py:394-398`), and `langchain-ollama` copies `kwargs["tools"]` into the request parameters for each call (`SP/langchain_ollama/chat_models.py:687-688`). Our harness already exercises this path once per request (`run_stage1.py:102`).
- Server-side prompt rendering also takes the tools per request: the model templates and renderers receive `.Tools` for the request being rendered. For example the `gpt-oss:20b` template read with `/api/show` has `{{- if .Tools -}}` blocks, and `qwen3.5:9b`, `mimo-v2.6:9b` and `lfm3:1.7b` use built-in renderers (`RENDERER qwen3.5`, `mimo-v2.6`, `lfm3`; `MODEL_FAMILIES.md`).

**Not established (stated so nobody assumes it):**
- Our logs never changed the list within an episode: all 259 `model_start` events of the Stage 3b run carry the identical 47-name list (checked in the traces). So "a different list per request works end to end in our harness" has not been run.
- The docs I found are the current docs, not versioned to 0.40.16; I did not confirm a version-specific difference.
- Two untested risks when the list changes mid-episode: (a) the tools are rendered into the prompt, so changing them changes the prompt text and the server may have to recompute the cached prefix (likely slower; not measured); (b) if an earlier assistant turn in the history called a tool that is no longer in the list, some templates or models may handle that history badly. Neither was tested; a 1-episode live check would settle (b) and give a latency number for (a), but that is a model run and was out of scope here.

## 3. How many tools does ROSA expose to the model in our Stage 3 harness?

**47.** Source: the schemas in the first `model_start` of a Stage 3b trace (`research/_artifacts/runs/headroom_diagnostic_20261112/stage3b_20261113T155721Z/00-v3-openai-r0/trace.jsonl`, line 3), identical in all 259 model requests of that run; consistent with the offline registry check in `run_stage3b.py:208-209` (`tools: 47`) and with the registry build (`src/rosa/tools/__init__.py:67-91`: `calculation`, `log`, `system`, `ros2` for ROS 2, no blacklist in our harness). Counts by module (`@tool` definitions): `calculation.py` 30, `log.py` 1, `system.py` 3, `ros2.py` 13.

Names (in the order sent):
- **Calculation (30):** acos, add, add_all, asin, atan, atan2, calculate_line_angle_and_distance, cosh, cosine, count_lines, count_list, count_words, degrees_to_radians, distance_between_points, divide, exponentiate, mean, median, mode, modulo, multiply, multiply_all, radians_to_degrees, sine, sinh, sqrt, subtract, tangent, tanh, variance.
- **Log (1):** read_log.
- **System (3):** set_debugging, set_verbosity, wait.
- **ROS 2 (13):** ros2_doctor, ros2_node_info, ros2_node_list, ros2_param_get, ros2_param_list, ros2_param_set, ros2_service_call, ros2_service_info, ros2_service_list, ros2_topic_echo, ros2_topic_info, ros2_topic_list, roslog_list.

Note for any per-request selection: all 47 are exposed even though our observation-only guard (`vendor/menu_run_study.py:111-129`) only allows `ros2 node list/info`, `topic list/info/echo`, `param list/get`, `service list/type`; `ros2_param_set`, `ros2_service_call` and `ros2_doctor` are visible to the model but their native commands are rejected (the guard's `guard_rejection`). A model has tried one of them: Qwen under A2 called `ros2_service_call` (rejected by the tool schema before execution; `REPORT_STAGE3D.md`).

## Limits
Read-only inspection of source and saved traces; one web search for documentation; no request was sent to Ollama; Question 2 rests on documentation and client code; the 47-tool list is the one in our harness for ROS 2 with no blacklist and may differ in other ROSA configurations.
