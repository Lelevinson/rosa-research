"""Descriptive tables for PILOT_REPORT.md from RESULTS_LOG.jsonl (no inference, no tests of significance).

  uv run python pilot_report.py > report_tables.md
"""
from collections import defaultdict
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
all_rows = [json.loads(line) for line in (HERE / "RESULTS_LOG.jsonl").read_text().splitlines()]
EXCLUDED = json.loads((HERE / "INFRA_EXCLUDED.json").read_text()) if (HERE / "INFRA_EXCLUDED.json").exists() else {}
INFRA = set(EXCLUDED.get("infrastructure_failures", {}).get("run_ids", []))
SUPERSEDED = set(EXCLUDED.get("superseded_protocol", {}).get("run_ids", []))
rows = [r for r in all_rows if r["run_id"] not in INFRA | SUPERSEDED]  # all tables below use the valid episodes only
superseded_rows = [r for r in all_rows if r["run_id"] in SUPERSEDED]
TASKS = {t["id"]: t for t in json.loads((HERE.parent / "headroom_diagnostic_20261112" / "stage3_tasks.json").read_text())}
TASKS.update({t["id"]: t for t in json.loads((HERE / "e1h_tasks.json").read_text())})
ARM_ORDER = ["A1", "C1", "M0", "C1+FN", "C1+H2", "C1+H1e", "C1+H1n", "C1+H7"]
models = sorted({r["model"] for r in rows})


def fires(row, name):
    return [f for f in row["handler_fires"] if f.get("event") == name]


def relevant_nodes(task):
    names = {v for v in json.dumps([task["answer"], task["support"], task["request"]]).replace('"', " ").replace(",", " ").split() if v.startswith("/")}
    return names


