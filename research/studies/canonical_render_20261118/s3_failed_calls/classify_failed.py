"""Offline, CPU only. Classify every failed call of the live rendering run (all 288 episodes; S3 reported separately) by cause, from the raw results.
Causes are tested in this order (first match):
  precheck_args   : harness 'Invalid arguments' message (nothing reached ROS)
  regex_pattern   : 'multiple repeat' / regex error from a pattern argument
  no_type_topic   : 'Could not determine the type for the passed topic' (echo of a topic without publisher)
  not_found_near  : entity not seen before as an exact string, but within edit distance 2 of a name seen in an earlier result or the task text (typo / truncation)
  not_found_unseen: entity not seen before and not near any seen name (invented)
  not_found_seen  : entity (leading slash added or not) equals a name seen before, but the call still failed
  other           : anything else
Also: whether the episode saw the correct name only in a derived 'Node full name' line is NOT used here; this file only classifies."""
import json, re, sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import analyze_live as A
C = A.C
tasks = A.tasks_all()
NAME = re.compile(r"/?[A-Za-z0-9_][A-Za-z0-9_./-]*")

def edit_distance(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

def strings(v):
    if isinstance(v, str): yield v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield str(k); yield from strings(x)
    elif isinstance(v, list):
        for x in v: yield from strings(x)

rows = [json.loads(l) for l in (HERE.parent / "RESULTS_LOG_LIVE.jsonl").read_text().splitlines()]
rows = [r for r in rows if r.get("phase") == "full"]
out = []
for row in rows:
    read = C.v2.s1.read_events
    C.v2.s1.read_events = lambda path, read=read: A.events_with_raw_results(read(path))
    try:
        ep = C.parse_episode("live", row, tasks)
    finally:
        C.v2.s1.read_events = read
    seen = {m for m in NAME.findall(ep["task_text"]) if "/" in m or len(m) > 3}
    for r in ep["requests"]:
        new = set()
        for c in r["calls"]:
            if c["tool"] == "final_answer":
                continue
            text = c["text"] if isinstance(c["text"], str) else json.dumps(c["text"])
            if not c["ok"]:
                ent = c.get("entity")
                if text.startswith("Invalid arguments"):
                    cause = "precheck_args"
                elif "multiple repeat" in text or "nothing to repeat" in text:
                    cause = "regex_pattern"
                elif "Could not determine the type" in text:
                    cause = "no_type_topic"
                elif ent is not None:
                    bare = ent.lstrip("/")
                    exact = ent in seen or ("/" + bare) in seen
                    if exact:
                        cause = "not_found_seen"
                    else:
                        near = [s for s in seen if edit_distance(ent.lstrip("/"), s.lstrip("/")) <= 2 and ent.lstrip("/") != s.lstrip("/")]
                        cause = "not_found_near" if near else "not_found_unseen"
                else:
                    cause = "other"
                out.append(dict(arm=row["arm"], model=row["model"], task=row["task"], seed=row["seed"], stratum=A.stratum(row["task"]), request=r["index"],
                                tool=c["tool"], entity=ent, cause=cause, text=text[:120], trace=row["trace_path"]))
            else:
                for s in strings(c["output"]):
                    new.update(NAME.findall(s))
        seen |= new  # names become visible only after the request that fetched them
(HERE / "failed_causes.jsonl").write_text("\n".join(json.dumps(o) for o in out) + "\n")
tab = collections.defaultdict(collections.Counter)
for o in out:
    tab[(o["stratum"] == "S3", o["arm"])][o["cause"]] += 1
for k in sorted(tab):
    print("S3" if k[0] else "non-S3", k[1], sum(tab[k].values()), dict(tab[k]))
