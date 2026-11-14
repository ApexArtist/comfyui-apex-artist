import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]))
spec=importlib.util.spec_from_file_location('audio_filename_test',ROOT/'apex_audio.py')
audio=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)
import torch


class AudioFilenameTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.root=Path(self.directory.name)
        self.addCleanup(self.directory.cleanup)
        for name in ['First song.wav','Second song.wav','Band.song.mix.wav']:
            with wave.open(str(self.root/name),'wb') as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(16000)
                stream.writeframes(struct.pack('<h',8192)*16000)
        self.resolve=patch.object(audio.folder_paths,'get_annotated_filepath',side_effect=lambda name:str(self.root/name))
        self.resolve.start()
        self.addCleanup(self.resolve.stop)

    def test_filename_is_appended_after_existing_outputs(self):
        result=audio.ApexAudio.execute(audio_file='First song.wav',preview=False).result
        self.assertEqual(len(result),6)
        self.assertEqual(result[1:],(1.0,16000,1,16000,'First song'))
        self.assertEqual(result[0]['waveform'].shape,(1,1,16000))
        self.assertEqual([x.display_name for x in audio.ApexAudio.GET_SCHEMA().outputs],
                         ['AUDIO','duration_seconds','sample_rate','channels','samples','filename'])

    def test_name_stays_stable_across_queues_trim_gain_and_preview(self):
        for preview in [False,True]:
            a=audio.ApexAudio.execute(audio_file='First song.wav',preview=preview).result
            b=audio.ApexAudio.execute(audio_file='First song.wav',start_seconds=.2,duration_seconds=.3,
                                     volume_percent=50,preview=preview).result
            self.assertEqual(a[5],b[5])
            self.assertEqual(b[1:5],(.3,16000,1,4800))
            torch.testing.assert_close(b[0]['waveform'],a[0]['waveform'][...,3200:8000]*.5)

    def test_changing_file_changes_name(self):
        first=audio.ApexAudio.execute(audio_file='First song.wav',preview=False).result[5]
        second=audio.ApexAudio.execute(audio_file='Second song.wav',preview=False).result[5]
        self.assertEqual((first,second),('First song','Second song'))

    def test_only_last_extension_is_removed(self):
        self.assertEqual(audio.ApexAudio.execute(audio_file='Band.song.mix.wav',preview=False).result[5],'Band.song.mix')

    def test_connected_audio_does_not_borrow_unrelated_selected_filename(self):
        connected={'waveform':torch.zeros((1,1,1600)),'sample_rate':16000}
        with patch.object(audio,'audio_path',side_effect=AssertionError('Connected AUDIO has priority')):
            result=audio.ApexAudio.execute(audio_file='Unrelated.wav',audio=connected,preview=False).result
        self.assertEqual(result[5],'')
        self.assertEqual(result[1:5],(.1,16000,1,1600))


if __name__=='__main__':
    unittest.main()
