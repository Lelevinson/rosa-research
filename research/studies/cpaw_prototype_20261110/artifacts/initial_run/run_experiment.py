"""Frozen offline paired synthetic experiment. Writes detailed JSONL and summaries."""
import hashlib, importlib.util, json, random, statistics, sys, time
from collections import Counter, defaultdict
from pathlib import Path
import cpaw as C

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cpaw_initial',ROOT/'artifacts/cpaw_initial.py')
initial=importlib.util.module_from_spec(spec);sys.modules[spec.name]=initial;spec.loader.exec_module(initial)

FAMILIES=('binary','unknown','correlated','misspecified','bulk')
ARMS=('full','fixed2','greedy','fixed_robust','robust_singleton','exact_singleton','exact_wave','initial','revised_unguarded','revised_guarded','cold')

def distribution(seed,family):
    rng=random.Random(seed)
    n=4
    ps=[rng.uniform(.18,.82) for _ in range(n)]
    if family=='correlated': ps=[.5]*n
    u=.08 if family=='unknown' else 0.
    def model(delta):
        return C.independent([(max(.01,min(.98-u,p+delta))*(1-u), (1-max(.01,min(.98-u,p+delta)))*(1-u),u) for p in ps])
    models=(model(0),model(-.12),model(.12))
    if family=='correlated': truth=C.Model((((C.T,)*4,.5),((C.F,)*4,.5)))
    elif family=='misspecified':truth=C.independent([(.05,.95,0)]*n)
    else:truth=models[0]
    return models,truth,ps,u

def sample(model,rng):
    r=rng.random();q=0.
    for w,p in model.worlds:
        q+=p
        if r<q:return w
    return model.worlds[-1][0]

