"""Sweep completion: the trigger and the sweep set (build round 2, 2026-11-16). Rules: PROTOCOL.md section 4. No ROS, no model, no I/O in this file.

THE IDEA IN ONE EXAMPLE
  The model read /plant/a with ros2_node_info in request 4 and /plant/b in request 5, and both names came from the same earlier list
  (say ros2_node_list). That is the one-by-one scan pattern. At request 5 the trigger fires and the sweep set is the rest of that list
  (/plant/c, /plant/d, ...), minus names already read or being read in request 5.

THE TRIGGER (all must hold) for a call of eligible read tool T on entity name E in request k:
  1. request k-1 has a call of the same T with all other arguments equal (an argument equal to its schema default counts as missing) on a different name P;
  2. E and P are both in one group of a successful result of a request earlier than k-1 (group = one JSON list value or one text section of a result;
     `episodes.groups_of` of the offline replay, unchanged). Several qualifying groups: the smallest one (ties: first found);
  3. E is neither already read by T with the same other arguments nor covered by an earlier sweep (live) / earlier shadow firing.
SWEEP SET = group in its own order, minus names called by T with the same other arguments in request k (the model's whole response is known),
  minus names T already ran on, minus names covered earlier; cut to the first MAX_SWEEP_NAMES. Empty: no firing. At most one firing per request.
The 3000-token limit needs real results and is applied by the arm (round2_harness.py) while the sweep runs.

This tracker is fed in event order: register_model_calls(k, ...) when the model's response k arrives, evaluate(...) after each call has returned,
add_result(...) for every successful result. The offline test (tests/test_round2.py) feeds recorded traces through it and compares with the replay.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "offline_replay_20261116"))
sys.path.insert(0, str(HERE.parent / "build_round1_20261115"))
import episodes as E  # noqa: E402  (offline replay: parsing, group definition, name rule)

ELIGIBLE_TOOLS = ("ros2_param_get", "ros2_param_list", "ros2_node_info", "ros2_topic_info", "ros2_service_info")  # read tools with an entity argument, not ros2_topic_echo
MAX_SWEEP_NAMES = 20
MAX_SWEEP_TOKENS = 3000


def entity_names(arguments):
    """(entity argument name, [names]) of a call, as the replay's expand_call reads it: the first argument whose name is node/topic/service (+ _name, plural)."""
    keys = [k for k in arguments if E.entity_argument(k)]
    if not keys:
        return None, []
    value = arguments[keys[0]]
    return keys[0], [n for n in (value if isinstance(value, list) else [value]) if isinstance(n, str)]


def other_arguments_key(tool, arguments, entity_key, defaults):
    """Canonical text of all arguments except the entity argument; an argument equal to its schema default is treated as missing."""
    tool_defaults = defaults.get(tool, {})
    rest = {k: v for k, v in arguments.items() if k != entity_key and not (k in tool_defaults and tool_defaults[k] == v)}
    return json.dumps(rest, sort_keys=True, default=str)


class SweepTracker:
    def __init__(self, defaults=None):
        self.defaults = defaults or {}                  # {tool: {argument: default}}
        self.model_calls = defaultdict(list)            # request -> [(tool, other-arguments key, entity)] from the model's response, executed or not
        self.results = []                               # (request, tool, output, text) of successful results
        self.executed = defaultdict(set)                # (request, tool, key) -> names whose call already returned in that request
        self.covered = defaultdict(set)                 # (tool, key) -> names read by an earlier sweep (live) or marked by a shadow firing
        self.fired_requests = set()
        self.first_fire_request = None

    # ---------------- inputs
    def register_model_calls(self, request, tool_calls):
        """tool_calls: [{'name':..., 'args':{...}}] of the model response of this request (includes calls that later fail)."""
        for call in tool_calls:
            if call["name"] == "final_answer" or not isinstance(call.get("args"), dict):
                continue
            entity_key, names = entity_names(call["args"])
            if entity_key is None:
                continue
            key = other_arguments_key(call["name"], call["args"], entity_key, self.defaults)
            for name in names:
                self.model_calls[request].append((call["name"], key, name))

    def add_result(self, request, tool, output, text, successful):
        if successful:
            self.results.append((request, tool, output, text))

    def earlier_groups(self, before_request):
        """[(group, (request, tool))] of successful results of requests with index < before_request (the replay's earlier_groups, plus the source)."""
        found = []
        for request, tool, output, text in self.results:
            if request >= before_request:
                continue
            for group in E.groups_of(output, text):
                found.append((group, (request, tool)))
        return found

    def queried(self, request, tool, key):
        """Names T already ran on with these other arguments: every call of earlier requests (the model's calls) plus calls of this request that returned."""
        names = set()
        for earlier, calls in self.model_calls.items():
            if earlier < request:
                names |= {e for (t, k, e) in calls if (t, k) == (tool, key)}
        return names | self.executed[(request, tool, key)]

    def all_queried(self):
        return {e for calls in self.model_calls.values() for (_t, _k, e) in calls}

    # ---------------- the decision
    def evaluate(self, request, tool, arguments):
        """Call after the call of `tool` with `arguments` in `request` returned normally. Returns a firing dict or None (state is updated either way)."""
        if tool not in ELIGIBLE_TOOLS:
            return None
        entity_key, names = entity_names(arguments)
        if entity_key is None:
            return None
        key = other_arguments_key(tool, arguments, entity_key, self.defaults)
        pair = (tool, key)
        firing = None
        for entity in names:
            known = self.queried(request, tool, key)
            if firing is None and request not in self.fired_requests and entity not in self.covered[pair] and entity not in known:
                for (previous_tool, previous_key, previous) in self.model_calls.get(request - 1, []):
                    if (previous_tool, previous_key) == pair and previous != entity:
                        common = [(g, src) for (g, src) in self.earlier_groups(request - 1) if previous in g and entity in g]
                        if common:
                            group, source = min(common, key=lambda item: len(item[0]))
                            called_now = {e for (t, k, e) in self.model_calls.get(request, []) if (t, k) == pair}
                            exclude = called_now | known | self.covered[pair] | {previous, entity}
                            candidates = [n for n in group if n not in exclude]
                            if candidates:
                                firing = dict(request=request, tool=tool, entity_key=entity_key, key=key, trigger_name=entity, previous_name=previous,
                                              group=group, group_source=dict(request=source[0], tool=source[1]), group_size=len(group),
                                              sweep=candidates[:MAX_SWEEP_NAMES], cut_by_name_limit=candidates[MAX_SWEEP_NAMES:])
                                self.fired_requests.add(request)
                                if self.first_fire_request is None:
                                    self.first_fire_request = request
                            break
            self.executed[(request, tool, key)].add(entity)
        return firing

    def mark_covered(self, firing, names):
        self.covered[(firing["tool"], firing["key"])] |= set(names)
