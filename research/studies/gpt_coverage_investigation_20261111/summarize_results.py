"""Postexecution summaries using explicit independent adjudication, never runtime policy."""
import argparse
import json
from pathlib import Path

METRICS=['model_attempts','model_completions','model_errors','action_turns','final_turns',
         'input_tokens','output_tokens','action_input_tokens','action_output_tokens',
         'final_output_tokens','action_words','final_words','native_attempts','native_completions',
         'native_successes','proposed_tools','tool_starts','tool_returns','invalid_tool_calls',
         'guard_rejections','budget_rejections','episode_seconds','http_seconds','provider_setup_seconds']


def summarize(root):
    auto=json.loads((root/'automatic_evaluation.json').read_text())
    manual=json.loads((root/'manual_adjudication.json').read_text())
    judgments={r['episode']:r for r in manual}
    rows=auto['episodes'];groups={}
    for provider in ['openai','ollama']:
        for arm in ['A','B','V']:
            selected=[r for r in rows if r['provider']==provider and r['arm']==arm]
            group={k:sum(r[k] or 0 for r in selected) for k in METRICS}
            group.update(episodes=len(selected),
                facts_supported=sum(judgments[r['episode']]['facts_supported'] for r in selected),
                strict_complete=sum(judgments[r['episode']]['strict_complete_supported'] for r in selected),
                fields=sum(len(r['fields']) for r in selected),
                supported_fields=sum(v['supported'] for r in selected for v in r['fields'].values()))
            if provider=='ollama':
                group['backend_durations_seconds']={k:sum(r['ollama_durations_ns'][k] for r in selected)/1e9
                    for k in ['eval_duration','prompt_eval_duration','load_duration','total_duration']}
            groups[provider+'_'+arm]=group
    pairs={}
    for provider in ['openai','ollama']:
        for treatment in ['B','V']:
            controls={r['task']:r for r in rows if r['provider']==provider and r['arm']=='A'
                      and judgments[r['episode']]['strict_complete_supported']}
            selected={r['task']:r for r in rows if r['provider']==provider and r['arm']==treatment
                      and judgments[r['episode']]['strict_complete_supported']}
            tasks=sorted(set(controls)&set(selected))
            metrics={arm:{k:sum(source[t][k] for t in tasks) for k in
                     ['model_completions','input_tokens','output_tokens','native_attempts','episode_seconds']}
                     for arm,source in [('A',controls),(treatment,selected)]}
            pairs[provider+'_'+treatment]=dict(tasks=tasks,metrics=metrics,
                 limits='Single observations and post-outcome mutually strict-supported subset; no population inference.')
    result=dict(oracle_valid=auto['oracle_valid'],episodes=len(rows),facts_supported=sum(r['facts_supported'] for r in manual),
                strict_complete=sum(r['strict_complete_supported'] for r in manual),
                all_requested_fields=sum(len(r['fields']) for r in rows),
                supported_fields=sum(v['supported'] for r in rows for v in r['fields'].values()),
                groups=groups,mutually_strict_pairs=pairs,
                decision='No unavoidable factual-coverage tradeoff established; no novel framework algorithm promoted. Strict-order failures persist; ordinary controls remain decisive.')
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);summarize(p.parse_args().root)
