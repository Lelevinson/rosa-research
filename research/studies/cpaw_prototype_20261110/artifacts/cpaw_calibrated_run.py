"""Offline, generic tri-state acquisition research prototype. No ROSA dependency."""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations, product, permutations
from time import perf_counter
from typing import Mapping
import math
import json

T, F, U, P = 'T', 'F', 'U', '-'

@dataclass(frozen=True)
class Goal:
    kind: str
    probe_ids: tuple[str, ...]
    k: int | None = None
    def threshold(self):
        n = len(self.probe_ids)
        if not n or len(set(self.probe_ids)) != n or any(not isinstance(x,str) or not x for x in self.probe_ids):
            raise ValueError('invalid probe IDs')
        if self.kind == 'ANY' and self.k is None: return 1
        if self.kind == 'ALL' and self.k is None: return n
        if self.kind == 'K_OF_N' and type(self.k) is int and 1 <= self.k <= n: return self.k
        raise ValueError('unsupported or invalid goal')

@dataclass(frozen=True)
class Probe:
    id: str
    tool: str
    arguments: Mapping
    resource: str = ''

@dataclass(frozen=True)
class Registration:
    name: str
    read_only: bool
    contract: str
    concurrent_safe: bool
    authorized: bool

@dataclass(frozen=True)
class Evidence:
    probe_id: str
    value: str
    source: str
    scope: str
    observed_at: float
    snapshot: str

@dataclass(frozen=True)
class Plan:
    goal: Goal
    probes: tuple[Probe, ...]
    # Trusted executor policy, not model-supplied; all evidence must bind to this snapshot.
    snapshot: str
    max_parallel: int
    conflicts: frozenset[tuple[str,str]] = frozenset()
    def validate(self, registry: Mapping[str, Registration]):
        self.goal.threshold()
        if tuple(p.id for p in self.probes) != self.goal.probe_ids or not self.snapshot or type(self.max_parallel) is not int or self.max_parallel < 1:
            raise ValueError('invalid bindings or snapshot')
        for p in self.probes:
            if not isinstance(p.arguments, Mapping) or not p.tool or p.tool not in registry:
                raise ValueError('unregistered or malformed probe')
            try: json.dumps(p.arguments, sort_keys=True, allow_nan=False)
            except (TypeError, ValueError): raise ValueError('invalid arguments')
            reg = registry[p.tool]
            if reg.name != p.tool or reg.read_only is not True or reg.authorized is not True or reg.contract != 'TRI_STATE_V1':
                raise ValueError('ordinary ROSA fallback required')
    def feasible(self, wave, registry):
        if not wave or len(wave)>self.max_parallel or len(set(wave))!=len(wave): return False
        if any(type(i) is not int or i<0 or i>=len(self.probes) for i in wave): return False
        if len(wave)>1 and any(not registry[self.probes[i].tool].concurrent_safe for i in wave): return False
        for i,j in combinations(wave,2):
            a,b=self.probes[i],self.probes[j]
            if (a.id,b.id) in self.conflicts or (b.id,a.id) in self.conflicts: return False
            if a.resource and a.resource == b.resource: return False
        return True

def certificate(goal, state):
    k=goal.threshold()
    if len(state)!=len(goal.probe_ids) or any(x not in (T,F,U,P) for x in state): raise ValueError('invalid state')
    if state.count(T)>=k: return 'TRUE'
    if state.count(T)+state.count(U)+state.count(P)<k: return 'FALSE'
    return 'UNRESOLVED' if P not in state else 'PENDING'

def scope_of(probe):
    return json.dumps(probe.arguments, sort_keys=True, separators=(',', ':'), allow_nan=False)

def ingest(plan, state, evidence, requested):
    """Only trusted executor-produced Evidence enters here; no raw text parsing."""
    out=list(state)
    if len(set(requested))!=len(requested) or len(evidence)!=len(requested): raise ValueError('missing or duplicate evidence')
    if any(not isinstance(e,Evidence) for e in evidence): raise ValueError('opaque evidence')
    by_id={e.probe_id:e for e in evidence}
    if len(by_id)!=len(evidence): raise ValueError('duplicate evidence')
    for i in requested:
        p=plan.probes[i]; e=by_id.get(p.id)
        if out[i]!=P or not isinstance(e,Evidence) or e.value not in (T,F,U) or e.source!=p.tool or e.scope!=scope_of(p) or e.snapshot!=plan.snapshot or not math.isfinite(e.observed_at):
            raise ValueError('invalid executor evidence')
        out[i]=e.value
    return tuple(out)

