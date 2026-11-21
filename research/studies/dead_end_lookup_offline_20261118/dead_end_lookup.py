"""Dead-end relation lookup, offline replay. Protocol: PROTOCOL.md (hash in PROTOCOL.sha256); read it first. CPU only, no model, no ROS.
  nice uv run python research/studies/dead_end_lookup_offline_20261118/dead_end_lookup.py
Flow: saved episodes (candidate_counts population) -> parse requests and calls -> find dead-end results of per-entity tools -> build the graph lines for the first dead end of each
(episode, entity) -> coverage, requests after the first dead end, upper-bound saving, look-alike exposure, tokens added -> results.json, fires.jsonl."""
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "research/studies"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDIES / "candidate_counts_20261118"))
import count_candidates as C  # noqa: E402

E = C.E
GRAPH_FILES = {"stage3": STUDIES / "headroom_diagnostic_20261112/stage3_graph.json", "e1h": STUDIES / "small_model_harness_20261115/e1h_graph.json",
               "namefix": STUDIES / "name_fix_applied_20261117/namefix_graph.json"}
ENTITY_TOOLS = {"ros2_node_info": "node", "ros2_param_list": "node", "ros2_param_get": "node", "ros2_topic_info": "topic", "ros2_service_info": "service"}
MAX_LINES, MAX_CHARS = 10, 600
ABS_TASKS = {"e1h_abs_1", "e1h_abs_2"}


def stratum(task):
    return "V2" if task == "v2" else ("ABS" if task in ABS_TASKS else "OTHER")


def env_of(task):
    return "e1h" if task.startswith("e1h_") else ("namefix" if task.startswith("nf_") else "stage3")


def norm(name):
    return "/" + name.lstrip("/") if isinstance(name, str) else name


# ------------------------------------------------------------------ the environment graph
def load_graph(env):
    """Items in fixture-file order: dict(kind, name, relation, relation_node). One item per (thing, relation)."""
    data = json.loads(GRAPH_FILES[env].read_text())
    items = []
    for node in data["nodes"]:
        items.append(dict(kind="node", name=node["fqn"], relation=None, node=None))
    for node in data["nodes"]:
        for topic in node.get("pubs", []):
            items.append(dict(kind="topic", name=topic["name"], relation="published by node", node=node["fqn"]))
        for topic in node.get("subs", []):
            items.append(dict(kind="topic", name=topic["name"], relation="subscribed by node", node=node["fqn"]))
        for service in node.get("services", []):
            items.append(dict(kind="service", name=service["name"], relation="provided by node", node=node["fqn"]))
        for key in node.get("params", {}):
            items.append(dict(kind="parameter", name=key, relation="of node", node=node["fqn"]))
    return data["namespace"].strip("/"), items


def segments_of(name, root):
    return [s for s in name.split("/") if s and s != root]


def item_matches(item, segment):
    if item["kind"] == "parameter":
        return item["name"] == segment
    return segment in item["name"].split("/")


def build_lines(entity, root, items):
    """The lines of PROTOCOL.md section 2: exact whole-segment matches, graph order, no ranking, at most MAX_LINES and MAX_CHARS."""
    lines, truncated = [], False
    for segment in segments_of(entity, root):
        for item in items:
            if not item_matches(item, segment):
                continue
            text = f"{segment} appears in: {item['kind']} {item['name']}" + (f" ({item['relation']} {item['node']})" if item["relation"] else "")
            if text in lines:
                continue
            if len(lines) >= MAX_LINES or sum(len(l) + 1 for l in lines) + len(text) + 1 > MAX_CHARS:
                return lines, True
            lines.append(text)
    return lines, truncated


def graph_has(entity, kind, items):
    return any(i["kind"] == kind and i["name"] == entity for i in items)


