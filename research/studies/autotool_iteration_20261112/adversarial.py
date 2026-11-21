"""Executable synthetic revisions using the actual learner and current binder.

Each case gets a small explicitly synthetic history. Test truth is kept separate
from predictor inputs. This does not estimate ROSA frequencies or task success.
"""
import copy
import json

from replay import ART, Boundary, Predictor, STOP, canonical


def receipt(output, name='discover', arguments=None):
    return dict(name=name, source_arguments={} if arguments is None else arguments,
                output=output, error=False)


def state(output, **changes):
    value = dict(history=['["discover"]'], registry=[], error=False,
                 request='Inspect the discovered identity.',
                 receipts=[receipt(output)])
    value.update(changes)
    return value


def history(training_state, target):
    return [Boundary(copy.deepcopy(training_state), copy.deepcopy(target), {'copy':f'synthetic-{i}'}) for i in range(5)]


def association_first(template, current):
    """Initial equality-association filler: retained only to expose its defect."""
    if isinstance(template, str):
        return template
    proposed = []
    for call in template:
        args = {}
        for key, spec in call['bindings'].items():
            if not spec['origins']:
                return None
            ref = spec['origins'][0]
            try:
                item = current['receipts'][ref['receipt']]['output']
                for part in ref['path']:
                    item = item[part]
                args[key] = item
            except (IndexError, KeyError, TypeError):
                return None
        proposed.append(dict(name=call['name'], args=args))
    return proposed


def cases():
    train = state({'node':'/a'})
    target = [dict(name='inspect', args={'node':'/a'})]
    equal = state({'configured':'map','observed':'map'})
    return [
        ('goal_STOP',train,target,state({'node':'/b'},request='List names only.'),STOP),
        ('goal_details',train,target,state({'node':'/b'}),[dict(name='inspect',args={'node':'/b'})]),
        ('error_repair',train,target,state({'node':'/b'},error=True),STOP),
        ('same_value_distinct_source',equal,[dict(name='inspect',args={'frame':'map'})],equal,None),
        ('text_only',train,target,state('{"node":"/b"}'),None),
        ('changed_source_identity',train,target,state({'node':'/b'},receipts=[receipt({'node':'/b'},name='other_discovery')]),None),
        ('changed_schema',train,target,state({'node':{'id':'/b'}}),None),
        ('already_available_list_helper',state({'nodes':['/a','/b']}),[dict(name='inspect',args={'nodes':['/a','/b']})],state({'nodes':['/c','/d']}),[dict(name='inspect',args={'nodes':['/c','/d']})]),
    ]


def run():
    report=[]
    for name,training,target,current,truth in cases():
        rows=history(training,target)
        versions=[]
        for version,mode in enumerate(['ngram1','conditional','candidate']):
            policy=Predictor(mode);policy.fit(rows)
            prediction=policy.predict(current)
            if version==0 and prediction.get('bindings'):
                proposal=association_first(prediction['bindings'],current)
                admitted=proposal is not None and proposal!=STOP and not current['error']
            elif version==1:
                proposal=prediction.get('proposed')
                admitted=bool(proposal) and proposal!=STOP and not prediction.get('problems') and not current['error']
            else:
                proposal=prediction.get('proposed');admitted=prediction['admission']
            versions.append(dict(version=version,mode=mode,raw_proposal=proposal,
                                 diagnostic_admission=admitted,
                                 false_admission=admitted and (truth is None or canonical(proposal)!=canonical(truth)),
                                 full_prediction=prediction))
        strong=Predictor('conditional_backoff');strong.fit(rows)
        assert strong.predict(current)==prediction
        report.append(dict(case=name,synthetic=True,truth_evaluator_only=truth,versions=versions,
                           C_backoff_same_as_final=True,
                           B='Same authorized path expressible as a parameterized helper; no model selection tested'))
    (ART/'results/adversarial_learner.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({f'v{i}_false_admissions':sum(r['versions'][i]['false_admission'] for r in report) for i in range(3)}))
    assert report[0]['versions'][1]['false_admission']
    assert report[3]['versions'][0]['false_admission']
    assert not report[3]['versions'][1]['diagnostic_admission']
    assert all(not r['versions'][2]['diagnostic_admission'] for r in report)


if __name__=='__main__':
    run()
