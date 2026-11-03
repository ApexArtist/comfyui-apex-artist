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
        self.assertEqual(widgets, ['language','device','corrected_lyrics','model_name',
                                   'beam_size','condition_on_previous_text','initial_prompt',
                                   'download_if_missing'])
        self.assertEqual(schema['optional']['beam_size'][1]['default'], 5)
        self.assertFalse(schema['optional']['condition_on_previous_text'][1]['default'])
        self.assertTrue(schema['optional']['download_if_missing'][1]['default'])

    def test_local_model_path_cannot_escape(self):
        for name in ('../model', '..\\model', '/model', '.', '..', '.. ', '...'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                lyrics.model_directory(name)

    def test_whisper_download_missing_and_reuse_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def download(**kwargs):
                self.assertEqual(kwargs['repo_id'], 'openai/whisper-large-v3-turbo')
                self.assertFalse(kwargs['token'])
                self.assertEqual(set(kwargs['allow_patterns']), set(lyrics.DOWNLOAD_FILES))
                target = Path(kwargs['local_dir'])
                target.mkdir(parents=True)
                for name in lyrics.DOWNLOAD_FILES:
                    (target/name).write_text('{}' if name.endswith('.json') else 'test')
            with patch.object(lyrics.folder_paths, 'get_folder_paths', return_value=[str(root)]), \
                    patch.object(lyrics, 'snapshot_download', side_effect=download) as fetch:
                target = lyrics.model_directory(download_if_missing=True)
                self.assertEqual(target, root/lyrics.DEFAULT_MODEL)
                self.assertEqual(lyrics.model_directory(download_if_missing=True), target)
                self.assertEqual(fetch.call_count, 1)

    def test_whisper_offline_and_unknown_model_never_download(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(lyrics.folder_paths, 'get_folder_paths', return_value=[directory]), \
                patch.object(lyrics, 'snapshot_download') as fetch:
            for name, enabled in [(lyrics.DEFAULT_MODEL, False), ('custom-local-model', True)]:
                with self.subTest(name=name), self.assertRaises(FileNotFoundError):
                    lyrics.model_directory(name, enabled)
            fetch.assert_not_called()

    def test_whisper_repairs_partial_files_in_existing_model_root(self):
        with tempfile.TemporaryDirectory() as directory:
            roots = [Path(directory)/'first', Path(directory)/'second']
            target = roots[1]/lyrics.DEFAULT_MODEL
            target.mkdir(parents=True)
            (target/'model.safetensors').write_text('existing weights')
            def download(**kwargs):
                self.assertEqual(Path(kwargs['local_dir']), target)
                for name in lyrics.DOWNLOAD_FILES:
                    if name != 'model.safetensors':
                        (target/name).write_text('{}' if name.endswith('.json') else 'test')
            with patch.object(lyrics.folder_paths, 'get_folder_paths', return_value=list(map(str,roots))), \
                    patch.object(lyrics, 'snapshot_download', side_effect=download):
                self.assertEqual(lyrics.model_directory(download_if_missing=True), target)
                self.assertEqual((target/'model.safetensors').read_text(), 'existing weights')

    def test_whisper_incomplete_download_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(lyrics.folder_paths, 'get_folder_paths', return_value=[directory]), \
                patch.object(lyrics, 'snapshot_download'):
            with self.assertRaises(FileNotFoundError):
                lyrics.model_directory(download_if_missing=True)

    def test_whisper_download_failure_preserves_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/lyrics.DEFAULT_MODEL
            target.mkdir()
            weights = target/'model.safetensors'
            weights.write_text('existing partial installation')
            with patch.object(lyrics.folder_paths, 'get_folder_paths', return_value=[directory]), \
                    patch.object(lyrics, 'snapshot_download', side_effect=OSError('Network unavailable')):
                with self.assertRaisesRegex(OSError, 'Network unavailable'):
                    lyrics.model_directory(download_if_missing=True)
            self.assertEqual(weights.read_text(), 'existing partial installation')

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