@dataclass(frozen=True)
class Model:
    """Explicit finite distribution over complete T/F/U vectors; may be correlated."""
    worlds: tuple[tuple[tuple[str,...], float], ...]
    def __post_init__(self):
        if not self.worlds or any(not math.isfinite(p) or p<0 or any(x not in (T,F,U) for x in w) for w,p in self.worlds): raise ValueError('invalid distribution')
        if abs(sum(p for _,p in self.worlds)-1)>1e-8: raise ValueError('distribution must sum to one')
        if len({len(w) for w,_ in self.worlds})!=1: raise ValueError('world dimensions')
    def conditional(self, state):
        if len(state)!=len(self.worlds[0][0]): raise ValueError('dimension mismatch')
        selected=[(w,p) for w,p in self.worlds if p and all(x==P or x==y for x,y in zip(state,w))]
        z=sum(p for _,p in selected)
        return [(w,p/z) for w,p in selected] if z else []
    def outcomes(self,state,wave):
        dist={}
        for world,p in self.conditional(state):
            s=list(state)
            for i in wave: s[i]=world[i]
            s=tuple(s); dist[s]=dist.get(s,0)+p
        return dist.items()

def independent(probs):
    worlds=[]
    for outcomes in product((T,F,U),repeat=len(probs)):
        p=math.prod(probs[i][(T,F,U).index(x)] for i,x in enumerate(outcomes))
        if p: worlds.append((outcomes,p))
    return Model(tuple(worlds))

@dataclass(frozen=True)
class Costs:
    native: tuple[float,...]
    duration: tuple[float,...]
    setup: float = 0.
    time_weight: float = 0.
    # Pre-authorized trusted bulk bindings: (exact proposition indices, work, elapsed,
    # actual underlying native operations). They are explicit input, never inferred.
    bulk: tuple = ()
    def accounting(self,b):
        individual=(sum(self.native[i] for i in b), max(self.duration[i] for i in b), len(b))
        options=[individual]+[(work,duration,ops) for indices,work,duration,ops in self.bulk if tuple(indices)==tuple(b)]
        return min(options,key=lambda x:(x[0]+self.time_weight*x[1],x[2]))
    def wave(self,b):
        native,duration,_=self.accounting(b)
        return native+self.setup+self.time_weight*duration

def waves(plan,registry,state):
    remaining=[i for i,x in enumerate(state) if x==P]
    return [b for z in range(1,min(len(remaining),plan.max_parallel)+1) for b in combinations(remaining,z) if plan.feasible(b,registry)]

def exact_policy(plan,registry,costs,model,max_wave=None):
    """Exact Bellman reference, conditional joint distribution; NOT efficient at scale."""
    @lru_cache(None)
    def solve(s):
        if certificate(plan.goal,s)!='PENDING': return (0.,())
        options=waves(plan,registry,s)
        if max_wave: options=[b for b in options if len(b)<=max_wave]
        if not model.conditional(s) or not options: return (float('inf'),())
        return min((costs.wave(b)+sum(p*solve(ns)[0] for ns,p in model.outcomes(s,b)), b) for b in options)
    return solve

def schedules(plan,registry,state,singletons=False):
    remaining=tuple(i for i,x in enumerate(state) if x==P)
    def rec(rem):
        if not rem:
            yield (); return
        for size in range(1,min(len(rem),1 if singletons else plan.max_parallel)+1):
            for b in combinations(rem,size):
                if plan.feasible(b,registry):
                    for tail in rec(tuple(i for i in rem if i not in b)): yield (b,)+tail
    return rec(remaining)

def schedule_cost(plan,costs,model,state,schedule):
    total=0.
    for world,prob in model.conditional(state):
        s=list(state); cost=0.
        for b in schedule:
            if certificate(plan.goal,s)!='PENDING': break
            cost+=costs.wave(b)
            for i in b:s[i]=world[i]
        total+=prob*cost
    return total

def best_schedule(plan,registry,costs,models,state,singletons=False,tick=None):
    # Exact static minimax over the supplied finite set, not a paper implementation.
    compatible=[m for m in models if m.conditional(state)]
    if not compatible:return ()
    best=None
    for sch in schedules(plan,registry,state,singletons):
        if tick: tick()
        item=(max(schedule_cost(plan,costs,m,state,sch) for m in compatible),sch)
        if best is None or item<best: best=item
    return best[1] if best else ()

