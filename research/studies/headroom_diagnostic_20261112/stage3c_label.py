"""Stage 3c offline labelling of the Stage 3b (arm A1) excess requests. See PROTOCOL_STAGE3C.md. Offline only.

  stage3c_label.py firstpass  <repo_root> <a1_run_dir>   -> stage3c_firstpass.json (rule-based P1-P4 and O/F for the 60 items)
  stage3c_label.py blindsheet <repo_root> <a1_run_dir>   -> STAGE3C_BLIND_SHEET.md (15 items, no labels shown)
  stage3c_label.py show       <repo_root> <a1_run_dir> [episode ...] -> print items with call and result excerpts
"""
import json, random, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stage3_review import requests_of
from label_requests import string_leaves

EXCESS_LABELS = {"RED", "REC", "LATE", "NOARG", "EXPLORE"}
TASKS = {t["id"]: t for t in json.loads((HERE / "stage3_tasks.json").read_text())}
MODEL = {"ollama": "Qwen", "openai": "Luna"}
BLIND_SEED = 20261116


def element_keys(call):
    """What a call reads, as hashable keys (same idea as stage3_labels.call_elements, kept local so this file stands alone)."""
    n, a = call["name"], call["args"]
    if n == "ros2_node_list":
        return [("node_list",)]
    if n == "ros2_node_info":
        return [("node_info", x) for x in a.get("nodes", [])]
    if n == "ros2_topic_info":
        return [("topic_info", x) for x in a.get("topics", [])]
    if n == "ros2_param_get":
        return [("param_get", a.get("node_name"), a.get("param_name"))]
    return [(n, json.dumps(a, sort_keys=True))]


