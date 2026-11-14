"""Compare actual cut discovery to an independent per-frame visibility oracle."""
import ast
import copy
import pathlib
import random
import unittest

HERE=pathlib.Path(__file__).resolve()
source=HERE.parents[1]/"apex_timeline_cut_window.py"
if not source.exists():source=HERE.with_name("apex_timeline_cut_window_candidate.py")
tree=ast.parse(source.read_text(encoding="utf-8"));ns={}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.FunctionDef))],type_ignores=[]),str(source),"exec"),ns)
windows=ns["v1_cut_windows"]

def project(clips,fps=24):
    return {"fps":fps,"tracks":[{"index":0,"clips":[{"start":s,"duration":d} for s,d in clips]}]}

class VisibleCuts(unittest.TestCase):
    def test_duplicate_start_has_no_cut_at_zero(self):
        self.assertEqual(windows(project([(0,10),(0,10),(10,10)]),3,2),[(8,3,10)])

    def test_zero_frame_tail_is_ignored(self):
        self.assertEqual(windows(project([(0,10),(10,10),(20,.000001)]),3,2),[(8,3,10)])

    def test_gap_is_not_a_picture_to_picture_cut(self):
        self.assertEqual(windows(project([(0,10),(15,10)]),3,2),[])

    def test_overlay_end_restores_underlying_clip(self):
        self.assertEqual(windows(project([(0,30),(10,5)]),3,2),[(8,3,10),(13,3,15)])

    def test_hidden_clip_start_does_not_create_cut(self):
        self.assertEqual(windows(project([(5,5),(0,20)]),3,2),[])

    def test_long_broll_and_short_final_picture(self):
        self.assertEqual(windows(project([(0,10),(10,.5)]),30,2),[(8,2.5,10)])

    def test_upper_track_does_not_change_v1(self):
        p=project([(0,10),(10,10)]);p['tracks'].append({'index':1,'clips':[{'start':0,'duration':100}]})
        self.assertEqual(windows(p,3,2),[(8,3,10)])

    def test_visibility_oracle_random_edits(self):
        rng=random.Random(20261108)
        for _ in range(1200):
            fps=rng.choice([23.976,24,25,30,60]);raw=[];intervals=[]
            for index in range(rng.randint(1,25)):
                a=rng.randint(0,200);b=a+rng.randint(0,80)
                raw.append((a/fps,(b-a)/fps));intervals.append((a,b))
            end=max(b for a,b in intervals);visible=[]
            for frame in range(end):
                visible.append(next((i for i in reversed(range(len(intervals))) if intervals[i][0]<=frame<intervals[i][1]),None))
            expected=[frame for frame in range(1,len(visible)) if visible[frame-1] is not None and visible[frame] is not None and visible[frame-1]!=visible[frame]]
            self.assertEqual([round(c*fps) for s,d,c in windows(project(raw,fps),3,1)],expected)

    def test_no_mutation_of_saved_project(self):
        p=project([(0,10),(10,10)]);before=copy.deepcopy(p);windows(p,3,2)
        self.assertEqual(p,before)

    def test_invalid_inputs_are_explained(self):
        for fps in [0,-1,float('nan'),float('inf')]:
            with self.assertRaisesRegex(ValueError,'frame rate'):windows(project([(0,10),(10,10)],fps),3,2)
        for duration,lead in [(0,0),(-1,2),(3,-1),(3,float('nan')),(float('inf'),2)]:
            with self.assertRaises(ValueError):windows(project([(0,10),(10,10)]),duration,lead)

    def test_hour_of_one_second_clips(self):
        result=windows(project([(i,1) for i in range(3600)]),3,2)
        self.assertEqual(len(result),3599)
        self.assertEqual(result[-1],(3597,3,3599))

if __name__=='__main__':unittest.main()