def lookalike_lines(entity, lines, items):
    """Node lines whose fqn is not the entity but has the same final segment or ends with the entity's path (protocol section 3, item 5)."""
    final = entity.rstrip("/").split("/")[-1]
    hits = []
    for line in lines:
        match = re.search(r"appears in: node (\S+)$", line)
        if match and match.group(1) != entity and (match.group(1).split("/")[-1] == final or match.group(1).endswith(entity)):
            hits.append(line)
    return hits


# ------------------------------------------------------------------ dead ends
def dead_end_class(call):
    """'a' not found, 'b' error with an empty message, 'c' empty; None if the call is not a dead end."""
    if call["harness_error"] or call["tool"] not in ENTITY_TOOLS or call.get("entity") is None or not isinstance(call["entity"], str):
        return None
    output, text = call["output"], call["text"]
    if E.NOT_FOUND.search(text):
        return "a"
    if isinstance(output, dict) and "error" in output and not str(output["error"]).strip():
        return "b"
    if output is None or (isinstance(output, (str, list, dict)) and not output) or (isinstance(output, str) and output.strip() in ("", "null", "None", "[]", "{}")):
        return "c"
    return None


def needed_entities(task):
    needed = []
    for item in task.get("support", []):
        if item[0] == "text" and isinstance(item[1], str) and item[1].startswith("/"):
            needed.append(item[1])
        elif item[0] == "param":
            needed.append(item[1])
    return list(dict.fromkeys(needed))


def episode_fires(ep, task):
    env = row_env = ep["env"]
    root, items = load_graph(env)
    needed = needed_entities(task)
    seen_before = []  # successful result texts in order, for 'covered-new'
    fired, fires, dead_ends = set(), [], 0
    results_after = []  # (request, text) of every successful call, to find where the episode obtained an entity
    for request in ep["requests"]:
        for call in request["calls"]:
            if call["tool"] != "final_answer" and call["ok"] and not call["harness_error"]:
                results_after.append((request["index"], call["text"]))
    for request in ep["requests"]:
        for call in request["calls"]:
            klass = dead_end_class(call)
            if klass is None:
                continue
            dead_ends += 1
            entity = norm(call["entity"])
            kind = ENTITY_TOOLS[call["tool"]]
            if (entity, kind) in fired:
                continue
            fired.add((entity, kind))
            if graph_has(entity, kind, items):
                fires.append(dict(request=request["index"], entity=entity, kind=kind, klass=klass, graph_has_it=True, lines=[], truncated=False, covered=False, covered_new=False,
                                  lookalike=[], tokens=0))
                continue
            lines, truncated = build_lines(entity, root, items)
            joined = "\n".join(lines)
            covered_entities = [n for n in needed if re.search(re.escape(n) + r"(?![\w/])", joined)]
            before_text = "\n".join(t for r, t in results_after if r < request["index"])
            covered_new = [n for n in covered_entities if n not in before_text]
            obtained = None
            for n in covered_entities:
                later = [r for r, t in results_after if r > request["index"] and n in t]
                if later:
                    obtained = min(later) if obtained is None else min(obtained, min(later))
            fires.append(dict(request=request["index"], entity=entity, kind=kind, klass=klass, graph_has_it=False, lines=lines, truncated=truncated, covered=bool(covered_entities),
                              covered_new=bool(covered_new), covered_entities=covered_entities, obtained_at=obtained, lookalike=lookalike_lines(entity, lines, items) if kind == "node" else [],
                              tokens=len(joined) / 4))
    return fires, dead_ends