def main():
    traces=[]
    for family in FAMILIES:
      for seed in range(101,113):
        models,truth,ps,u=distribution(seed,family)
        world=sample(truth,random.Random(90000+seed))
        ids=tuple(f'p{i}' for i in range(4))
        plan=C.Plan(C.Goal('K_OF_N',ids,2),tuple(C.Probe(x,'typed',{'index':i}) for i,x in enumerate(ids)),'offline-snapshot',2)
        registry={'typed':C.Registration('typed',True,'TRI_STATE_V1',True,True)}
        plan.validate(registry)
        rng=random.Random(seed*11)
        costs=C.Costs(tuple(round(rng.uniform(.6,1.4),2) for _ in ids),tuple(round(rng.uniform(.3,1.2),2) for _ in ids),.7,.25,
              (((0,1),.5,.5,3),) if family=='bulk' else ())
        startstate=(C.P,)*4
        # This fixed minimax schedule is shared data. Its measured preparation is
        # charged to every user including arms that depend on it.
        start=time.perf_counter()
        robust=C.best_schedule(plan,registry,costs,models,startstate)
        robust_prep=time.perf_counter()-start
        start=time.perf_counter()
        robust_seq=C.best_schedule(plan,registry,costs,models,startstate,singletons=True)
        seq_prep=time.perf_counter()-start
        def next_schedule(schedule,s):
            return next((tuple(i for i in b if s[i]==C.P) for b in schedule if any(s[i]==C.P for i in b)),())
        ref=lambda s:next_schedule(robust,s)
        for arm in ARMS:
            s=startstate; log=[]; native=elapsed=objective=sched=0.;ops=0; fallbacks=Counter()
            prep=robust_prep if arm in ('fixed_robust','initial','revised_unguarded','revised_guarded','cold') else seq_prep if arm=='robust_singleton' else 0.
            if arm.startswith('exact_'): solve=C.exact_policy(plan,registry,costs,models[0],1 if arm=='exact_singleton' else None)
            if arm=='initial':policy=initial.Rollout(plan,registry,costs,models,ref,depth=1,guard=0.,max_nodes=5000,seconds=2.)
            if arm.startswith('revised_') or arm=='cold':
                policy=C.Rollout(plan,registry,costs,models,ref,depth=1,guard=.02 if arm=='revised_guarded' else 0.,max_nodes=5000,seconds=2.,cold=arm=='cold')
            while C.certificate(plan.goal,s)=='PENDING':
                before=time.perf_counter()
                if arm=='full': wave=max(C.waves(plan,registry,s),key=lambda b:(len(b),tuple(-i for i in b)))
                elif arm=='fixed2': wave=next_schedule(((0,1),(2,3)),s)
                elif arm=='greedy':wave=C.greedy(plan,registry,costs,models[0],s,width=2)
                elif arm=='fixed_robust':wave=ref(s)
                elif arm=='robust_singleton':wave=next_schedule(robust_seq,s)
                elif arm.startswith('exact_'):
                    _,wave=solve(s)
                    # Under misspecification, impossible histories take normal reference.
                    if not wave:wave=ref(s);fallbacks['model_mismatch']+=1
                else:
                    wave=policy.choose(s)
                    if policy.last.get('fallback'):fallbacks[policy.last['fallback']]+=1
                dt=time.perf_counter()-before;sched+=dt
                if not wave or not plan.feasible(wave,registry):raise RuntimeError((arm,s,wave))
                before_state=s
                evidence=[C.Evidence(ids[i],world[i],'typed',C.scope_of(plan.probes[i]),float(len(log)),plan.snapshot) for i in wave]
                s=C.ingest(plan,s,evidence,wave)
                work,duration,nops=costs.accounting(wave)
                native+=work;elapsed+=duration;ops+=nops;objective+=costs.wave(wave)
                log.append({'state':before_state,'wave':wave,'outcomes':[world[i] for i in wave],'after':s,'decision_s':dt,
                            'native_work':work,'native_operations':nops,'sim_elapsed_s':duration,
                            'policy':getattr(policy,'last',{}) if arm in ('initial','revised_unguarded','revised_guarded','cold') else {}})
            cert=C.certificate(plan.goal,s)
            # True/false certificate checked over all completions of missing and unknown values.
            true_n=s.count(C.T);possible=true_n+s.count(C.U)+s.count(C.P)
            sound=(cert=='TRUE' and true_n>=2) or (cert=='FALSE' and possible<2) or cert=='UNRESOLVED'
            traces.append({'family':family,'seed':seed,'world':world,'truth_marginal_t':[sum(p for w,p in truth.worlds if w[i]==C.T) for i in range(4)],
                           'nominal_p':ps,'nominal_u':u,'arm':arm,'certificate':cert,'sound':sound,'probes_attempted':sum(x!=C.P for x in s),'waves':len(log),
                           'native_work':native,'native_operations':ops,'sim_elapsed_s':elapsed,'objective':objective,
                           'scheduler_s':sched,'preparation_s':prep,'objective_incl_measured_compute':objective+.25*(sched+prep),
                           'sim_inference_s':100.,'fallbacks':dict(fallbacks),'log':log,
                           'scope':'synthetic; certificate only; no task intent evaluation'})
    out=ROOT/'artifacts'
    with (out/'traces.jsonl').open('w') as f:
        for x in traces:f.write(json.dumps(x,sort_keys=True)+'\n')
    summary={}
    for family in FAMILIES:
      summary[family]={}
      for arm in ARMS:
        group=[x for x in traces if x['family']==family and x['arm']==arm]
        means={k:statistics.mean(x[k] for x in group) for k in ('objective','objective_incl_measured_compute','native_work','native_operations','sim_elapsed_s','scheduler_s','preparation_s','probes_attempted','waves')}
        means.update({'episodes':len(group),'certificates':dict(Counter(x['certificate'] for x in group)),
                      'sound':sum(x['sound'] for x in group),'fallbacks':dict(sum((Counter(x['fallbacks']) for x in group),Counter()))})
        summary[family][arm]=means
    # Pairwise differences are over 12 fixed tasks per family. No CI claimed with this small non-random suite.
    for family in FAMILIES:
      b={x['seed']:x for x in traces if x['family']==family and x['arm']=='fixed_robust'}
      for arm in ('initial','revised_unguarded','revised_guarded'):
        pair=[x for x in traces if x['family']==family and x['arm']==arm]
        summary[family][arm]['mean_delta_vs_fixed_robust']=statistics.mean(x['objective']-b[x['seed']]['objective'] for x in pair)
        summary[family][arm]['initial_wave_differs_from_fixed_robust']=sum(x['log'][0]['wave']!=b[x['seed']]['log'][0]['wave'] for x in pair)
    (out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print('episodes',len(traces),'sound',sum(x['sound'] for x in traces),'unresolved',sum(x['certificate']=='UNRESOLVED' for x in traces))
    for family in FAMILIES:
        print(family,' '.join(f"{a}={summary[family][a]['objective']:.3f} (+compute {summary[family][a]['objective_incl_measured_compute']:.3f})" for a in ('fixed_robust','exact_wave','initial','revised_unguarded','revised_guarded')))

if __name__=='__main__':main()
