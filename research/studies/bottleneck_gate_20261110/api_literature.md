# Installed API and primary-literature audit — 2026-11-10

This is source inspection and literature checking, with no ROS initialization, graph observer, model inference, robot operation, or timing experiment. It establishes semantics and counterexamples; it establishes neither historical prevalence nor measured overhead. The mission's dynamic-graph recommendation remains a hypothesis.

## Installed source, scope, and identity

`dpkg-query -W` reports rclpy `7.1.12-1noble.20260902.053513`, rclcpp `28.1.22-1noble.20260902.055335`, rcl `9.2.11-1noble.20260902.044558`, rmw `7.3.3-1noble.20260612.050218`, rcl_interfaces `2.0.4-1noble.20260902.021729`.

The installed Python API root below is `/opt/ros/jazzy/lib/python3.12/site-packages/`.

| Verified source | Finding and limit |
|---|---|
| `rclpy/node.py:2077–2119` | `get_node_names()` drops namespaces. `get_node_names_and_namespaces()` retains pairs; fully qualified names join them. These contain no process-incarnation token. |
| `rclpy/node.py:1971–1991` | By-node publisher queries require separate node name and namespace. A missing node can raise `NodeNameNonExistentError`; an unexpected failure is distinct. |
| `rclpy/node.py:2221–2249`; `rclpy/topic_endpoint_info.py:35–54` | Publisher information contains endpoint GID, name, namespace, type, QoS. The GID identifies an endpoint, not a universal node-process identity or parameter-version certificate. Relative/private topic queries expand in the observer's namespace/name; queried names are not remapped. |
| `/opt/ros/jazzy/include/rmw/rmw/rmw.h:215–244,2703–2730` | Graph guard conditions cover discovered topology/matching changes, as seen by the associated node. Queries return nodes discovered so far. A graph query is synchronous/nonblocking at RMW level, may allocate/lock, and does not create a global freshness barrier. |
| `/opt/ros/jazzy/include/rclcpp/rclcpp/node_interfaces/node_graph_interface.hpp:332–386` | Installed C++ exposes `get_graph_guard_condition`, `get_graph_event`, `wait_for_graph_change`. No public methods of the last two names occur in installed rclpy Python source. Do not attribute C++ event APIs to rclpy Node. |
| `/opt/ros/jazzy/include/rclcpp/rclcpp/event.hpp:30–74` | Event state is an atomic Boolean with set/check/check-and-clear. It is not an ordered per-entity change log. Multiple changes can coalesce. |
| `rclpy/node.py:920–959`; `rclpy/parameter_client.py:339–355` | Successful parameter updates publish a separate `/parameter_events` message containing node FQN, timestamp, and new/changed/deleted parameter lists. Parameter values can change without a graph-topology change. The client subscription is to the absolute event topic; filtering by fully qualified node/parameter is necessary. |
| `/opt/ros/jazzy/share/rcl_interfaces/msg/ParameterEvent.msg` | Message has no sequence number, process incarnation, or proof that the receiver has consumed every earlier event. Timestamp is not itself a distributed synchronization certificate. |
| `/opt/ros/jazzy/include/rmw/rmw/qos_profiles.h:77–87` | Default parameter events use KEEP_LAST depth 1000, RELIABLE, VOLATILE. Reliability does not supply historical replay to late joiners; finite queues and executor processing also matter. Do not silently assume TRANSIENT_LOCAL. |
| `rclpy/parameter_client.py:160–175` | `get_parameters(names)` dispatches a real asynchronous service request, not a local proof of value stability. A ready service does not prove a requested parameter exists or the same process still serves the name. |
| `rclpy/parameter_service.py:80–90`; `/opt/ros/jazzy/share/rcl_interfaces/srv/GetParameters.srv` | Interface promises result values in request order/length and NOT_SET for unset values. This installed Python callback instead clears all values and returns an empty list on an undeclared/uninitialized name. This is a source-level provider behavior, not malformed serialization; an empty response to a nonempty request cannot certify coverage. |
| `ros2param/verb/get.py:46–68`; `ros2param/api/__init__.py:72–85`; `ros2cli/node/strategy.py:24–67` | Scalar CLI get already performs `wait_for_node` before reading, then waits for parameter services. NodeStrategy can use a daemon or DirectNode. An additional framework membership preflight can repeat existing CLI work and still race. Distinguish these observation scopes. |
| Repository `src/rosa/tools/ros2.py:25–48,174–214,273–287` | Current stock ROSA wraps CLI subprocesses; node/topic list inputs can batch identities but the loops execute CLI commands sequentially. `execute_ros_command` returns exception text for failure and does not preserve a structured stderr/exit/timeout envelope. Topic/node info output is raw text. Transport, parse failure, valid emptiness, and semantic sufficiency need separate ledger fields. No runtime change made. |