def table_main():
    out = ["| model | arm | episodes | supported-complete | LLM requests (total) | input tokens | output tokens | native ops | aborted episodes |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for m in models:
        for a in ARM_ORDER:
            sel = [r for r in rows if r["model"] == m and r["arm"] == a]
            if not sel:
                continue
            out.append(f"| {m} | {a} | {len(sel)} | {sum(r['supported_complete'] for r in sel)} | {sum(r['llm_requests'] for r in sel)} | {sum(r['input_tokens'] for r in sel)} | "
                       f"{sum(r['output_tokens'] for r in sel)} | {sum(r['native_ops'] for r in sel)} | {sum(bool(r['aborts']) for r in sel)} |")
    return "\n".join(out)


def table_by_env():
    out = ["| model | arm | stage3 tasks (supported/n) | E1h tasks (supported/n) |", "|---|---|---:|---:|"]
    for m in models:
        for a in ARM_ORDER:
            cells = []
            for env in ("stage3", "e1h"):
                sel = [r for r in rows if r["model"] == m and r["arm"] == a and r["env"] == env]
                cells.append(f"{sum(r['supported_complete'] for r in sel)}/{len(sel)}" if sel else "-")
            if cells != ["-", "-"]:
                out.append(f"| {m} | {a} | {cells[0]} | {cells[1]} |")
    return "\n".join(out)


def paired():
    """Paired by (model, task, seed): C1 versus each other arm. b = C1 supported and arm not; c = arm supported and C1 not."""
    out = ["| model | arm vs C1 | pairs | both supported | C1 only (arm worse) | arm only (arm better) | neither |", "|---|---|---:|---:|---:|---:|---:|"]
    index = {(r["model"], r["task"], r["seed"], r["arm"]): r for r in rows}
    harmed = []
    for m in models:
        for a in ARM_ORDER:
            if a == "C1":
                continue
            n = both = b = c = neither = 0
            for (mm, task, seed, arm), r in index.items():
                if mm != m or arm != a or (m, task, seed, "C1") not in index:
                    continue
                base = index[(m, task, seed, "C1")]
                n += 1
                x, y = base["supported_complete"], r["supported_complete"]
                both += x and y
                b += x and not y
                c += y and not x
                neither += (not x) and (not y)
                if x and not y:
                    harmed.append((m, a, task, seed, r["run_id"], r["failure_rows"]))
            if n:
                out.append(f"| {m} | {a} | {n} | {both} | {b} | {c} | {neither} |")
    return "\n".join(out), harmed


def noise_floor():
    """Pairs C1 vs C1+H2 / C1+H1e in which the handler never fired: the prompt, tools and seed are identical, so a deterministic model would give the same
    episode. Differences here are sampling/runtime noise and bound what a paired difference between arms can mean."""
    index = {(r["model"], r["task"], r["seed"], r["arm"]): r for r in rows}
    quiet = {"C1+H2": ("h2_repair", "h2_no_repair"), "C1+H1e": ("reuse", "reuse_blocked")}
    out = ["| model | arm | pairs where the handler never fired | same supported flag and same request count | different outcome or request count |", "|---|---|---:|---:|---:|"]
    for m in models:
        for arm, names in quiet.items():
            same = diff = 0
            for (mm, task, seed, a), r in index.items():
                if mm != m or a != arm or (m, task, seed, "C1") not in index or any(fires(r, n) for n in names):
                    continue
                base = index[(m, task, seed, "C1")]
                if base["supported_complete"] == r["supported_complete"] and base["llm_requests"] == r["llm_requests"]:
                    same += 1
                else:
                    diff += 1
            if same + diff:
                out.append(f"| {m} | {arm} | {same + diff} | {same} | {diff} |")
    return "\n".join(out)


def h2_section():
    out = ["| run id | task | given | resolved | correct? (heuristic) | episode supported |", "|---|---|---|---|---|---:|"]
    count = correct = 0
    for r in rows:
        for f in fires(r, "h2_repair"):
            task = TASKS[r["task"]]
            if task["template"] == "absent":
                verdict = "incorrect (target is not running)"
            elif f["resolved"] in relevant_nodes(task):
                verdict = "correct (named in truth/support)"
                correct += 1
            else:
                verdict = "incorrect (not in truth/support)"
            count += 1
            out.append(f"| {r['run_id']} | {r['task']} | {f['given']} | {f['resolved']} | {verdict} | {r['supported_complete']} |")
    nr = sum(len(fires(r, "h2_no_repair")) for r in rows)
    return "\n".join(out) + f"\n\nH2 repairs: {count} (heuristic 'correct': {correct}); H2 decisions without repair (zero or several matches): {nr}.", count


def h1_section():
    out = ["| model | arm | reuse events | reuse blocked by event | changing-task episodes | answered with the stale value (not supported) |", "|---|---|---:|---:|---:|---:|"]
    for m in models:
        for a in ("C1+H1e", "C1+H1n"):
            sel = [r for r in rows if r["model"] == m and r["arm"] == a]
            if not sel:
                continue
            chg = [r for r in sel if r["task"].startswith("e1h_chg")]
            stale = [r for r in chg if not r["supported_complete"] and any(f.get("event") == "reuse" for f in r["handler_fires"])]
            out.append(f"| {m} | {a} | {sum(len(fires(r, 'reuse')) for r in sel)} | {sum(len(fires(r, 'reuse_blocked')) for r in sel)} | {len(chg)} | {len(stale)} |")
    return "\n".join(out)


def h7_section():
    out = ["| model | episodes | plan accepted | invalid plans | fallbacks | replans | accepted plans complete vs floor route | supported-complete | LLM requests (total) |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for m in models:
        sel = [r for r in rows if r["model"] == m and r["arm"] == "C1+H7"]
        if not sel:
            continue
        accepted = [f for r in sel for f in fires(r, "plan_accepted")]
        complete = [f for f in accepted if f.get("complete_vs_floor_route")]
        out.append(f"| {m} | {len(sel)} | {len(accepted)} | {sum(len(fires(r, 'plan_invalid')) for r in sel)} | {sum(len(fires(r, 'plan_fallback')) for r in sel)} | "
                   f"{sum(f.get('tool') == 'replan' for f in accepted)} | {len(complete)}/{len(accepted)} | {sum(r['supported_complete'] for r in sel)} | {sum(r['llm_requests'] for r in sel)} |")
    return "\n".join(out)


def m0_section():
    out = ["| model | M0 episodes | supertool called | supertool before any other tool | answered with final_answer |", "|---|---:|---:|---:|---:|"]
    for m in models:
        sel = [r for r in rows if r["model"] == m and r["arm"] == "M0"]
        if not sel:
            continue
        called = [r for r in sel if fires(r, "supertool_first_call")]
        first = [r for r in called if fires(r, "supertool_first_call")[0].get("tools_called_before") == 0]
        out.append(f"| {m} | {len(sel)} | {len(called)} | {len(first)} | n/a |")
    return "\n".join(out)


def wall_time_section():
    out = ["| model | arm | episodes | median s | p90 s | max s | episodes > 150 s |", "|---|---|---:|---:|---:|---:|---:|"]
    for m in models:
        for a in ARM_ORDER:
            t = sorted(r["wall_seconds"] for r in rows if r["model"] == m and r["arm"] == a)
            if not t:
                continue
            p90 = t[min(len(t) - 1, int(0.9 * len(t) + 0.999999) - 1)]
            out.append(f"| {m} | {a} | {len(t)} | {t[len(t) // 2]:.0f} | {p90:.0f} | {t[-1]:.0f} | {sum(x > 150 for x in t)} |")
    return "\n".join(out)


def abort_section():
    import re
    out = ["| model | arm | aborted episodes | causes |", "|---|---|---:|---|"]
    for m in models:
        for a in ARM_ORDER:
            sel = [r for r in rows if r["model"] == m and r["arm"] == a and r["aborts"]]
            if not sel:
                continue
            causes = defaultdict(int)
            for r in sel:
                for x in r["aborts"]:
                    key = "iteration limit (40)" if "iteration" in x else re.sub(r"\s+", " ", x)[:70]
                    causes[key] += 1
            out.append(f"| {m} | {a} | {len(sel)} | " + "; ".join(f"{k} x{v}" for k, v in causes.items()) + " |")
    return "\n".join(out)


def failure_rows_section():
    out = ["| model | arm | unsupported episodes | taxonomy rows (automatic, descriptive; row 9 and 15 not labelled) |", "|---|---|---:|---|"]
    for m in models:
        for a in ARM_ORDER:
            sel = [r for r in rows if r["model"] == m and r["arm"] == a and not r["supported_complete"]]
            if not sel:
                continue
            count = defaultdict(int)
            for r in sel:
                for x in r["failure_rows"]:
                    count[x] += 1
            out.append(f"| {m} | {a} | {len(sel)} | " + ", ".join(f"row {k}: {v}" for k, v in sorted(count.items())) + " |")
    return "\n".join(out)


if __name__ == "__main__":
    pairs, harmed = paired()
    h2, _ = h2_section()
    print(f"## Totals\n{len(rows)} episodes; models: {', '.join(models)}\n")
    print("## Per model and arm\n" + table_main() + "\n")
    print("## Supported-complete by environment\n" + table_by_env() + "\n")
    print("## Paired disagreement counts, C1 versus each arm (pairs = same model, task, seed)\n" + pairs + "\n")
    print("## Noise floor: C1 pairs in which the other arm's handler never fired\n" + noise_floor() + "\n")
    print("## H2 repairs\n" + h2 + "\n")
    print("## H1e / H1n reuse\n" + h1_section() + "\n")
    print("## H7 plans\n" + h7_section() + "\n")
    print("## M0 plan adoption\n" + m0_section() + "\n")
    print("## Wall time per episode\n" + wall_time_section() + "\n")
    print("## Abort causes per arm\n" + abort_section() + "\n")
    print("## Failure rows of unsupported episodes\n" + failure_rows_section() + "\n")
    print("## Excluded episodes (kept in RESULTS_LOG.jsonl)\n")
    print(f"- infrastructure failures (crashed before any model request): {len(INFRA)}")
    print(f"- superseded protocol, C1+H7 version 1 (valid tool names not shown to the model): {len(superseded_rows)} episodes, supported-complete {sum(r['supported_complete'] for r in superseded_rows)}, "
          f"invalid plans {sum(len(fires(r, 'plan_invalid')) for r in superseded_rows)}, accepted plans {sum(len(fires(r, 'plan_accepted')) for r in superseded_rows)}, LLM requests {sum(r['llm_requests'] for r in superseded_rows)}\n")
    print("## Episodes supported under C1 but not under the other arm (possible harm)\n")
    for h in harmed:
        print(f"- {h[0]} {h[1]} {h[2]} seed {h[3]}: {h[4]}, failure rows {h[5]}")
