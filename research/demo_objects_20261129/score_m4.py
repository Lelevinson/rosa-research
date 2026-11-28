"""Score Milestone 4 live takes from a session folder (scripted heuristics, answers are kept for a human check). usage: score_m4.py <rehearsals/<name>/SESSION.json>
Prompts in order per take: where / pick / put / put-again / out-of-scope. LABEL: demonstration only, not evaluated, not for the paper."""
import json, sys
from collections import defaultdict
s = json.load(open(sys.argv[1]))
rows = s['requests']
names = ['where', 'pick', 'put', 'put_again', 'out_of_scope']
res = defaultdict(list)
for i, r in enumerate(rows):
    kind = names[i % 5]
    fs = r.get('final_state') or {}
    calls = r.get('object_calls') or []
    ans = json.dumps(r.get('answer')) .lower() if r.get('answer') else ''
    moved = any(t in ('pick', 'place') for t, ok in calls) or r.get('run_skill_calls', 0) > 0
    if kind == 'where':
        ok = bool(r.get('answer')) and any(t == 'get_object_pose' for t, _ in calls) and not moved and '0.45' in ans
    elif kind == 'pick':
        ok = fs.get('block_held') is True and any(t == 'pick' and k for t, k in calls)
    elif kind == 'put':
        ok = fs.get('block_on_tray') is True and not fs.get('block_held') and any(t == 'place' and k for t, k in calls)
    elif kind == 'put_again':
        ok = fs.get('block_on_tray') is True and not any(t in ('pick', 'place') and k for t, k in calls) and ('tray' in ans or 'already' in ans)
    else:
        ok = bool(r.get('answer')) and not moved and not calls
    res[kind].append((ok, r['n'], (r.get('answer') or r.get('error') or '')[:140]))
for k in names:
    v = res[k]; print(k, '%d/%d' % (sum(o for o, _, _ in v), len(v)))
    for o, n, a in v: print('   ', n, 'PASS' if o else 'FAIL', a)
