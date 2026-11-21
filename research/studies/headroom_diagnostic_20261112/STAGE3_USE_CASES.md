# Stage 3, step 0: what ROSA requests look like (offline, read-only grounding)

Written 2026-11-13. **Honest limit first:** nothing in this repository or the research folder records real operator requests, logs or usage statistics. `README.md`, `docs/START_HERE.md` and the installed `jpl-rosa` metadata (which only carries this fork's README) contain no example requests, and the research literature notes (`research/literature/`) are about tool-use methods, not ROSA deployments. No usage numbers are given here, and none should be inferred from this page. Each item below is marked **[file]** (taken from a cited file) or **[inference]** (mine).

## What the files do show
- ROSA is "an AI agent that can use ROS tools to answer questions about robotics systems", with responses "grounded in real-time information" [file: `src/rosa/prompts.py`, first system message].
- The stock prompt names two request classes: questions about what is running ("check what is available ... rosnode_list, rostopic_list", "TOOL USAGE REQUIREMENT") and action requests ("move, draw, control", "WORKFLOW FOR ACTION REQUESTS") [file: `src/rosa/prompts.py`]. Stage 3 is read-only, so action requests are out of scope.
- `RobotSystemPrompts` carries fields such as `about_your_operators`, `about_your_environment` and `mission_and_objectives`, so deployments describe their operators and robot to the agent [file: `src/rosa/prompts.py`, `RobotSystemPrompts`].
- The ROS 2 read tools are node/topic/service listing, `ros2_node_info` (publishers, subscribers, service servers and clients of a node), `ros2_topic_info` (type, publisher and subscriber endpoints), `ros2_service_info` (type), `ros2_param_list`, `ros2_param_get` (one node and one parameter per call), `ros2_topic_echo` [file: `src/rosa/tools/ros2.py`]. Writes (`ros2_param_set`, `ros2_service_call`) exist and are excluded here.
- The research record lists the task families earlier studies used on ROSA: interface discovery and wiring of a turtle simulator and a demo application, clock (`use_sim_time`) configuration, service and parameter reads, ROS 2 action feedback, and a Nav2 map-server/lifecycle application where errors were wrong semantic source, observed versus configured values, and omitted requested fields [file: `research/ROSA_RESEARCH_CONTEXT.md` §5, stages C to E]. Those are research tasks the team wrote, not operator logs.

## Request kinds that follow from the tools (inference)
All inferred from what the read tools can answer; none is a measured frequency.
1. **Trace a data flow upstream.** "Which node feeds the topic my node consumes, and what does it consume?" Each hop needs the previous answer: topic to publisher (`topic_info`), publisher to its inputs (`node_info`), input topic to its publisher. Typical depth 2 to 4 [inference].
2. **Follow configuration that points at other entities.** A parameter names a peer node or a frame; the next read uses that value [inference; the dependency-through-values pattern also appears as the earlier "structured dependency" experiments, `ROSA_RESEARCH_CONTEXT.md` §5 stage H].
3. **Inspect a node's neighbourhood.** "What does this node consume, who publishes each input, and how are those nodes configured?" A short chain followed by several independent reads [inference].
4. **Find who provides a service, then check it.** There is no direct service-to-node tool, so the provider is found by listing nodes and reading each node's service servers, then reading a parameter of the provider [inference from the tool set].
5. Plain discovery and one-hop reads ("what is running", "type of this topic"): the six baseline tasks already cover these [file: `STUDY_INDEX.md`, headroom rows; inference for how typical they are].

## Dependency depth and read-only status (inference)
Kinds 1 to 4 need 2 to 4 sequential observation stages, with independent reads inside a stage. All use only the read tools. I found no file stating how many dependent steps real requests need, so the depth range 2 to 4 is a design choice for this study, not a measured property of ROSA use.

## Choice for Step 1
Four templates, one per kind 1 to 4: upstream data-flow trace; parameter-pointer chain; node neighbourhood with a fan-out; service-provider route. Depths 2, 3 and 4 each, on a custom fixture with generated names.
