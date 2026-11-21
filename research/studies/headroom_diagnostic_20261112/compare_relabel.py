"""Agreement between primary labels and the blind relabel (writes RELABEL_AGREEMENT.md)."""
import collections, csv, json, sys
from pathlib import Path
d = Path(sys.argv[1])
primary = {f"{r['episode']}#{r['request_index']}": r for r in csv.DictReader(open(d / "labeled_requests.csv"))}
blind = json.load(open(d / "relabel_blind_output.json"))
pairs = [(primary[k]["label"], v["label"], k) for k, v in blind.items()]
n = len(pairs); agree = sum(a == b for a, b, _ in pairs)
nf = [(a, b, k) for a, b, k in pairs if a != "FIN"]; agree_nf = sum(a == b for a, b, _ in nf)
labels = sorted({x for a, b, _ in pairs for x in (a, b)})
po = agree / n
pe = sum((sum(a == l for a, _, _ in pairs) / n) * (sum(b == l for _, b, _ in pairs) / n) for l in labels)
kappa = (po - pe) / (1 - pe)
avoid = lambda l: l in ("DEP", "RED")
agree_avoid = sum(avoid(a) == avoid(b) for a, b, _ in nf)
out = [f"# Blind relabel agreement\n", f"Sample: {n} of 269 labeled requests (seeded random 20%).\n",
       f"- Exact agreement: {agree}/{n} = {100*po:.0f}%; Cohen's kappa = {kappa:.2f}",
       f"- Excluding FIN (trivial): {agree_nf}/{len(nf)} = {100*agree_nf/len(nf):.0f}%",
       f"- Agreement on the coarse question 'avoidable (DEP or RED) vs not', excluding FIN: {agree_avoid}/{len(nf)} = {100*agree_avoid/len(nf):.0f}%\n",
       "Confusion (primary -> blind):\n", "| primary | blind | n |", "|---|---|---:|"]
for (a, b), c in sorted(collections.Counter((a, b) for a, b, _ in pairs).items()):
    out.append(f"| {a} | {b} | {c} |")
out += ["\nDisagreements:\n", "| request | primary | blind | blind reason |", "|---|---|---|---|"]
for a, b, k in pairs:
    if a != b: out.append(f"| {k} | {a} | {b} | {blind[k]['reason'][:110]} |")
(d / "RELABEL_AGREEMENT.md").write_text("\n".join(out) + "\n"); print("\n".join(out))
