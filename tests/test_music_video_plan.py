import ast
import importlib
import itertools
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if (ROOT / "apex_music_video_plan.py").exists():
    sys.path.insert(0, str(ROOT.parents[1]))
    pkg = types.ModuleType("music_plan_test")
    pkg.__path__ = [str(ROOT)]
    sys.modules[pkg.__name__] = pkg
    plan = importlib.import_module(pkg.__name__ + ".apex_music_video_plan").music_video_plan
else:
    source = pathlib.Path(__file__).with_name("apex_music_video_plan_candidate.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    ns = {}
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, (ast.Import, ast.FunctionDef))],
                            type_ignores=[]), str(source), "exec"), ns)
    plan = ns["music_video_plan"]


class MusicVideoPlanTests(unittest.TestCase):
    def make(self, **kw):
        params = dict(song_seconds=240, singer_seconds=20, b_roll_seconds=3,
                      b_roll_offset=8, b_roll_gap=17, c_roll_seconds=3,
                      c_roll_offset=14, c_roll_gap=17, enable_c_roll=True,
                      b_image_count=3, c_image_count=5, fps=24)
        params.update(kw)
        return plan(**params)

    def test_four_minutes_has_independent_twelve_pass_lanes(self):
        p = self.make()
        self.assertEqual([p[k] for k in ["singer_passes", "b_roll_passes", "c_roll_passes", "total_passes"]], [12,12,12,36])

    def test_tiny_floating_tail_does_not_create_an_extra_clip(self):
        for t in [239.999999, 240, 240.000001]:
            self.assertEqual(self.make(song_seconds=t)["singer_passes"], 12)

    def test_real_one_frame_tail_is_preserved(self):
        p = self.make(song_seconds=240+1/24)
        self.assertEqual((p["singer_passes"],p["last_singer_frames"]), (13,1))

    def test_duration_reference_and_fps_matrix(self):
        for fps,total,singer,b,c,en in itertools.product(
                [23.976,24,25,30,60], [1/24,.5,3,10,10.000001,20,150,179.88,240,240.000001,480,1800,3600],
                [3,5,10,20], [0,1,4,17], [0,1,5,17], [False,True]):
            p=self.make(fps=fps,song_seconds=total,singer_seconds=singer,b_image_count=b,c_image_count=c,enable_c_roll=en)
            self.assertEqual(p["total_frames"],round(total*fps))
            self.assertTrue(1<=p["last_singer_frames"]<=p["singer_frames"])
            self.assertEqual(p["total_passes"],p["singer_passes"]+p["b_roll_passes"]+p["c_roll_passes"])
            if not b:self.assertEqual(p["b_roll_passes"],0)
            if not c or not en:self.assertEqual(p["c_roll_passes"],0)

    def test_broll_longer_than_aroll_is_supported(self):
        p=self.make(b_roll_seconds=30)
        self.assertEqual(p["b_roll_passes"],5)
        self.assertEqual(p["c_roll_passes"],12)

    def test_invalid_used_offsets_and_gaps_stop_at_preflight(self):
        for key in ["b_roll_offset","b_roll_gap","c_roll_offset","c_roll_gap"]:
            for value in [-1,float("nan"),float("inf")]:
                with self.subTest(key=key,value=value), self.assertRaisesRegex(ValueError,"Music video timing"):
                    self.make(**{key:value})

    def test_disabled_optional_settings_are_not_consumed(self):
        p=self.make(b_image_count=0,c_image_count=0,b_roll_seconds=-1,b_roll_offset=float("nan"),c_roll_seconds=-1)
        self.assertEqual(p["total_passes"],12)
        p=self.make(song_seconds=1)
        self.assertEqual(p["total_passes"],1)

    def test_zero_gap_is_valid_back_to_back(self):
        p=self.make(b_roll_offset=0,b_roll_gap=0)
        self.assertEqual(p["b_roll_passes"],80)

    def test_offsets_at_or_after_end_skip_lane(self):
        for offset in [240,300]:
            p=self.make(b_roll_offset=offset,c_roll_offset=offset)
            self.assertEqual((p['b_roll_passes'],p['c_roll_passes']),(0,0))

    def test_singer_length_does_not_change_optional_schedule(self):
        a=self.make(singer_seconds=3);b=self.make(singer_seconds=20)
        self.assertEqual(a['b_roll'],b['b_roll']);self.assertEqual(a['c_roll'],b['c_roll'])

    def test_invalid_required_lengths_and_rates(self):
        for name in ["song_seconds","singer_seconds","fps"]:
            for value in [0,-1,float("nan"),float("inf")]:
                with self.subTest(name=name,value=value), self.assertRaisesRegex(ValueError,"Music video timing"):
                    self.make(**{name:value})

    def test_no_subframe_or_zero_frame_job(self):
        for key in ["song_seconds","singer_seconds"]:
            with self.assertRaisesRegex(ValueError,"at least one video frame"):
                self.make(**{key:.000001})

    def test_bad_reference_counts(self):
        for key in ["b_image_count","c_image_count"]:
            for value in [-1,101,1.5,True]:
                with self.subTest(key=key,value=value), self.assertRaisesRegex(ValueError,"reference count"):
                    self.make(**{key:value})

    def test_repeated_plan_is_pure_and_deterministic(self):
        a=self.make();a["notes"].append("caller change")
        self.assertEqual(self.make(),self.make())
        self.assertNotIn("caller change",self.make()["notes"])

if __name__ == "__main__":
    unittest.main()
