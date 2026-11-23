import ast,json,math,pathlib,random,unittest
from functools import lru_cache
ROOT=pathlib.Path(__file__).resolve().parents[1]
tree=ast.parse((ROOT/'apex_music_video_plan.py').read_text(encoding='utf8'))
ns={'math':math,'random':random,'json':json,'lru_cache':lru_cache}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),'plan','exec'),ns)
plan=ns['music_video_plan'];read=ns['_sequence_shots']
class SequenceTests(unittest.TestCase):
    def make(self,total=240,b=1,c=True,seed=42):
        return plan(total,5,5,0,0,10,0,0,c,b,1,24,'sequential_shuffle',seed)
    def test_timing_matrix_is_exact_without_overlaps(self):
        for total in [1/24,1,4.9,5,10,17,120,150,234.96,240,480,1800,3600]:
            for b,c in [(0,False),(1,False),(0,True),(1,True)]:
                for seed in [0,1,42,991]:
                    p=self.make(total,b,c,seed);at=0
                    self.assertEqual(p['shots'][0]['role'],'singer')
                    for s in p['shots']:
                        self.assertEqual(s['start_frame'],at)
                        self.assertGreater(s['frames'],0)
                        self.assertLessEqual(s['frames'],240 if s['role']=='c_roll' else 120)
                        at+=s['frames']
                        if not b:self.assertNotEqual(s['role'],'b_roll')
                        if not c:self.assertNotEqual(s['role'],'c_roll')
                    self.assertEqual(at,round(total*24));self.assertEqual(len(p['shots']),p['total_passes'])
                    self.assertEqual(sum(p[k] for k in ['singer_passes','b_roll_passes','c_roll_passes']),p['total_passes'])
                    self.assertEqual(len(read(json.dumps(p))[1]),p['total_passes'])
    def test_deterministic_and_seed_changes_order(self):
        self.assertEqual(self.make(),self.make())
        self.assertNotEqual(self.make(seed=42)['shots'],self.make(seed=43)['shots'])
    def test_cost_reduction_counts_visible_seconds_only(self):
        p=self.make();self.assertEqual(sum(s['frames'] for s in p['shots']),5760)
        self.assertLess(p['singer_passes']*5,240)
        self.assertTrue(any(s['frames']==240 for s in p['shots'] if s['role']=='c_roll'))
    def test_corrupt_plan_is_rejected(self):
        for field,value in [('start_frame',1),('frames',0),('frames',361),('role','unknown')]:
            p=self.make();p['shots'][0][field]=value
            with self.assertRaises(ValueError):read(json.dumps(p))
    def test_layered_behavior_is_preserved(self):
        p=plan(240,20,3,8,17,3,14,17,True,3,5,24)
        self.assertEqual([p[k] for k in ['singer_passes','b_roll_passes','c_roll_passes','total_passes']],[12,12,12,36])
    def test_cutaway_opening_matrix_including_no_singer(self):
        for total in [1/24,1,4.9,5,10,17,120,240,480,3600]:
            for b,c in [(0,False),(1,False),(0,True),(1,True)]:
                for seed in [0,1,42,991]:
                    p=plan(total,5,5,0,0,10,0,0,c,b,1,24,'sequential_shuffle',seed,'cutaway')
                    allowed=({'b_roll'} if b else set()) | ({'c_roll'} if c else set())
                    self.assertIn(p['shots'][0]['role'],allowed or {'singer'})
                    at=0
                    for s in p['shots']:
                        self.assertEqual(s['start_frame'],at)
                        self.assertGreater(s['frames'],0)
                        if s['role']!='singer':self.assertIn(s['role'],allowed)
                        at+=s['frames']
                    self.assertEqual(at,round(total*24))
                    self.assertEqual(len(read(json.dumps(p))[1]),p['total_passes'])
                    if p['singer_passes']==0:self.assertEqual(p['last_singer_frames'],0)
    def test_explicit_opening_and_disabled_role_fallback(self):
        for requested in ['singer','b_roll','c_roll','cutaway']:
            for b,c in [(0,False),(1,False),(0,True),(1,True)]:
                p=plan(30,5,5,0,0,10,0,0,c,b,1,24,'sequential_shuffle',42,requested)
                enabled={'singer'} | ({'b_roll'} if b else set()) | ({'c_roll'} if c else set())
                actual=p['shots'][0]['role']
                self.assertIn(actual,enabled)
                if requested in enabled:self.assertEqual(actual,requested)
                elif enabled!={'singer'}:self.assertNotEqual(actual,'singer')
        roles={plan(30,5,5,0,0,10,0,0,True,1,1,24,'sequential_shuffle',s,'cutaway')['shots'][0]['role'] for s in range(32)}
        self.assertEqual(roles,{'b_roll','c_roll'})
        with self.assertRaisesRegex(ValueError,'opening shot'):
            plan(30,5,5,0,0,10,0,0,True,1,1,24,'sequential_shuffle',42,'bad')
    def test_cutaway_first_cycle_visits_all_enabled_roles(self):
        for seed in range(32):
            p=plan(120,5,5,0,0,10,0,0,True,1,1,24,'sequential_shuffle',seed,'cutaway')
            self.assertEqual({s['role'] for s in p['shots'][:3]},{'singer','b_roll','c_roll'})
            self.assertNotEqual(p['shots'][0]['role'],'singer')
    def test_existing_default_schedules_are_unchanged(self):
        original=ROOT/'original-plan.py'
        if not original.exists():
            for seed in [0,1,42,991]:self.assertEqual(self.make(seed=seed)['shots'][0]['role'],'singer')
            return
        scope={'math':math,'random':random}
        fn=next(n for n in ast.parse(original.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='music_video_plan')
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'original_plan','exec'),scope)
        for total in [1/24,5,17,240,3600]:
            for b,c in [(0,False),(1,False),(0,True),(1,True)]:
                for seed in [0,1,42,991]:
                    self.assertEqual(self.make(total,b,c,seed),scope['music_video_plan'](total,5,5,0,0,10,0,0,c,b,1,24,'sequential_shuffle',seed))
if __name__=='__main__':unittest.main()
