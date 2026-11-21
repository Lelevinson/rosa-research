"""Independent trace accounting and paired decision audit; no dispatch."""
import json, statistics
from collections import Counter, defaultdict
from pathlib import Path

root=Path(__file__).resolve().parent/'artifacts'
records=[json.loads(line) for line in (root/'traces.jsonl').read_text().splitlines()]
assert len(records)==720
errors=[]
for row in records:
    s=['-']*4; work=duration=obj=0;ops=0
    for item in row['log']:
        if item['state']!=s:errors.append('state chain')
        for i,x in zip(item['wave'],item['outcomes']):
            if s[i]!='-':errors.append('duplicate probe')
            if x!=row['world'][i]:errors.append('world mismatch')
            s[i]=x
        if s!=item['after']:errors.append('outcome chain')
        work+=item['native_work'];duration+=item['sim_elapsed_s'];ops+=item['native_operations']
        obj+=item['native_work']+.7+.25*item['sim_elapsed_s']
    t=s.count('T'); possible=t+s.count('U')+s.count('-')
    cert='TRUE' if t>=2 else 'FALSE' if possible<2 else 'UNRESOLVED' if '-' not in s else 'PENDING'
    if cert!=row['certificate'] or abs(work-row['native_work'])>1e-8 or abs(duration-row['sim_elapsed_s'])>1e-8 or ops!=row['native_operations'] or abs(obj-row['objective'])>1e-8:errors.append('accounting or certificate')
assert not errors,errors[:5]
paired={}
for family in sorted(set(r['family'] for r in records)):
    data={(r['seed'],r['arm']):r for r in records if r['family']==family}
    out={}
    for arm in ('initial','revised_unguarded','revised_guarded'):
      for control in ('fixed_robust','fixed_nominal','exact_wave','greedy'):
        differences=[]; common=changed=0; examples=[]
        for seed in range(101,113):
            a=data[seed,arm]; b=data[seed,control]
            differences.append(a['objective_incl_measured_compute']-b['objective_incl_measured_compute'])
            bmap={tuple(x['state']):x['wave'] for x in b['log']}
            for step in a['log']:
                state=tuple(step['state'])
                if state in bmap:
                    common+=1
                    if step['wave']!=bmap[state]:
                        changed+=1
                        if len(examples)<2:examples.append({'seed':seed,'state':state,'candidate':step['wave'],'control':bmap[state]})
        out[f'{arm}_vs_{control}']={'paired':12,'mean_cost_delta_including_compute':statistics.mean(differences),'wins':sum(x<-.000001 for x in differences),'losses':sum(x>.000001 for x in differences),'common_states':common,'different_waves':changed,'examples':examples}
    paired[family]=out
(root/'paired_audit.json').write_text(json.dumps(paired,indent=2,sort_keys=True)+'\n')
print('independently replayed',len(records),'episodes; errors',len(errors))
for family,rows in paired.items():
    print(family)
    for control in ('fixed_robust','exact_wave'):
        x=rows['revised_guarded_vs_'+control]
        print(' ',control,'delta',round(x['mean_cost_delta_including_compute'],4),'wins/losses',x['wins'],x['losses'],'same-state changes',x['different_waves'],'/',x['common_states'],'examples',x['examples'])
