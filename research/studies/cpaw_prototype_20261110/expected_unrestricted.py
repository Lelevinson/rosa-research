"""Exact expectation under the calibrated nominal model, 12 unrestricted tasks."""
import json, time, random
from functools import lru_cache
from pathlib import Path
import cpaw as C
from run_experiment import distribution

out=[]
for seed in range(101,113):
    models,truth,_,_,_=distribution(seed,'binary')
    ids=tuple(f'p{i}' for i in range(4))
    plan=C.Plan(C.Goal('K_OF_N',ids,2),tuple(C.Probe(x,'typed',{'index':i}) for i,x in enumerate(ids)),'offline-snapshot',4)
    registry={'typed':C.Registration('typed',True,'TRI_STATE_V1',True,True,lambda args: set(args)=={'index'} and type(args['index']) is int)}
    cost=C.Costs((1.,)*4,(1.,)*4,.7,0.)
    state=(C.P,)*4
    fixed=C.best_schedule(plan,registry,cost,models[:1],state)
    robust=C.best_schedule(plan,registry,cost,models,state)
    def ref(s):return next((tuple(i for i in b if s[i]==C.P) for b in robust if any(s[i]==C.P for i in b)),())
    policy=C.Rollout(plan,registry,cost,models,ref,guard=.02,max_nodes=5000,seconds=2.)
    exact=C.exact_policy(plan,registry,cost,models[0])
    counter={'elapsed_s':0.,'decisions':0,'different_from_oracle':0}
    @lru_cache(None)
    def value(s):
        if C.certificate(plan.goal,s)!='PENDING':return 0.
        start=time.perf_counter(); wave=policy.choose(s); counter['elapsed_s']+=time.perf_counter()-start;counter['decisions']+=1
        if wave!=exact(s)[1]:counter['different_from_oracle']+=1
        return cost.wave(wave)+sum(prob*value(ns) for ns,prob in models[0].outcomes(s,wave))
    candidate=value(state)
    out.append({'seed':seed,'exact_fixed_nominal':C.schedule_cost(plan,cost,models[0],state,fixed),
                'exact_fixed_robust':C.schedule_cost(plan,cost,models[0],state,robust),
                'exact_adaptive':exact(state)[0],'candidate_guarded':candidate,'diagnostic':counter})
p=Path(__file__).resolve().parent/'artifacts/unrestricted/expected.json'
p.write_text(json.dumps(out,indent=2)+'\n')
for key in ('exact_fixed_nominal','exact_fixed_robust','exact_adaptive','candidate_guarded'):
    print(key,sum(x[key] for x in out)/len(out))
print('distinct state decisions',sum(x['diagnostic']['decisions'] for x in out),'different from optimal',sum(x['diagnostic']['different_from_oracle'] for x in out))
