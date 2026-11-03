"""Small real-media regression for cut timestamps and muted exports."""
import importlib,shutil,sys,tempfile,types,unittest
from pathlib import Path
import av,torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]))
package=types.ModuleType('apex_timestamp_tests');package.__path__=[str(ROOT)];sys.modules[package.__name__]=package
timeline=importlib.import_module('apex_timestamp_tests.apex_timeline')

@unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg is required for timeline exports')
class TimelineTimestamps(unittest.TestCase):
    def test_trimmed_cuts_have_uniform_pts_and_aligned_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);store=timeline.TimelineStore(root/'timelines')
            project={'project_id':'test','fps':24}
            store.project_dir('test').mkdir(parents=True)
            videos=[]
            for index,color in enumerate(('red','blue')):
                source=root/f'{index}.mp4'
                timeline._ffmpeg(['-f','lavfi','-i',f'color={color}:s=64x64:r=24','-f','lavfi','-i','sine=frequency=440:sample_rate=48000',
                    '-t','1','-c:v','libx264','-video_track_timescale',str(12288 if index else 24000),'-c:a','aac',str(source)])
                videos.append(timeline.InputImpl.VideoFromFile(str(source)).as_trimmed(.25,.5))
            audio={'waveform':torch.zeros((1,1,48000)),'sample_rate':48000}
            for sound in (audio,None):
                result=timeline.assemble_timeline(videos,sound,project,store)
                with av.open(result.get_stream_source()) as movie:
                    frames=list(movie.decode(video=0))
                self.assertEqual(len(frames),24)
                self.assertTrue(all(abs(float(f.pts*f.time_base)-i/24)<1e-6 for i,f in enumerate(frames)))
                self.assertGreater(frames[0].to_ndarray(format='rgb24')[...,0].mean(),200)
                self.assertGreater(frames[12].to_ndarray(format='rgb24')[...,2].mean(),200)
                with av.open(result.get_stream_source()) as movie:
                    self.assertAlmostEqual(float(movie.streams.video[0].duration*movie.streams.video[0].time_base),1,places=5)
                    self.assertEqual(bool(movie.streams.audio),sound is not None)
                    if sound is not None:
                        self.assertAlmostEqual(float(movie.streams.audio[0].duration*movie.streams.audio[0].time_base),1,places=3)

if __name__=='__main__':unittest.main()
