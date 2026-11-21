"""POST-HOC (not in the frozen protocol): relaxed retry matching. The frozen definition counts a retry only if the later call equals the converted arguments exactly;
a model that retries an optional field it got wrong usually just omits it. Here a later call counts as a retry if it equals the converted arguments after dropping every
key whose value is an empty array, empty string or null (on both sides). Everything else as in PROTOCOL.md. Labelled post-hoc; the frozen results are unchanged.
  nice uv run python research/studies/arg_type_retry_offline_20261119/posthoc_relaxed_retry.py"""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arg_type_retry as R  # noqa: E402


def norm(args):
    return json.dumps({k: v for k, v in args.items() if v not in ([], "", None)}, sort_keys=True)


def main():
    rows = []
    for study, row in R.C.load_population():
        events, requests = R.read_episode(row)
        fixable = {}
        for request in requests:
            for call in request["calls"]:
                schema = request["schemas"].get(call["name"])
                verdict = R.judge_call(call["name"], call["args"], schema) if schema else None
                if verdict and verdict["fixable"]:
                    fixable.setdefault((call["name"], norm(verdict["converted"])), []).append(request["index"])
        if not fixable:
            continue
        pure = mixed = 0
        tokens = 0
        for request in requests:
            keys = [(c["name"], norm(c["args"])) for c in request["calls"]]
            hits = [k for k in keys if any(r < request["index"] for r in fixable.get(k, []))]
            if hits and len(hits) == len(keys):
                pure += 1
                tokens += request.get("usage", {}).get("input_tokens", 0) + request.get("usage", {}).get("output_tokens", 0)
            elif hits:
                mixed += 1
        rows.append(dict(study=study, arm=row["arm"], model=row["model"], full_type=(study, row["arm"]) in R.C.FULL_TYPE, pure=pure, mixed=mixed, tokens=tokens, requests=row["llm_requests"], trace=row["trace_path"]))
    full = [r for r in rows if r["full_type"]]
    all_full_requests = sum(r["llm_requests"] for _s, r in R.C.load_population() if (_s, r["arm"]) in R.C.FULL_TYPE)
    out = dict(all=dict(episodes_with_fixable=len(rows), pure_retry_requests=sum(r["pure"] for r in rows), mixed=sum(r["mixed"] for r in rows), tokens=sum(r["tokens"] for r in rows)),
               full_type_menu=dict(episodes_with_fixable=len(full), pure_retry_requests=sum(r["pure"] for r in full), mixed=sum(r["mixed"] for r in full), tokens=sum(r["tokens"] for r in full),
                                   share_of_requests=sum(r["pure"] for r in full) / all_full_requests, models=sorted({r["model"] for r in full})))
    (HERE / "posthoc_relaxed_retry.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


main()
