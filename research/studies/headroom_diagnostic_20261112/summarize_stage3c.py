"""Stage 3c tables and the frozen decision rule (writes STAGE3C_TABLES.md). Offline.
usage: summarize_stage3c.py <a1_run_dir>   (reads manual_labels_3c.json, stage3c_firstpass.json, blind_labels_3c.json, stage3c_blind_index.json)
"""
import collections, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
run = Path(sys.argv[1]).resolve()
final = json.loads((HERE / "manual_labels_3c.json").read_text())
first = {f"{i['episode']}:R{i['request']}": i for i in json.loads((HERE / "stage3c_firstpass.json").read_text())}
blind = json.loads((HERE / "blind_labels_3c.json").read_text()); blind.pop("_note")
bindex = {b["blind_id"]: f"{b['episode']}:R{b['request']}" for b in json.loads((HERE / "stage3c_blind_index.json").read_text())}
scores = {r["episode"]: r for r in json.loads((run / "scores_3.json").read_text()) if not r.get("status") and not r["pilot"]}
MODEL = {"ollama": "Qwen", "openai": "Luna"}
rows = []
for key, f in final.items():
    s, fp = scores[f["episode"]], first[key]
    rows.append(dict(key=key, **f, provider=s["provider"], template=s["template"], excess=s["excess"], line=fp["line"], stage3=fp["stage3_label"],
                     first=fp["first_pass"], first_of=fp["first_pass_of"]))

def removable(prov, of_override=None, sat_counts=True):
    """Per-episode removable (P1+P2+P3, capped at the episode excess; if the cap binds drop F first). of_override maps (cat) -> forced 'F'."""
    per, binds = {}, 0
    for ep in sorted({r["episode"] for r in rows if r["provider"] == prov}):
        mine = [r for r in rows if r["episode"] == ep and r["cat"] in ("P1", "P2", "P3") and (sat_counts or not r["sat"])]
        ofs = sorted(((of_override or {}).get(r["cat"], r["of"]) for r in mine), key=lambda x: 0 if x == "O" else 1)  # O first: F dropped first
        cap = scores[ep]["excess"]
        if len(ofs) > cap:
            binds += 1
        per[ep] = ofs[:cap]
    return per, binds

def branch(prov, of_override=None, sat_counts=True, total=47):
    per, binds = removable(prov, of_override, sat_counts)
    n = sum(len(v) for v in per.values()); o = sum(v.count("O") for v in per.values()); f = n - o
    top2 = sum(sorted((len(v) for v in per.values()), reverse=True)[:2])
    if n < 19:
        b = "stop method work"
    elif o > n / 2:
        b = "prompt control, not a method"
    else:
        b = "a target exists"
    fragile = n > 0 and top2 / n > 0.40
    return dict(n=n, o=o, f=f, top2=top2, fragile=fragile, branch=b, binds=binds)

out = ["# Stage 3c tables (offline replay of arm A1 excess requests; see PROTOCOL_STAGE3C.md)\n"]
for prov in ("ollama", "openai"):
    mine = [r for r in rows if r["provider"] == prov]
    out += [f"\n## {MODEL[prov]}: {len(mine)} excess requests\n", "| category | count | of which O | of which F | of which `sat` (P3 only by the requirements-satisfied clause) |", "|---|---:|---:|---:|---:|"]
    for cat in ("P1", "P2", "P3", "P4"):
        c = [r for r in mine if r["cat"] == cat]
        out.append(f"| {cat} | {len(c)} | {sum(r['of'] == 'O' for r in c) if cat != 'P4' else '-'} | {sum(r['of'] == 'F' for r in c) if cat != 'P4' else '-'} | {sum(r['sat'] for r in c)} |")
    out.append(f"| P4 optional extra step (`p4_unneeded`) | {sum(r['p4_unneeded'] for r in mine)} | | | |")
    out += ["\n### By template\n", "| template | excess requests | P1 | P2 | P3 | P4 |", "|---|---:|---:|---:|---:|---:|"]
    for t in ("upstream", "pointer", "hub", "service"):
        c = [r for r in mine if r["template"] == t]
        out.append(f"| {t} | {len(c)} | " + " | ".join(str(sum(r['cat'] == k for r in c)) for k in ("P1", "P2", "P3", "P4")) + " |")
    out += ["\n### By task\n", "| task | excess requests | P1 | P2 | P3 | P4 |", "|---|---:|---:|---:|---:|---:|"]
    for t in sorted({r["episode"].split("-")[1] for r in mine}):
        c = [r for r in mine if r["episode"].split("-")[1] == t]
        out.append(f"| {t} | {len(c)} | " + " | ".join(str(sum(r['cat'] == k for r in c)) for k in ("P1", "P2", "P3", "P4")) + " |")
    per_ep = collections.Counter(r["episode"] for r in mine)
    top = per_ep.most_common(2); total = len(mine)
    per, _ = removable(prov)
    remv = sorted(((len(v), e) for e, v in per.items()), reverse=True)
    out.append(f"\nLargest episode by excess: {top[0][0]} with {top[0][1]} of {total} ({100 * top[0][1] / total:.0f}%); two largest: {top[0][0]} + {top[1][0]} = {top[0][1] + top[1][1]} ({100 * (top[0][1] + top[1][1]) / total:.0f}%).")
    r0, r1 = remv[0], remv[1]
    nrem = sum(len(v) for v in per.values())
    out.append(f"Largest episode by removable: {r0[1]} with {r0[0]} of {nrem} ({100 * r0[0] / nrem:.0f}%); two largest: {r0[1]} + {r1[1]} = {r0[0] + r1[0]} ({100 * (r0[0] + r1[0]) / nrem:.0f}%).")
