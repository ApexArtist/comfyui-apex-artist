"""Frame-aligned independent track offsets for the music-video loop."""
import json
import math
from comfy_api.latest import io
from .apex_loop_cache_keys import enable_uncached_music_loop_keys


def music_video_plan(song_seconds, singer_seconds, b_roll_seconds, b_roll_offset,
                     b_roll_gap, c_roll_seconds, c_roll_offset, c_roll_gap,
                     enable_c_roll, b_image_count, c_image_count, fps):
    def number(value, name, positive=False):
        result=float(value)
        if not math.isfinite(result) or result<0 or (positive and result==0):
            condition="greater than zero" if positive else "non-negative"
            raise ValueError(f"Music video timing: {name} must be finite and {condition}.")
        return result
    rate=number(fps,"frame rate",True)
    if not 1<=rate<=120:
        raise ValueError("Music video timing: frame rate must be between 1 and 120 fps, matching native Create Video.")
    def frames(value,name,positive=False):
        value=number(value,name,positive)
        product=value*rate
        if not math.isfinite(product):
            raise ValueError(f"Music video timing: {name} exceeds the supported numeric range.")
        result=round(product)
        if positive and result<1:
            raise ValueError(f"Music video timing: {name} must contain at least one video frame.")
        return result
    total_frames=frames(song_seconds,"selected song seconds",True)
    singer_frames=frames(singer_seconds,"singer clip seconds",True)
    for count,name in [(b_image_count,"B-roll"),(c_image_count,"C-roll")]:
        if not isinstance(count,int) or isinstance(count,bool) or not 0<=count<=100:
            raise ValueError(f"Music video timing: {name} reference count must be an integer from 0 to 100.")
    notes=[]
    def lane(enabled,seconds,offset,gap,name,candid=False):
        if not enabled:return {"count":0}
        seconds=number(seconds,name+" seconds",True)
        if candid:
            limited=min(5.0,max(3.0,seconds))
            if limited!=seconds:notes.append("C-roll duration kept within the workflow's 3-5 second range.")
            seconds=limited
        length=frames(seconds,name+" seconds",True)
        start=frames(offset,name+" start offset")
        spacing=frames(gap,name+" gap")
        count=0 if start>=total_frames else (total_frames-1-start)//(length+spacing)+1
        if not count:notes.append(name+" skipped: its first offset is at or beyond the selected song end.")
        return {"count":count,"duration_frames":length,"offset_frames":start,"gap_frames":spacing}
    b=lane(bool(b_image_count),b_roll_seconds,b_roll_offset,b_roll_gap,"B-roll")
    c=lane(bool(enable_c_roll and c_image_count),c_roll_seconds,c_roll_offset,c_roll_gap,"C-roll",True)
    main=(total_frames+singer_frames-1)//singer_frames
    return {"total_passes":main+b["count"]+c["count"],"singer_passes":main,
            "b_roll_passes":b["count"],"c_roll_passes":c["count"],
            "song_seconds":total_frames/rate,"singer_seconds":singer_frames/rate,
            "total_frames":total_frames,"singer_frames":singer_frames,
            "last_singer_frames":total_frames-(main-1)*singer_frames,
            "fps":rate,"b_roll":b,"c_roll":c,"notes":notes,
            "placement":"Each optional track uses its own song-relative offset plus index times (its own duration plus gap); final windows are trimmed at the song end.",
            "limitations":["Tracks may overlap; the editor's upper track is visible. Model VRAM use and third-party failures are not predicted by timing validation."]}


class ApexMusicVideoPlan(io.ComfyNode):
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        # Re-register this prompt's scoped loop policy even when timing matches
        # a previous queue. Shared preparation nodes retain their native cache.
        return float("nan")

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexMusicVideoPlan",display_name="Apex Music Video Plan",
            category="Apex Artist/Video",
            description="Validate timing before generation. B-roll and C-roll use independent song-relative start offsets and gaps, without reading singer cuts or saved timelines.",
            inputs=[io.Float.Input("song_seconds",default=180.0,min=0.0,max=86400.0),
                    io.Float.Input("singer_seconds",default=20.0,min=0.0,max=86400.0),
                    io.Float.Input("b_roll_seconds",default=3.0,min=0.0,max=86400.0),
                    io.Float.Input("b_roll_offset",default=8.0,min=0.0,max=86400.0),
                    io.Float.Input("b_roll_gap",default=17.0,min=0.0,max=86400.0),
                    io.Float.Input("c_roll_seconds",default=3.0,min=0.0,max=86400.0),
                    io.Float.Input("c_roll_offset",default=14.0,min=0.0,max=86400.0),
                    io.Float.Input("c_roll_gap",default=17.0,min=0.0,max=86400.0),
                    io.Boolean.Input("enable_c_roll",default=True),
                    io.Int.Input("b_image_count",default=0,min=0,max=100),
                    io.Int.Input("c_image_count",default=0,min=0,max=100),
                    io.Int.Input("fps",default=24,min=1,max=120)],
            outputs=[io.Int.Output("total_passes"),io.Int.Output("singer_passes"),
                     io.Int.Output("b_roll_passes"),io.Int.Output("c_roll_passes"),
                     io.Float.Output("song_seconds",display_name="frame-aligned song seconds"),
                     io.Float.Output("singer_seconds",display_name="frame-aligned singer seconds"),
                     io.String.Output("plan")],
            hidden=[io.Hidden.dynprompt,io.Hidden.execution_list,io.Hidden.unique_id])
    @classmethod
    def execute(cls,song_seconds,singer_seconds,b_roll_seconds,b_roll_offset,b_roll_gap,
                c_roll_seconds,c_roll_offset,c_roll_gap,enable_c_roll,b_image_count,c_image_count,fps):
        p=music_video_plan(song_seconds,singer_seconds,b_roll_seconds,b_roll_offset,b_roll_gap,
                           c_roll_seconds,c_roll_offset,c_roll_gap,enable_c_roll,b_image_count,c_image_count,fps)
        p['cache_policy']=enable_uncached_music_loop_keys(cls.hidden.dynprompt,cls.hidden.execution_list,cls.hidden.unique_id,require_uncached=True)
        return io.NodeOutput(*(p[k] for k in ["total_passes","singer_passes","b_roll_passes","c_roll_passes","song_seconds","singer_seconds"]),json.dumps(p,ensure_ascii=False))
