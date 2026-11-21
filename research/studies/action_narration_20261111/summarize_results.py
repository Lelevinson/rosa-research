"""Postexecution accounting using explicit manual judgments; never a runtime policy."""
import argparse
import json
from pathlib import Path


def summarize(root):
    auto=json.loads((root/'automatic_scores.json').read_text())
    manual=json.loads((root/'manual_adjudication.json').read_text())
    review={r['episode']:r for r in manual}
    rows=auto['episodes']
    totals={}
    for arm in 'ABC':
        selected=[r for r in rows if r['arm']==arm]
        totals[arm]=dict(**auto['summary'][arm],
            supported_conditional=sum(review[r['episode']]['supported'] for r in selected),
            fields_total=sum(len(r['fields']) for r in selected),
            fields_value_correct=sum(v['correct'] for r in selected for v in r['fields'].values()),
            fields_supported=sum(v['supported_in_answer'] for r in selected for v in review[r['episode']]['fields'].values()),
            unsupported_claims=sum(review[r['episode']]['unsupported_value_claims'] for r in selected))
    pairs={}
    for arm in 'BC':
        tasks=sorted({r['task'] for r in rows if r['arm']==arm and review[r['episode']]['supported']}
                     & {r['task'] for r in rows if r['arm']=='A' and review[r['episode']]['supported']})
        metrics={}
        for label in ['A',arm]:
            selected=[r for r in rows if r['arm']==label and r['task'] in tasks]
            metrics[label]={k:sum(r[k] for r in selected) for k in
                ['model_calls','eval_count','prompt_eval_count','eval_duration','episode_seconds',
                 'native_attempts','action_words','action_eval_count','action_eval_duration','final_eval_count']}
        pairs[arm]=dict(tasks=tasks,metrics=metrics,
            reduction_percent={k:100*(metrics['A'][k]-metrics[arm][k])/metrics['A'][k]
                               for k in ['eval_count','eval_duration','episode_seconds']},
            limits='Post-outcome mutually supported subset specified by protocol; only Turtlesim, not full workload or generalization.')
    result=dict(protocol_closeout_valid=auto['protocol_closeout_valid'],
                source_supported_counts_are_conditional=True,totals=totals,mutually_supported_pairs=pairs,
                stage1_gate='FAIL: both B and C lose supported recovery task vs A; all x1 incomplete; no cross-application positive signal.',
                D='Rejected before implementation: no supported difference from static C.')
    (root/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path)
    summarize(p.parse_args().root)
