"""Frame-aligned independent track offsets for the music-video loop."""
import json
import math
import random
from functools import lru_cache
from comfy_api.latest import io
from .apex_loop_cache_keys import enable_uncached_music_loop_keys


def music_video_plan(song_seconds, singer_seconds, b_roll_seconds, b_roll_offset,
                     b_roll_gap, c_roll_seconds, c_roll_offset, c_roll_gap,
                     enable_c_roll, b_image_count, c_image_count, fps,
                     layout="layered", sequence_seed=0, opening_shot="singer", merge_short_tail=False):
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
    if layout not in ("layered", "sequential_shuffle"):
        raise ValueError("Music video timing: unknown layout.")
    if layout == "sequential_shuffle":
        if not isinstance(sequence_seed, int) or isinstance(sequence_seed, bool) or not 0 <= sequence_seed <= 2**53-1:
            raise ValueError("Music video timing: sequence seed must be a non-negative safe integer.")
        lengths = {"singer": singer_frames}
        if b_image_count:
            lengths["b_roll"] = frames(b_roll_seconds, "B-roll seconds", True)
        if enable_c_roll and c_image_count:
            lengths["c_roll"] = frames(c_roll_seconds, "C-roll seconds", True)
        if any(length > round(15*rate) for length in lengths.values()):
            raise ValueError("Music video timing: sequential H3 shots must be at most 15 seconds.")
        if total_frames > round(86400*rate):
            raise ValueError("Music video timing: sequential song length must be at most 24 hours.")
        rng = random.Random(sequence_seed)
        if opening_shot not in ("singer", "b_roll", "c_roll", "cutaway"):
            raise ValueError("Music video timing: opening shot must be singer, b_roll, c_roll or cutaway.")
        cutaways = [role for role in lengths if role != "singer"]
        notes = []
        if opening_shot == "cutaway":
            first = rng.choice(cutaways) if cutaways else "singer"
            if not cutaways:
                notes.append("No cutaway roles are enabled; opening on the singer.")
        elif opening_shot in lengths:
            first = opening_shot
        else:
            first = rng.choice(cutaways) if cutaways else "singer"
            notes.append(f"Requested {opening_shot} opening is disabled; opening on {first}.")
        shots, start, bag = [], 0, [first]
        if opening_shot != "singer":
            remaining = [role for role in lengths if role != first]
            rng.shuffle(remaining)
            bag.extend(remaining)
        # One of each enabled role per shuffled cycle after the chosen opening.
        # No singer footage is generated underneath a cutaway.
        while start < total_frames:
            if not bag:
                bag = list(lengths)
                rng.shuffle(bag)
                if len(bag) > 1 and bag[0] == shots[-1]["role"]:
                    bag[0], bag[1] = bag[1], bag[0]
            role = bag.pop(0)
            length = min(lengths[role], total_frames-start)
            shots.append({"role": role, "start_frame": start, "frames": length})
            start += length
        if merge_short_tail and len(shots) > 1 and shots[-1]["frames"] < round(rate):
            previous, tail = shots[-2:]
            if previous["frames"] + tail["frames"] <= round(15 * rate):
                previous["frames"] += tail["frames"]
                shots.pop()
                notes.append("Merged the sub-second ending into the previous shot.")
            elif previous["frames"] >= 2 * round(rate):
                extra = round(rate) - tail["frames"]
                previous["frames"] -= extra
                tail["start_frame"] -= extra
                tail["frames"] += extra
                notes.append("Extended the sub-second ending within the 15-second cap.")
        counts = {role: sum(s["role"] == role for s in shots) for role in ("singer", "b_roll", "c_roll")}
        singer_shots = [s for s in shots if s["role"] == "singer"]
        return {"layout": layout, "total_passes": len(shots), "singer_passes": counts["singer"],
                "b_roll_passes": counts["b_roll"], "c_roll_passes": counts["c_roll"],
                "song_seconds": total_frames/rate, "singer_seconds": singer_frames/rate,
                "total_frames": total_frames, "singer_frames": singer_frames,
                "last_singer_frames": singer_shots[-1]["frames"] if singer_shots else 0, "fps": rate,
                "sequence_seed": sequence_seed, "shots": shots, "notes": notes,
                "placement": "One continuous sequence; exact frame boundaries, no gaps or overlaps. Offsets and gaps are unused in this layout.",
                "limitations": ["The final shot may be shorter. H3 may generate padded frames internally and trim them. Timing does not predict model memory use or generation quality."]}
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
            description="Validate timing before generation. Layered mode keeps independent offsets/gaps. Sequential shuffle creates a contiguous edit with no overlaps; offsets and gaps are unused in that mode.",
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
                    io.Int.Input("fps",default=24,min=1,max=120),
                    io.Combo.Input("layout",options=["layered","sequential_shuffle"],default="layered",optional=True),
                    io.Int.Input("sequence_seed",default=0,min=0,max=2**53-1,optional=True),
                    io.Combo.Input("opening_shot",options=["singer","b_roll","c_roll","cutaway"],default="singer",optional=True,tooltip="Sequential mode only. Cutaway chooses an enabled B/C role using the sequence seed. Falls back to singer if neither is enabled. This does not detect vocal onset."),
                    io.Boolean.Input("merge_short_tail", default=False, optional=True,
                                     tooltip="Sequential mode only. Absorb a final shot under one second into the previous shot when it fits.")],
            outputs=[io.Int.Output("total_passes"),io.Int.Output("singer_passes"),
                     io.Int.Output("b_roll_passes"),io.Int.Output("c_roll_passes"),
                     io.Float.Output("song_seconds",display_name="frame-aligned song seconds"),
                     io.Float.Output("singer_seconds",display_name="frame-aligned singer seconds"),
                     io.String.Output("plan")],
            hidden=[io.Hidden.dynprompt,io.Hidden.execution_list,io.Hidden.unique_id])
    @classmethod
    def execute(cls,song_seconds,singer_seconds,b_roll_seconds,b_roll_offset,b_roll_gap,
                c_roll_seconds,c_roll_offset,c_roll_gap,enable_c_roll,b_image_count,c_image_count,fps,
                layout="layered",sequence_seed=0,opening_shot="singer",merge_short_tail=False):
        p=music_video_plan(song_seconds,singer_seconds,b_roll_seconds,b_roll_offset,b_roll_gap,
                           c_roll_seconds,c_roll_offset,c_roll_gap,enable_c_roll,b_image_count,c_image_count,fps,layout,sequence_seed,opening_shot,merge_short_tail)
        p['cache_policy']=enable_uncached_music_loop_keys(cls.hidden.dynprompt,cls.hidden.execution_list,cls.hidden.unique_id,require_uncached=True)
        return io.NodeOutput(*(p[k] for k in ["total_passes","singer_passes","b_roll_passes","c_roll_passes","song_seconds","singer_seconds"]),json.dumps(p,ensure_ascii=False))