def main():
    tasks = C.all_tasks()
    population = C.load_population()
    episodes, fire_rows = [], []
    for study, row in population:
        ep = C.parse_episode(study, row, tasks)
        task = tasks[row["task"]]
        ep["env"] = env_of(row["task"])
        if row.get("env") and row["env"] != ep["env"]:
            raise SystemExit(f"environment mismatch for {row['run_id']}: row {row['env']} vs task rule {ep['env']}")
        fires, dead_ends = episode_fires(ep, task)
        total = row["llm_requests"]
        requests = {r["index"]: r for r in ep["requests"]}
        first = fires[0]["request"] if fires else None
        real = [f for f in fires if not f["graph_has_it"]]
        # upper bound: first covered fire
        saved = never = tokens_saved = 0
        covered_first = next((f for f in real if f["covered"]), None)
        if covered_first is not None:
            f = covered_first["request"]
            if covered_first["obtained_at"] is not None:
                span = range(f + 1, covered_first["obtained_at"])
            else:
                span = range(f + 1, total)
                never = 1
            saved = len(span)
            tokens_saved = sum(requests[i]["input_tokens"] + requests[i]["output_tokens"] for i in span if i in requests)
        episodes.append(dict(study=study, run_id=row["run_id"], arm=row["arm"], model=row["model"], task=row["task"], stratum=stratum(row["task"]), seed=row["seed"],
                             full_type=(study, row["arm"]) in C.FULL_TYPE, stock=(study, row["arm"]) in {("s0", "S0"), ("pilot", "A1"), ("fairness", "E0"), ("fairness", "E1")},
                             supported=bool(ep["supported"]), requests=total, tokens=row["input_tokens"] + row["output_tokens"], dead_ends=dead_ends, fires=len(fires),
                             real_fires=len(real), graph_has_it=len(fires) - len(real), first_fire_request=first, requests_after_first=(total - first) if first else 0,
                             covered_fires=sum(f["covered"] for f in real), covered_new_fires=sum(f["covered_new"] for f in real), has_needed=bool(needed_entities(task)),
                             saved_max=saved, saved_never_obtained=never, tokens_saved_max=tokens_saved, lines_total=sum(len(f["lines"]) for f in real),
                             empty_line_fires=sum(not f["lines"] for f in real), truncated_fires=sum(f["truncated"] for f in real),
                             tokens_added=sum(f["tokens"] * (total - f["request"]) for f in real), lookalike_fires=sum(bool(f["lookalike"]) for f in real),
                             classes=dict(Counter(f["klass"] for f in fires)), trace=row["trace_path"]))
        for f in fires:
            fire_rows.append(dict(run_id=row["run_id"], arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], trace=row["trace_path"], **f))
    return episodes, fire_rows


def summarize(rows):
    with_fire = [r for r in rows if r["real_fires"]]
    needed_rows = [r for r in rows if r["has_needed"]]
    return dict(episodes=len(rows), requests=sum(r["requests"] for r in rows), tokens=sum(r["tokens"] for r in rows), episodes_with_dead_end=sum(bool(r["dead_ends"]) for r in rows),
                episodes_with_fire=len(with_fire), fires=sum(r["real_fires"] for r in rows), graph_has_it_fires=sum(r["graph_has_it"] for r in rows),
                empty_line_fires=sum(r["empty_line_fires"] for r in rows), truncated_fires=sum(r["truncated_fires"] for r in rows),
                fires_in_tasks_with_needed=sum(r["real_fires"] for r in needed_rows), covered_fires=sum(r["covered_fires"] for r in needed_rows),
                covered_new_fires=sum(r["covered_new_fires"] for r in needed_rows), requests_after_first_sum=sum(r["requests_after_first"] for r in with_fire),
                requests_after_first_median=statistics.median([r["requests_after_first"] for r in with_fire]) if with_fire else None,
                saved_max=sum(r["saved_max"] for r in rows), saved_never_obtained_episodes=sum(r["saved_never_obtained"] for r in rows), tokens_saved_max=sum(r["tokens_saved_max"] for r in rows),
                tokens_added=round(sum(r["tokens_added"] for r in rows)), lookalike_fires=sum(r["lookalike_fires"] for r in rows),
                supported_in_lookalike_episodes=sum(r["supported"] for r in rows if r["lookalike_fires"]), episodes_with_lookalike=sum(bool(r["lookalike_fires"]) for r in rows))


