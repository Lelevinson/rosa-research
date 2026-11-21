import sys, json
sys.path.insert(0,"research/studies/stall_hint_v2_20261118")
import step1_offline as S
from collections import Counter
tasks=S.E.load_tasks()
weak={"bonsai-2:4b","lfm3:1.7b"}
cnt=Counter(); rows=[]
for g,row,sup in S.load_population():
    if row["model"] not in weak: continue
    if not ((g in("pilot","round1") and row["arm"]=="C1") or (g=="round2" and row["arm"]=="CONTROL")): continue
    if sup is not True: continue
    e=S.replay(g,row,sup,tasks,True)
    first=next((f for f in e["fires"] if f["type"]=="informative"),None)
    if not first: continue
    p=S.next_progress_call(e,first)
    if p is None: cnt["no_P (excluded from B2)"]+=1; continue
    c=S.classify_p(first,p)
    in_names=any(x in first["shown"] for x in p["entities"]); in_tools=p["tool"] in first["suggested"]
    cnt[(c, "names_ok" if in_names else "names_no", "tool_ok" if in_tools else "tool_no", "S_empty" if not first["suggested"] else "S_set")]+=1
    rows.append((e["model"],e["task"],e["seed"],first["request"],first["tool"],first["shown"],first["suggested"],p["request"],p["tool"],p["entities"]))
for k,v in cnt.items(): print(v,k)
for r in rows: print(r)

print("\n--- post-hoc: leading-slash-normalised comparison of P's entity (clean ledger) ---")
norm=lambda x: x if x.startswith("/") else "/"+x
c2=Counter()
for g,row,sup in S.load_population():
    if row["model"] not in weak: continue
    if not ((g in("pilot","round1") and row["arm"]=="C1") or (g=="round2" and row["arm"]=="CONTROL")): continue
    if sup is not True: continue
    e=S.replay(g,row,sup,tasks,True)
    first=next((f for f in e["fires"] if f["type"]=="informative"),None)
    if not first: continue
    p=S.next_progress_call(e,first)
    if p is None: continue
    n_ok=any(norm(x) in first["shown"] for x in p["entities"]); t_ok=p["tool"] in first["suggested"]
    if n_ok and t_ok: c2["pointed_delayed" if p["request"]>=first["request"]+2 else "pointed_immediate"]+=1
    elif first["shown"] and first["suggested"] and not n_ok and not t_ok: c2["contradicted"]+=1
    else: c2["indeterminate"]+=1
print(dict(c2), "pointed", c2["pointed_delayed"]+c2["pointed_immediate"], "of", sum(c2.values()), "delayed share", c2["pointed_delayed"], "of", c2["pointed_delayed"]+c2["pointed_immediate"])
