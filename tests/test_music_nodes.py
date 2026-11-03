"""Run from the repository with ComfyUI's Python environment."""
import ast
import importlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1]))
package = types.ModuleType('apex_music_tests')
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
optional = importlib.import_module('apex_music_tests.apex_optional_images')
lyrics = importlib.import_module('apex_music_tests.apex_audio_lyrics')
cuts = importlib.import_module('apex_music_tests.apex_timeline_cut_window')
timeline = importlib.import_module('apex_music_tests.apex_timeline')
import torch


class MusicNodes(unittest.TestCase):
    def test_nodes_are_registered_and_described(self):
        tree = ast.parse((ROOT/'__init__.py').read_text(encoding='utf-8'))
        mapping = next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'NODE_CLASS_MAPPINGS' for t in n.targets))
        registered = {key.value for key in mapping.keys}
        described = {n['id'] for n in json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))['nodes']}
        self.assertEqual(registered, described)
        self.assertTrue({'ApexAudioLyrics', 'ApexOptionalImages', 'ApexTimelineCutWindow'} <= registered)

    def test_empty_and_growing_images(self):
        empty, count = optional.ApexOptionalImages.execute().result
        self.assertIsNone(empty)
        self.assertEqual(count, 0)
        image = torch.zeros(1, 8, 8, 3)
        batch, count = optional.ApexOptionalImages.execute({'image_0':image, 'image_1':image+1}).result
        self.assertEqual(count, 2)
        self.assertEqual(batch.shape, (2,8,8,3))
        self.assertEqual(float(batch[1].mean()), 1)

    def test_lyrics_override_does_not_load_model(self):
        with patch.object(lyrics, 'model_directory', side_effect=AssertionError('Model must not load')):
            text, document = lyrics.ApexAudioLyrics.execute(None, corrected_lyrics='  Exact reviewed lyrics.  ').result
        self.assertEqual(text, 'Exact reviewed lyrics.')
        self.assertEqual(json.loads(document)['source'], 'user_corrected')

    def test_lyrics_controls_keep_old_widget_positions(self):
        schema = lyrics.ApexAudioLyrics.INPUT_TYPES()
        widgets = [k for group in ('required','optional') for k in schema[group] if k != 'audio']
        self.assertEqual(widgets[:3], ['language','device','corrected_lyrics'])
        self.assertEqual(schema['optional']['beam_size'][1]['default'], 5)
        self.assertFalse(schema['optional']['condition_on_previous_text'][1]['default'])

    def test_local_model_path_cannot_escape(self):
        for name in ('../model', '..\\model', '/model', '.', '..', '.. ', '...'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                lyrics.model_directory(name)

    def test_windows_follow_actual_v1_joins(self):
        project = {'fps':24,'tracks':[{'index':0,'clips':[
            {'start':0,'duration':10}, {'start':10,'duration':7.5}, {'start':17.5,'duration':8}]}]}
        self.assertEqual(cuts.v1_cut_windows(project,3,2),[(8,3,10),(15.5,3,17.5)])
        project['tracks'][0]['clips'] = project['tracks'][0]['clips'][:1]
        self.assertEqual(cuts.v1_cut_windows(project,3,2),[])

    def test_editor_snapshot_opens_without_overwriting_source(self):
        with tempfile.TemporaryDirectory() as directory:
            store = timeline.TimelineStore(Path(directory)/'timelines')
            project = store._new_project(store.project_id('Original','1'),'Original','Multi',60)
            project['fps'] = 24
            store.save(project)
            original = (store.project_dir(project['project_id'])/'project.json').read_bytes()
            snapshot = store.project_snapshot(project['project_id'])
            opened = store.open_snapshot(snapshot,'2')
            self.assertNotEqual(opened['project_id'],project['project_id'])
            self.assertEqual(opened['tracks'],project['tracks'])
            self.assertEqual((store.project_dir(project['project_id'])/'project.json').read_bytes(),original)


if __name__ == '__main__':
    unittest.main()