The [upstream Jazzy NodeGraph source](https://raw.githubusercontent.com/ros2/rclcpp/jazzy/rclcpp/src/rclcpp/node_interfaces/node_graph.cpp) independently shows `notify_graph_change()` sets observer events and `get_graph_event()` registers a new event and starts the graph listener on first use. This branch is supporting source, not asserted byte-identical to the installed binary. Official docs.ros.org pages were blocked by access protection during this audit; installed headers and source supply the version-specific evidence.

Consequences (inferences from these contracts): event silence cannot prove current topology, unchanged parameter values, or process continuity. A fresh membership check reduces some known-stale proposals but cannot close the check/use race. An endpoint GID may expose endpoint replacement; it does not validate a separate parameter service or all of a node's identity. No inspected API supplies the requested cheap, universally trustworthy freshness certificate. Discovery lag and callback delay remain unmeasured; this audit does not assert observed notification loss or numerical lag.

## Ordinary controls and accounting

| Control | Information/cost required | What it cannot prove |
|---|---|---|
| Dispatch directly; one bounded retry on a typed failure | Requested read, plus recovery only after failure | Avoids no first stale call; often cheapest if failures are rare |
| Always refresh graph | One graph observation per guarded read, setup/daemon costs included | Value freshness, process continuity, atomicity with dispatch |
| Name-membership check | Existing discovered name set or another graph query; preserve namespace | Presence in observer cache is insufficient for read success |
| TTL | Timestamp and chosen lifetime | TTL is a heuristic, not factual freshness |
| Ordinary graph-event invalidation | Persistent listener, setup, queue/callback work, refresh after change | No-event freshness, parameter stability, event identity journal |
| Ordinary parameter-event invalidation | Subscription, explicit FQN filtering, value-event processing, bounded refresh | Complete history for late joiners or unobserved updates |

For a policy to beat bounded retry on expected native latency, saved failed-read/recovery work must exceed guard/setup/false-refusal work on the same distribution. In a simple accounting model this requires `p(stale) × avoidable_failure_cost > guard_cost + false_refusal_cost`; this is a screening inequality, not an implemented rule or fitted estimate. Saved native milliseconds do not establish a saved model turn. Always charge listener startup and full result/token envelopes to every arm with equal capabilities.

## Primary-paper checks

All five supplied identifiers resolved to matching primary records. SCA and When2Tool full HTML and clarification/Proof-of-Use PDFs were inspected. Gecko's PMLR PDF endpoint returned an unsupported content type, so its author arXiv v2 full text was used instead. No numerical literature result below is treated as a ROSA result.

| Primary source | Checked mechanism | Consequence for this hypothesis |
|---|---|---|
| [Lee & Barke, SCA, arXiv:2610.25552v1, §§3.1–3.3 and Limitations](https://arxiv.org/html/2610.25552v1) | Mines documentation constraints, refines against training histories, checks first-order call/argument/result history using SMT. Warning can follow returned results; pre-dispatch MaxSMT repair changes arguments only if the satisfying replacement is unique. It explicitly cannot detect unobserved environmental state or omitted necessary calls. | Argument provenance, history-qualified constraints, state checking, unique correction, and conservative fallback are already present. External ROS observations might add information, but freshness qualification must outperform ordinary invalidation/retry. The limitation is an observability boundary, not evidence of an unoccupied algorithm category. False warnings can cause valid calls to be retried. |
| [Zhang et al., Gecko, arXiv:2602.19218v2, §§3–4](https://arxiv.org/html/2602.19218v2), [ICML/PMLR record](https://proceedings.mlr.press/v306/zhang26cv.html) | Combines schema validation, helper-model semantic validation, simulated responses/state estimation, and objective feedback. GATS refines plans in simulation before the real-tool agent runs. | Generic validity checking and pre-execution refinement are prior art. Simulated state is not an independent observation of a live ROS graph. It incurs model work outside a framework-only guard. |
| [Suri et al., Structured Uncertainty guided Clarification, §§3–4](https://aclanthology.org/2026.findings-acl.2028.pdf) | Models beliefs over structured tool/parameter completions; values questions through EVPI and aspect costs. | Clarifying user intent differs from observing whether an already discovered ROS entity remains live. Generic uncertainty/cost balancing is not a novelty claim. |
| [Sun et al., When2Tool / Probe&Prefill, arXiv:2605.09252v3, §§2–5](https://arxiv.org/html/2605.09252v3) | Benchmarks necessity; trains a linear probe over pre-generation hidden states and steers with a prefilled sentence. Version 3 dated 2026-11-04 was current in this check. | This relies on hidden-state access/training and permits an accuracy tradeoff in aggregate results. A live robot-state answer cannot be replaced by model prior knowledge merely because a call seems unnecessary. It does not establish a ROS temporal certificate. |
| [Ma et al., Proof-of-Use, §2](https://aclanthology.org/2026.emnlp-main.1664.pdf) | Retrieval responses get shared evidence IDs; reasoning declares usefulness/citations; RL combines citation validity, answer–support alignment and reward mixing. | IDs/lineage alone are not a method contribution. This is retrieval/RL evidence dependence, distinct from framework-only ROS temporal state observation; claimed novelty must be narrower than generic evidence grounding. |
| [Kamath et al., Agent-C, arXiv:2512.23738](https://arxiv.org/abs/2512.23738) | Temporal ordering constraints are translated into first-order logic and enforced during tool-call generation. Abstract/record checked, not a full implementation review. | Merely calling a guard temporal does not distinguish it. Action-sequence policy conformance is different from physical environment freshness. |

## Gate implication and public-API witnesses

There is no source-grounded basis to promote dynamic read admission by itself. Its unmeasured prerequisites are stale-call prevalence, a useful observable warning before dispatch, and net benefit over the controls above. A source-level possible failure is not demonstrated demand.

Three real API cases that a separately authorized diagnostic should distinguish are: (1) discovered `/demo/talker` disappears before `get_publisher_names_and_types_by_node('talker','/demo')`; (2) a node returns under the same FQN while its endpoint GID changes, defeating name-only continuity; (3) an existing node changes a parameter while topology remains unchanged, separating graph events from parameter events. A nonempty `get_parameters` request returning `[]` supplies an additional typed-response case. These are proposed fixture cases, not newly executed observations or an algorithm decision rule.

## Installed-source hashes

SHA-256, read from current files:

```text
8b7fe0ea64e0de12cc1d5d01ebf56c202fa6e153251eb71dfff93e35eb5b3c80  /opt/ros/jazzy/lib/python3.12/site-packages/rclpy/node.py
31daa88e9477e61c507c6ba93fa7319d56580637010c946f6d4a5576e0123ff9  /opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_client.py
f7546866ac5e9443b5524f1ec0e63eeb8bdca1041e7392d2390d5f5b68396aaa  /opt/ros/jazzy/lib/python3.12/site-packages/rclpy/parameter_service.py
b1162b828ffe357295157a8f4262856dbb90bf3557652961c21bf0776022f0ae  /opt/ros/jazzy/include/rclcpp/rclcpp/node_interfaces/node_graph_interface.hpp
bbbc2aaa89f57151f2f9cd0e4a5913c101331d02c28495ef8f10c7cadbfe6e17  /opt/ros/jazzy/include/rclcpp/rclcpp/event.hpp
0502801c68adbd61bc884aafea5c5bbfa4deb326aacb4d0fdbab3a32aab3539c  /opt/ros/jazzy/include/rmw/rmw/qos_profiles.h
9fbdba3127f095e1b14057c07d4c4acb3df4226d9bfebacbfb9123fc7088a3d2  /opt/ros/jazzy/include/rmw/rmw/rmw.h
99f239f007b55c675d4a21fb654a690f30d52395da48cf18c038384bbe857a29  /opt/ros/jazzy/share/rcl_interfaces/msg/ParameterEvent.msg
3ae49531812d8813350fad5261905a88939f8352f8a08fd238dcae19a08e59f7  /opt/ros/jazzy/share/rcl_interfaces/srv/GetParameters.srv
```