def bars(episodes):
    full = [r for r in episodes if r["full_type"]]
    f = summarize(full)
    per_model_fire = {m: sum(r["real_fires"] > 0 for r in full if r["model"] == m) for m in sorted({r["model"] for r in full})}
    b1 = f["episodes_with_fire"] / max(f["episodes"], 1) >= 0.10 and sum(v >= 5 for v in per_model_fire.values()) >= 3
    needed_all = summarize([r for r in episodes if r["has_needed"]])
    covered_models = {r["model"] for r in episodes if r["covered_fires"]}
    share = needed_all["covered_fires"] / max(needed_all["fires_in_tasks_with_needed"], 1)
    share_new = needed_all["covered_new_fires"] / max(needed_all["fires_in_tasks_with_needed"], 1)
    b2 = share >= 0.5 and needed_all["covered_fires"] >= 20 and len(covered_models) >= 2 and share_new >= 0.25
    b3 = f["saved_max"] >= 0.03 * f["requests"] and f["tokens_added"] < f["tokens_saved_max"]
    abs_look = [r for r in episodes if r["stratum"] == "ABS" and r["lookalike_fires"]]
    b4 = len(abs_look) == 0
    by_task = Counter()
    for r in episodes:
        by_task[r["task"]] += r["covered_fires"]
    top_task_share = (max(by_task.values()) / sum(by_task.values())) if sum(by_task.values()) else None
    klass = "A" if (b1 and b2 and b3 and b4) else ("C" if not b4 else "B")
    return dict(B1=dict(met=b1, episodes_with_fire_share=f["episodes_with_fire"] / max(f["episodes"], 1), models_with_5plus=per_model_fire), B2=dict(met=b2, covered_share=share, covered_new_share=share_new,
                covered_fires=needed_all["covered_fires"], models=sorted(covered_models)), B3=dict(met=b3, saved_max=f["saved_max"], requests=f["requests"], saved_share=f["saved_max"] / max(f["requests"], 1),
                tokens_added=f["tokens_added"], tokens_saved_max=f["tokens_saved_max"]), B4=dict(met=b4, abs_lookalike_episodes=len(abs_look)),
                top_task_share_of_covered=top_task_share, top_task=(by_task.most_common(1)[0][0] if by_task else None), klass=klass)


if __name__ == "__main__":
    episodes, fire_rows = main()
    out = dict(protocol_sha256=(HERE / "PROTOCOL.sha256").read_text().split()[0], episodes=len(episodes), overall=summarize(episodes), full_type=summarize([r for r in episodes if r["full_type"]]),
               menu_arms=summarize([r for r in episodes if not r["stock"]]), stock_arms=summarize([r for r in episodes if r["stock"]]),
               by_stratum={s: summarize([r for r in episodes if r["stratum"] == s]) for s in ("V2", "ABS", "OTHER")},
               by_stratum_full_type={s: summarize([r for r in episodes if r["stratum"] == s and r["full_type"]]) for s in ("V2", "ABS", "OTHER")},
               by_model={m: summarize([r for r in episodes if r["model"] == m]) for m in sorted({r["model"] for r in episodes})},
               by_task={t: summarize([r for r in episodes if r["task"] == t]) for t in sorted({r["task"] for r in episodes})},
               fire_classes=dict(Counter(f["klass"] for f in fire_rows)), bars=bars(episodes))
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=str))
    with (HERE / "fires.jsonl").open("w") as handle:
        for f in fire_rows:
            handle.write(json.dumps(f, default=str) + "\n")
    (HERE / "episodes.jsonl").write_text("\n".join(json.dumps(r, default=str) for r in episodes) + "\n")
    print(json.dumps(dict(overall=out["overall"], full_type=out["full_type"], bars=out["bars"], fire_classes=out["fire_classes"]), indent=1, default=str))