def load_items(repo_root, run):
    """Return (items, episodes). An item is one excess request. Asserts the Stage 3b Table 4 totals (47 Qwen, 13 Luna)."""
    scores = {r["episode"]: r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"]}
    labels = {e["episode"]: e for e in json.loads((run / "labels_3.json").read_text())}
    items, episodes, missing = [], {}, []
    for name, s in sorted(scores.items()):
        if not s["supported_complete"] or s["excess"] <= 0:
            continue
        try:
            reqs = requests_of(repo_root, run, name, s["task"])
        except Exception as exc:  # unreadable trace: report and continue (protocol section 1)
            missing.append((name, str(exc)))
            continue
        episodes[name] = dict(task=s["task"], provider=s["provider"], depth=s["depth"], excess=s["excess"], requests=reqs, template=s["template"])
        stage3 = dict(labels[name]["labels"])
        for r in reqs:
            if stage3.get(r["index"]) in EXCESS_LABELS:
                items.append(dict(episode=name, task=s["task"], provider=s["provider"], template=s["template"], request=r["index"],
                                  line=r["line"], stage3_label=stage3[r["index"]]))
    for prov, expected in (("ollama", 47), ("openai", 13)):
        got = sum(1 for i in items if i["provider"] == prov)
        assert got == expected, f"{prov}: {got} excess requests found, protocol expects {expected}; missing traces: {missing}"
    return items, episodes, missing


def results_text(request):
    return " ".join(c["text"] for c in request["calls"])


def first_pass(item, episode):
    """Rule-based P1-P4 from the episode's own calls and results (protocol section 4.1). Returns (category, o_or_f, note)."""
    reqs, k = episode["requests"], item["request"]
    me = next(r for r in reqs if r["index"] == k)
    earlier = [r for r in reqs if r["index"] < k]
    task_text = TASKS[item["task"]]["request"]
    ok_calls = [(c, e) for r in earlier for c in r["calls"] if c["ok"] for e in element_keys(c)]
    ok_keys = {e for _, e in ok_calls}
    ok_sigs = {json.dumps([c["name"], c["args"]], sort_keys=True) for r in earlier for c in r["calls"] if c["ok"]}

    def repeat(c):
        return json.dumps([c["name"], c["args"]], sort_keys=True) in ok_sigs or (element_keys(c) and all(e in ok_keys for e in element_keys(c)))

    if all(repeat(c) for c in me["calls"]):
        return "P3", "O", "repeats a call or reads only elements already read successfully"
    prev = next((r for r in reversed(earlier)), None)
    if prev and any(not c["ok"] for c in prev["calls"]):
        history = " ".join(results_text(r) for r in earlier)
        names = [x for c in me["calls"] for x in string_leaves(c["args"])]
        held = all(x in history for x in names if x.startswith("/"))
        return "P1", ("O" if held else "F"), "follows a failed call; corrected name " + ("was already in an earlier result" if held else "was not in any earlier result")
    known_text = task_text + " " + " ".join(results_text(r) for r in earlier if r["index"] <= k - 2)
    args = [x for c in me["calls"] for x in string_leaves(c["args"])]
    if args and all(x in known_text for x in args):
        return "P2", "O", "all arguments known before request k-1"
    return "P4", None, "arguments first appear in the result of request k-1, or no rule fits"


def show_request(episode, k, width=220):
    r = next(r for r in episode["requests"] if r["index"] == k)
    lines = []
    for c in r["calls"]:
        res = re.sub(r"\s+", " ", c["text"])[:width]
        lines.append(f"    CALL {c['name'].replace('ros2_', '')}{json.dumps(c['args'])[:110]} ok={c['ok']}\n      -> {res}")
    return f"  R{k} (model_end line {r['line']})\n" + "\n".join(lines)


def main():
    cmd, repo_root, run = sys.argv[1], Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve()
    items, episodes, missing = load_items(repo_root, run)
    if missing:
        print("MISSING/UNREADABLE traces:", missing)
    if cmd == "firstpass":
        for it in items:
            it["first_pass"], it["first_pass_of"], it["first_pass_note"] = first_pass(it, episodes[it["episode"]])
        (HERE / "stage3c_firstpass.json").write_text(json.dumps(items, indent=1))
        from collections import Counter
        for prov in ("ollama", "openai"):
            print(MODEL[prov], dict(Counter(i["first_pass"] for i in items if i["provider"] == prov)))
    elif cmd == "blindsheet":
        rng = random.Random(BLIND_SEED)
        ids = sorted(rng.sample(range(len(items)), 15))
        out = ["# Stage 3c blind sheet (15 requests; no first-pass or Stage 3 label shown)\n",
               "Label each request P1/P2/P3/P4 and, for P1-P3, O or F, per PROTOCOL_STAGE3C.md sections 3 and 4.\n"]
        chosen = []
        for n, i in enumerate(ids, 1):
            it = items[i]
            ep = episodes[it["episode"]]
            out.append(f"\n## B{n:02d}  {it['episode']}  ({MODEL[it['provider']]}, task {it['task']})  request R{it['request']}\n")
            out.append(f"Task text: {TASKS[it['task']]['request']}\n")
            for r in ep["requests"]:
                if r["index"] <= it["request"]:
                    out.append(show_request(ep, r["index"], 160) + ("   <== LABEL THIS REQUEST" if r["index"] == it["request"] else ""))
            chosen.append(dict(blind_id=f"B{n:02d}", episode=it["episode"], request=it["request"]))
        (HERE / "STAGE3C_BLIND_SHEET.md").write_text("\n".join(out) + "\n")
        (HERE / "stage3c_blind_index.json").write_text(json.dumps(chosen, indent=1))
        print(f"wrote 15 blind items, seed {BLIND_SEED}")
    elif cmd == "show":
        wanted = set(sys.argv[4:])
        for name, ep in episodes.items():
            if wanted and name not in wanted:
                continue
            mine = [i for i in items if i["episode"] == name]
            if not mine:
                continue
            print(f"\n## {name} task {ep['task']} {MODEL[ep['provider']]} excess={ep['excess']}  items: {[i['request'] for i in mine]}")
            print("  task:", TASKS[ep["task"]]["request"][:300])
            for r in ep["requests"]:
                print(show_request(ep, r["index"], 200))


if __name__ == "__main__":
    main()