b = branch("ollama")
out += ["\n## Frozen decision rule (Qwen only)\n",
        f"- Removable (P1+P2+P3, capped per episode): **{b['n']} of 47** ({100 * b['n'] / 47:.1f}%); threshold 19. Cap bound in {b['binds']} episodes.",
        f"- O: **{b['o']}**, F: **{b['f']}** (O share {100 * b['o'] / b['n']:.1f}%).",
        f"- Two largest episodes by removable: {b['top2']} of {b['n']} = {100 * b['top2'] / b['n']:.1f}% (fragile if > 40%): **fragile: {'yes' if b['fragile'] else 'no'}**.",
        f"- Branch: **{b['branch']}**.",
        f"- Luna (information only): removable {branch('openai')['n']} of 13, O {branch('openai')['o']}, F {branch('openai')['f']}."]
out += ["\n## Sensitivities (not part of the frozen rule; they show how much the branch depends on judgments)\n",
        "| reading | removable | O | F | O share | two largest share | branch |", "|---|---:|---:|---:|---:|---:|---|"]
for label, kw in (("headline (manual O/F as labelled, sat items count)", {}),
                  ("without `sat` items (requirements-satisfied clause not counted)", dict(sat_counts=False)),
                  ("all P3 treated as F", dict(of_override={"P3": "F"})),
                  ("all P1 treated as F", dict(of_override={"P1": "F"})),
                  ("all P1 and P3 treated as F (only P2 is O)", dict(of_override={"P1": "F", "P3": "F"})),
                  ("all P2 treated as F (A1 already permits batching and Qwen did not)", dict(of_override={"P2": "F"})),
                  ("all P1, P2 and P3 treated as F", dict(of_override={"P1": "F", "P2": "F", "P3": "F"}))):
    x = branch("ollama", **kw)
    out.append(f"| {label} | {x['n']} | {x['o']} | {x['f']} | {100 * x['o'] / x['n']:.0f}% | {100 * x['top2'] / x['n']:.0f}% | {x['branch']} |")
# agreement
out += ["\n## Agreement\n"]
def agree(pairs, label):
    cat = sum(a[0] == b[0] for a, b in pairs); both = sum(a == b for a, b in pairs)
    out.append(f"- {label}: category {cat}/{len(pairs)} ({100 * cat / len(pairs):.0f}%); category and O/F {both}/{len(pairs)} ({100 * both / len(pairs):.0f}%).")
    return [(p, a, b) for p, (a, b) in zip(range(len(pairs)), pairs) if a != b]
pairs = []
ids = []
for bid, key in sorted(bindex.items()):
    pairs.append(((blind[bid]["cat"], blind[bid]["of"]), (final[key]["cat"], final[key]["of"]))); ids.append(f"{bid}={key}")
d1 = agree(pairs, "Blind relabel (15, first pass and Stage 3 labels hidden) vs final manual")
for i, a, b in d1:
    out.append(f"  - disagreement {ids[i]}: blind {a}, final {b}")
pairs = [((r["first"], r["first_of"]), (r["cat"], r["of"])) for r in rows]
d2 = agree(pairs, "Rule-based first pass vs final manual (all 60)")
fp_conf = collections.Counter((r["first"], r["cat"]) for r in rows if r["first"] != r["cat"])
out.append("  - first-pass category changes (first -> final: count): " + "; ".join(f"{a}->{b}: {n}" for (a, b), n in sorted(fp_conf.items())))
out.append("  - note: the same analyst (Claude) made the blind and the final labels, so the blind check measures consistency over time and with the sheet alone, not independent human agreement.")
# per-item table
out += ["\n## Every item (trace line is the `model_end` line of the request; trace = `stage3b_20261113T155721Z/<episode>/trace.jsonl`)\n",
        "| model | episode | task | request / line | Stage 3 label | first pass | final | O/F | sat | note |", "|---|---|---|---|---|---|---|---|---|---|"]
for r in sorted(rows, key=lambda r: (r["provider"] != "ollama", r["episode"], r["request"])):
    out.append(f"| {MODEL[r['provider']]} | {r['episode']} | {r['episode'].split('-')[1]} | R{r['request']} / {r['line']} | {r['stage3']} | {r['first']}/{r['first_of'] or '-'} | {r['cat']} | {r['of'] or '-'} | {'sat' if r['sat'] else ''} | {r['note']} |")
out += ["\n## O sentences used (generic, no task names; each is untested)\n"]
for s in sorted({r["sentence"] for r in rows if r["sentence"]}):
    out.append(f"- {s}  ({sum(r['sentence'] == s for r in rows if r['provider'] == 'ollama')} Qwen, {sum(r['sentence'] == s for r in rows if r['provider'] == 'openai')} Luna)")
(HERE / "STAGE3C_TABLES.md").write_text("\n".join(out) + "\n")
print("\n".join(out[:12])); print("..."); print("\n".join(l for l in out if l.startswith(("- ", "|")) and ("headline" in l or "treated" in l or "without" in l or "disagree" in l or "Blind" in l or "Rule" in l or "first-pass" in l)))