def greedy(plan,registry,costs,model,state,width=1):
    # immediate certificate probability per cost, with uncertainty-neutral tie break
    legal=waves(plan,registry,state)
    if not model.conditional(state): return min(legal,key=lambda b:(len(b),b)) if legal else ()
    legal=[b for b in legal if len(b)<=width]
    def key(b):
        cert=sum(p for s,p in model.outcomes(state,b) if certificate(plan.goal,s)!='PENDING')
        # when no immediate certificate can occur, prefer probes reducing expected residual ambiguity
        gain=sum(p*abs(sum(x==T for x in s)-plan.goal.threshold()+.5) for s,p in model.outcomes(state,b))
        return (-(cert+1e-6*gain)/costs.wave(b),b)
    return min(legal,key=key) if legal else ()

class BudgetExceeded(Exception): pass

class Rollout:
    """Scenario robust finite-horizon rollout; nested sup is a rectangular relaxation.

    Models with zero conditional likelihood are excluded; if all are contradicted,
    abstain. This is not a simultaneous statistical coverage guarantee.
    """
    def __init__(self,plan,registry,costs,models,reference,depth=1,guard=0.,max_nodes=5000,seconds=.05,cold=False):
        self.plan,self.registry,self.costs,self.models,self.reference=plan,registry,costs,models,reference
        self.depth,self.guard,self.max_nodes,self.seconds,self.cold=depth,guard,max_nodes,seconds,cold
        self.nodes=0; self.last={}
    def choose(self,state):
        start=perf_counter(); self.nodes=0
        ref=self.reference(state)
        if not ref: return ()
        if self.cold or not any(m.conditional(state) for m in self.models):
            self.last={'fallback':'cold_or_model_mismatch','nodes':0};return ref
        def tick():
            self.nodes+=1
            if self.nodes>self.max_nodes or perf_counter()-start>self.seconds: raise BudgetExceeded
        def candidates(s):
            legal=waves(self.plan,self.registry,s)
            # Bounded, tool-agnostic: first 3 singletons, reference, prefix, full, and first 4 combinations.
            singles=[b for b in legal if len(b)==1][:3]
            multi=[b for b in legal if len(b)>1]
            baseline=self.reference(s)
            return sorted(set(singles+multi[:4]+multi[-1:]+([baseline] if baseline else [])))
        @lru_cache(None)
        def baseline_schedule(s):
            tick()
            # One common policy across all still plausible scenarios, no hidden oracle.
            return best_schedule(self.plan,self.registry,self.costs,self.models,s,tick=tick)
        @lru_cache(None)
        def q_vector(s,b,h):
            tick(); vals=[]
            for m in self.models:
                if not m.conditional(s):
                    vals.append(None); continue
                v=self.costs.wave(b)
                for ns,p in m.outcomes(s,b):
                    if certificate(self.plan.goal,ns)!='PENDING':continue
                    if h<=1:
                        sch=baseline_schedule(ns)
                        nxt=schedule_cost(self.plan,self.costs,m,ns,sch) if sch else 0.
                    else:
                        opts=candidates(ns)
                        nxt=min((worst(q_vector(ns,c,h-1)) for c in opts),default=0.)
                    v+=p*nxt
                vals.append(v)
            return tuple(vals)
        def worst(vector):
            return max((v for v in vector if v is not None), default=float('inf'))
        try:
            opts=candidates(state)
            vectors={b:q_vector(state,b,self.depth) for b in opts}
            if ref not in vectors: vectors[ref]=q_vector(state,ref,self.depth)
            values={b:worst(v) for b,v in vectors.items()}
            best=min(values,key=lambda b:(values[b],b))
            # Paired advantage must hold in every modeled scenario. It is still only
            # a modeled one-step claim, not a guarantee under misspecification.
            diffs=[x-y for x,y in zip(vectors[ref],vectors[best]) if x is not None and y is not None]
            advantage=min(diffs,default=0.)
            chosen=best if advantage>self.guard else ref
            self.last={'fallback':'margin' if chosen==ref else '', 'nodes':self.nodes,'advantage':advantage,'q':{str(k):v for k,v in values.items()}}
            return chosen
        except BudgetExceeded:
            self.last={'fallback':'budget','nodes':self.nodes};return ref
