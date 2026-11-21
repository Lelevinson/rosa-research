import itertools, math, unittest
from cpaw import *

class CPAWTests(unittest.TestCase):
    def fixture(self,n=4,k=2,parallel=4,probs=None,setup=0):
        ids=tuple('p'+str(i) for i in range(n))
        plan=Plan(Goal('K_OF_N',ids,k),tuple(Probe(x,'generic',{'index':i}) for i,x in enumerate(ids)),'snapshot-1',parallel)
        reg={'generic':Registration('generic',True,'TRI_STATE_V1',True,True,lambda args: set(args)=={'index'} and type(args['index']) is int)}
        model=independent(probs or [(0.5,0.5,0)]*n)
        return plan,reg,model,Costs((1.,)*n,(1.,)*n,setup,0.)
    def test_01_no_equal_value_equivalence(self):
        p,r,m,c=self.fixture(2,1)
        self.assertEqual([x.id for x in p.probes],['p0','p1'])
        self.assertEqual(len(waves(p,r,(P,P))),3)
        e=Evidence('p0',T,'generic',scope_of(p.probes[0]),1.,p.snapshot)
        self.assertEqual(ingest(p,(P,P),[e],(0,)),(T,P))
    def test_02_binary_degeneracy_and_classical_branch(self):
        for kind,nonterminal in [('ANY',F),('ALL',T)]:
            g=Goal(kind,('a','b','c'))
            self.assertEqual([x for x in (T,F) if certificate(g,(x,P,P))=='PENDING'],[nonterminal])
        p,r,m,c=self.fixture(4,2,1,[(.5,.5,0),(.5,.5,0),(.95,.05,0),(.05,.95,0)])
        solve=exact_policy(p,r,c,m,1)
        self.assertEqual(solve((T,F,P,P))[1],(2,))
        self.assertEqual(solve((F,F,P,P))[1],(3,))
    def test_03_opaque(self):
        p,r,m,c=self.fixture()
        r['generic']=Registration('generic',True,'raw text',True,True)
        with self.assertRaises(ValueError):p.validate(r)
        with self.assertRaises(ValueError):ingest(p,(P,)*4,['Node X ready'],(0,))
    def test_04_wrong_plan_not_complete(self):
        # Independent evaluator knows obligation is enumeration; certificate does not.
        g=Goal('ANY',('a','b','c'))
        s=(T,P,P)
        self.assertEqual(certificate(g,s),'TRUE')
        self.assertFalse(all(x!=P for x in s))
    def test_05_unknown_not_false(self):
        self.assertEqual(certificate(Goal('ANY',('a','b','c')),(U,F,F)),'UNRESOLVED')
        self.assertEqual(certificate(Goal('ALL',('a','b','c')),(U,F,T)),'FALSE')
    def test_06_snapshot(self):
        p,r,m,c=self.fixture()
        bad=Evidence('p0',T,'generic',scope_of(p.probes[0]),1.,'different')
        with self.assertRaises(ValueError):ingest(p,(P,)*4,[bad],(0,))
        with self.assertRaises(ValueError):Plan(p.goal,p.probes,'',4).validate(r)
    def test_07_conflict_and_permission(self):
        p,r,m,c=self.fixture()
        p=Plan(p.goal,p.probes,p.snapshot,4,frozenset({('p0','p1')}))
        self.assertFalse(p.feasible((0,1),r))
        r['generic']=Registration('generic',True,'TRI_STATE_V1',False,True,lambda args: True)
        self.assertFalse(p.feasible((0,2),r))
        r['generic']=Registration('generic',False,'TRI_STATE_V1',True,True)
        with self.assertRaises(ValueError):p.validate(r)
    def test_08_cold_and_new_contract(self):
        p,r,m,c=self.fixture()
        p.validate(r)
        ref=lambda s:(next(i for i,x in enumerate(s) if x==P),)
        a=Rollout(p,r,c,(),ref,cold=True)
        self.assertEqual(a.choose((P,)*4),(0,))
        self.assertEqual(a.last['fallback'],'cold_or_model_mismatch')
        p2=Plan(p.goal,tuple(Probe(x.id,'brand_new',x.arguments) for x in p.probes),p.snapshot,4)
        p2.validate({'brand_new':Registration('brand_new',True,'TRI_STATE_V1',True,True,lambda args: True)})
    def test_09_inference_cost_not_claimed(self):
        def total(native,inference):return native+inference
        self.assertEqual(total(2,100)-total(1,100),1)
        self.assertEqual((total(2,100)-total(1,100))/total(2,100),1/102)
    def test_10_misspecification_and_joint_dependence(self):
        p,r,m,c=self.fixture(2,1)
        correlated=Model((((T,T),.5),((F,F),.5)))
        self.assertEqual(dict(correlated.outcomes((T,P),(1,)))[(T,T)],1.)
        ref=lambda s:tuple(i for i,x in enumerate(s) if x==P)[:1]
        a=Rollout(p,r,c,(correlated,),ref)
        self.assertEqual(a.choose((T,F)),()) # terminal and no remaining
        # evidence impossible under the scenario: reference, not fabricated confidence
        p,r,m,c=self.fixture(3,2)
        corr=Model((((T,T,T),.5),((F,F,F),.5)))
        a=Rollout(p,r,c,(corr,),ref)
        self.assertEqual(a.choose((T,F,P)),(2,))
        self.assertEqual(a.last['fallback'],'cold_or_model_mismatch')
    def test_11_native_aggregation_parity(self):
        # Bulk is a generic separately authorized option shared across arms; counted as native cost.
        # This prototype cannot infer that a bulk operation proves multiple propositions.
        p,r,m,c=self.fixture(2,1,2)
        self.assertEqual(c.wave((0,1)),2)
        self.assertIn((0,1),waves(p,r,(P,P)))
        bulk=Costs((1.,1.),(1.,1.),0.,0.,(((0,1),.7,.5,3),))
        self.assertEqual(bulk.wave((0,1)),.7)
        self.assertEqual(bulk.accounting((0,1))[2],3) # one wrapper can perform three native operations
        self.assertEqual(exact_policy(p,r,bulk,m)((P,P))[1],(0,1))
    def test_12_setup_and_sequential_optimality(self):
        p,r,m,c=self.fixture(3,1,3)
        s=(P,)*3
        self.assertAlmostEqual(exact_policy(p,r,c,m)(s)[0],exact_policy(p,r,c,m,1)(s)[0])
        c=Costs((1.,)*3,(1.,)*3,10.,0.)
        self.assertEqual(exact_policy(p,r,c,m)(s)[1],(0,1,2))
    def test_13_certificate_not_intent(self):
        g=Goal('K_OF_N',('a','b','c'),2)
        self.assertEqual(certificate(g,(T,T,P)),'TRUE')
        intent_correct=False
        self.assertFalse(intent_correct)
    def test_registry_claim_does_not_authorize(self):
        from eligibility import inspect_registry
        class Schema:
            @staticmethod
            def model_json_schema(): return {'title':'example'}
        class NewTool:
            name='new'
            metadata={'outcome_contract':'TRI_STATE_V1','read_only':True,'authorized':True}
            @staticmethod
            def func(): pass
            @staticmethod
            def get_output_schema(): return Schema
        self.assertEqual(inspect_registry([NewTool()])['eligible'],0)
        trust={'new':{'outcome_contract':'TRI_STATE_V1','read_only':True,'authorized':True,'authorize_arguments':lambda args: True}}
        self.assertEqual(inspect_registry([NewTool()],trust)['eligible'],1)
    def test_corrupt_evidence_and_goal(self):
        for goal in [Goal('K_OF_N',('a','a'),1),Goal('K_OF_N',('a',),True),Goal('COUNT',('a',),1)]:
            with self.assertRaises(ValueError):goal.threshold()
        p,r,m,c=self.fixture()
        for evidence in [Evidence('p0',T,'wrong',scope_of(p.probes[0]),0.,p.snapshot),Evidence('p0',F,'generic','wrong',0.,p.snapshot),Evidence('p0',U,'generic',scope_of(p.probes[0]),float('nan'),p.snapshot)]:
            with self.assertRaises(ValueError):ingest(p,(P,)*4,[evidence],(0,))
    def test_zero_budget_falls_back(self):
        p,r,m,c=self.fixture()
        ref=lambda s:(next(i for i,x in enumerate(s) if x==P),)
        a=Rollout(p,r,c,(m,),ref,max_nodes=0)
        self.assertEqual(a.choose((P,)*4),(0,))
        self.assertEqual(a.last['fallback'],'budget')
    def test_scenario_specific_continuations_are_clairvoyant(self):
        p,r,_,c=self.fixture(3,1,1)
        ma=independent([(0.,1.,0.),(.9,.1,0.),(.1,.9,0.)])
        mb=independent([(0.,1.,0.),(.1,.9,0.),(.9,.1,0.)])
        state=(F,P,P)
        single_a=best_schedule(p,r,c,(ma,),state)
        single_b=best_schedule(p,r,c,(mb,),state)
        common=best_schedule(p,r,c,(ma,mb),state)
        self.assertNotEqual(single_a,single_b)
        self.assertAlmostEqual(max(schedule_cost(p,c,m,state,sch) for m,sch in ((ma,single_a),(mb,single_b))),1.1)
        self.assertAlmostEqual(max(schedule_cost(p,c,m,state,common) for m in (ma,mb)),1.9)
    def test_argument_authorization_is_independent(self):
        p,r,m,c=self.fixture()
        r['generic']=Registration('generic',True,'TRI_STATE_V1',True,True)
        with self.assertRaises(ValueError):p.validate(r)
        r['generic']=Registration('generic',True,'TRI_STATE_V1',True,True,lambda args: False)
        with self.assertRaises(ValueError):p.validate(r)
    def test_invalid_costs_and_zero_cost(self):
        with self.assertRaises(ValueError):Costs((float('nan'),),(1.,))
        with self.assertRaises(ValueError):Costs((1.,),(1.,),-.1)
        p,r,m,_=self.fixture(2,1)
        cost=Costs((0.,0.),(0.,0.))
        self.assertIn(greedy(p,r,cost,m,(P,P)),waves(p,r,(P,P)))
    def test_execution_failure_and_deadline(self):
        p,r,m,c=self.fixture(2,1,1)
        selector=lambda s:(next(i for i,x in enumerate(s) if x==P),)
        def failed(plan,wave): raise TimeoutError('no response')
        result=execute(p,r,selector,failed,lambda plan:'ordinary',selector)
        self.assertEqual(result.status,'UNRESOLVED')
        self.assertEqual(result.state,(U,U))
        self.assertEqual(len(result.attempts),2)
        stopped=execute(p,r,selector,failed,lambda plan:'ordinary',selector,max_waves=0)
        self.assertEqual(stopped.status,'UNRESOLVED')
        self.assertEqual(stopped.state,(P,P))
        r['generic']=Registration('generic',False,'TRI_STATE_V1',True,True)
        fallback=execute(p,r,selector,failed,lambda plan:'ordinary',selector)
        self.assertEqual((fallback.status,fallback.ordinary_result),('FALLBACK','ordinary'))
    def test_all_worlds_certificate_sound(self):
        # Enumerate every partial T/F/U observation and every hidden completion.
        for k in (1,2,3):
            g=Goal('K_OF_N',('a','b','c'),k)
            for state in itertools.product((T,F,U,P),repeat=3):
                status=certificate(g,state)
                completions=list(itertools.product(*[(T,F) if x in (P,U) else (x,) for x in state]))
                if status=='TRUE':self.assertTrue(all(w.count(T)>=k for w in completions))
                if status=='FALSE':self.assertTrue(all(w.count(T)<k for w in completions))
                if status=='UNRESOLVED':self.assertTrue(any(w.count(T)>=k for w in completions) and any(w.count(T)<k for w in completions))

if __name__=='__main__':unittest.main(verbosity=2)