@lru_cache(maxsize=4)
def _sequence_shots(plan_text):
    """Validate once per plan; keep only a bounded, immutable CPU schedule cache."""
    p = json.loads(plan_text)
    if not isinstance(p,dict) or p.get("layout") != "sequential_shuffle":
        raise ValueError("Apex Music Video Shot requires a sequential timing plan.")
    fps, total, shots = p.get("fps"), p.get("total_frames"), p.get("shots")
    if not isinstance(fps, (int,float)) or not math.isfinite(fps) or not 1 <= fps <= 120:
        raise ValueError("Apex Music Video Shot: invalid frame rate.")
    if type(total) is not int or total <= 0 or total > 86400*fps or not isinstance(shots,list) or not shots:
        raise ValueError("Apex Music Video Shot: invalid schedule.")
    start, checked = 0, []
    for s in shots:
        if not isinstance(s,dict):
            raise ValueError("Apex Music Video Shot: malformed shot entry.")
        role, at, length = s.get("role"), s.get("start_frame"), s.get("frames")
        if role not in ("singer","b_roll","c_roll") or type(at) is not int or at != start or type(length) is not int or not 0 < length <= round(15*fps):
            raise ValueError("Apex Music Video Shot: invalid, overlapping or discontinuous shot.")
        checked.append((role,at,length))
        start += length
    if start != total or len(checked) != p.get("total_passes"):
        raise ValueError("Apex Music Video Shot: schedule does not match the selected song.")
    return fps, tuple(checked)


