import copy
import importlib
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
package=types.ModuleType('cut_window_test')
package.__path__=[str(pathlib.Path(__file__).resolve().parents[1])]
sys.modules[package.__name__]=package
timeline=types.ModuleType('cut_window_test.apex_timeline')
timeline.get_timeline_store=lambda: None
sys.modules[timeline.__name__]=timeline
module=importlib.import_module('cut_window_test.apex_timeline_cut_window')

def project(starts, end=46, fps=24):
    return {'fps':fps,'tracks':[{'index':0,'clips':[
        {'start':a,'duration':b-a,'source_in':17} for a,b in zip(starts,starts[1:]+[end])]},
        {'index':1,'clips':[{'start':2,'duration':5}]}]}

class CutWindows(unittest.TestCase):
    def test_all_four_actual_joins_are_inside_windows(self):
        self.assertEqual(module.v1_cut_windows(project([0,10,20,30,40]),5,2),
                         [(8,5,10),(18,5,20),(28,5,30),(38,5,40)])

    def test_irregular_edited_main_clips_change_windows(self):
        self.assertEqual(module.v1_cut_windows(project([0,7.5,19.25,34.5]),5,2),
                         [(5.5,5,7.5),(17.25,5,19.25),(32.5,5,34.5)])

    def test_reloads_saved_v1_each_time(self):
        class Store:
            saved=project([0,10,20])
            def project_id(self,name,node):return 'test'
            def load(self,*args):return copy.deepcopy(self.saved)
        store=Store()
        module.get_timeline_store=lambda:store
        self.assertEqual(module.ApexTimelineCutWindow.execute('test','6841',1,5,2).result[:3],(18,5,20))
        store.saved=project([0,10,23.5])
        self.assertEqual(module.ApexTimelineCutWindow.execute('test','6841',1,5,2).result[:3],(21.5,5,23.5))

    def test_last_window_ends_at_main_picture_end(self):
        self.assertEqual(module.v1_cut_windows(project([0,10,20],end=21),5,2)[-1],(18,3,20))

    def test_does_not_guess_if_main_track_is_missing(self):
        self.assertEqual(module.v1_cut_windows(project([0]),5,2),[])
        with self.assertRaisesRegex(ValueError,'both sides'):
            module.v1_cut_windows(project([0,10]),5,0)

if __name__ == '__main__':
    unittest.main()