class ApexMusicVideoShot(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(node_id="ApexMusicVideoShot", display_name="Apex Music Video Shot",
            category="Apex Artist/Video", description="Read one shot from a sequential music-video plan. Same source-audio and timeline start; no hidden overlap.",
            inputs=[io.String.Input("plan",multiline=True),io.Int.Input("index",default=0,min=0,max=2**31-1)],
            outputs=[io.Float.Output("start_seconds"),io.Float.Output("duration_seconds"),
                     io.Boolean.Output("is_cutaway"),io.Boolean.Output("is_b_roll"),
                     io.Boolean.Output("is_c_roll"),io.Boolean.Output("is_song_end"),io.Int.Output("frames")])

    @classmethod
    def execute(cls,plan,index):
        fps, shots = _sequence_shots(plan)
        if type(index) is not int or not 0 <= index < len(shots):
            raise ValueError("Apex Music Video Shot: index outside the schedule.")
        role, start, length = shots[index]
        return io.NodeOutput(start/fps,length/fps,role!="singer",role=="b_roll",role=="c_roll",index==len(shots)-1,length)



@lru_cache(maxsize=4)
def _cutaway_positions(plan):
    _, shots = _sequence_shots(plan)
    counts = {"b_roll": 0, "c_roll": 0}
    positions = []
    for role, _, _ in shots:
        if role in counts:
            counts[role] += 1
            positions.append((role, counts[role]))
        else:
            positions.append((role, 0))
    return tuple((role, ordinal, counts.get(role, 0)) for role, ordinal in positions)


def cutaway_brief(plan, index, direction, candid_shots, story_shots):
    positions = _cutaway_positions(plan)
    if type(index) is not int or not 0 <= index < len(positions):
        raise ValueError("Cutaway brief: shot index is outside the schedule.")
    role, ordinal, count = positions[index]
    if role == "singer":
        return direction
    lines = candid_shots if role == "b_roll" else story_shots
    briefs = [line.strip() for line in lines.splitlines() if line.strip()]
    if not briefs:
        return f"{direction} Assign a distinct visible action for this {role} shot {ordinal} of {count}."
    if count == 1:
        selected = 0
    else:
        selected = round((ordinal - 1) * (len(briefs) - 1) / (count - 1))
    assignment = briefs[selected]
    if count > len(briefs) and ordinal > 1 and selected == round((ordinal - 2) * (len(briefs) - 1) / (count - 1)):
        assignment = f"Show a different, immediate consequence of this beat: {assignment}"
    return f"Cutaway {ordinal} of {count}. Assigned shot: {assignment} Overall direction: {direction}"


class ApexMusicVideoCutawayBrief(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexMusicVideoCutawayBrief", display_name="Apex Music Video Cutaway Brief",
            category="Apex Artist/Video",
            description="Choose a role-specific action in timeline order. Enter one shot per line.",
            inputs=[
                io.String.Input("plan", multiline=True),
                io.Int.Input("index", default=0, min=0, max=2**31-1),
                io.String.Input("direction", multiline=True),
                io.String.Input("candid_shots", multiline=True),
                io.String.Input("story_shots", multiline=True),
            ],
            outputs=[io.String.Output("brief")],
        )

    @classmethod
    def execute(cls, plan, index, direction, candid_shots, story_shots):
        return io.NodeOutput(cutaway_brief(plan, index, direction, candid_shots, story_shots))
