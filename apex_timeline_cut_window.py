"""B-roll source windows derived from the saved main-video cuts."""

import heapq
import math

from comfy_api.latest import io

from .apex_timeline import get_timeline_store


def v1_cut_windows(project, clip_seconds, before_cut):
    fps = float(project["fps"])
    seconds, before = float(clip_seconds), float(before_cut)
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("V1 frame rate must be finite and greater than zero.")
    if not math.isfinite(seconds) or seconds <= 0 or not math.isfinite(before) or before < 0:
        raise ValueError("B-roll seconds must be finite and positive; lead seconds must be finite and non-negative.")
    if not math.isfinite(seconds * fps) or not math.isfinite(before * fps):
        raise ValueError("B-roll timing exceeds the supported numeric range.")
    length, lead = round(seconds * fps), round(before * fps)
    if not 0 < lead < length:
        raise ValueError(
            f"B-roll {seconds:g}s with lead {before:g}s at {fps:g} fps becomes "
            f"{length} frames with {lead} frames before the cut. "
            "The B-roll duration and lead must leave picture on both sides of each V1 cut "
            "(at least one frame on each side). For example, use 3s B-roll and a 2s lead."
        )

    # Match the editor/export's frame rounding and last-placement-wins order.
    # A sub-frame tail has no picture and must not create a phantom cut.
    events = {}
    order = 0
    for track in project["tracks"]:
        if int(track["index"]) != 0:
            continue
        for clip in track["clips"]:
            start, duration = float(clip["start"]), float(clip["duration"])
            if not math.isfinite(start) or not math.isfinite(duration) or start < 0 or duration < 0:
                raise ValueError("V1 placements must have finite, non-negative start and duration values.")
            if not math.isfinite(start * fps) or not math.isfinite((start + duration) * fps):
                raise ValueError("V1 placement exceeds the supported numeric range.")
            a, b = round(start * fps), round((start + duration) * fps)
            if b <= a:
                continue
            events.setdefault(a, [[], []])[0].append(order)
            events.setdefault(b, [[], []])[1].append(order)
            order += 1
    if not events:
        return []
    boundaries = sorted(events)
    active, stack, cuts = set(), [], []
    previous = None
    for frame in boundaries:
        added, removed = events[frame]
        active.difference_update(removed)
        for item in added:
            active.add(item)
            heapq.heappush(stack, -item)
        while stack and -stack[0] not in active:
            heapq.heappop(stack)
        visible = -stack[0] if stack else None
        if previous is not None and visible is not None and visible != previous:
            cuts.append(frame)
        previous = visible

    end_frame = boundaries[-1]
    windows = []
    for cut in cuts:
        start = max(0, cut - lead)
        stop = min(end_frame, start + length)
        if not start < cut < stop:
            raise ValueError(f"V1 cut at {cut/fps:g}s has no usable picture on both sides after frame alignment.")
        windows.append((start / fps, (stop - start) / fps, cut / fps))
    return windows


class ApexTimelineCutWindow(io.ComfyNode):
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        return float("nan")

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexTimelineCutWindow", display_name="Apex V1 Cut Window",
            category="Apex Artist/Video",
            description="Read visible V1 joins on the saved frame grid, accounting for overlaps and gaps. Upper tracks do not affect the joins. Use the same start for audio cropping and timeline placement.",
            inputs=[io.String.Input("project_name", default="Apex Timeline"),
                    io.String.Input("timeline_node_id", default="6841"),
                    io.Int.Input("cut_index", default=0, min=0),
                    io.Float.Input("clip_seconds", default=5.0, min=0.01, max=86400.0, tooltip="B-roll may span multiple V1 clips; the window is trimmed at the end of V1."),
                    io.Float.Input("before_cut", default=2.0, min=0.0, max=86400.0, tooltip="Time before the V1 cut. Must leave at least one frame before and after the cut within the B-roll duration.")],
            outputs=[io.Float.Output("start", display_name="source and placement start"),
                     io.Float.Output("duration"), io.Float.Output("cut", display_name="V1 cut"),
                     io.Int.Output("cut_count", display_name="V1 join count")],
        )

    @classmethod
    def execute(cls, project_name, timeline_node_id, cut_index, clip_seconds, before_cut):
        store = get_timeline_store()
        project = store.load(store.project_id(project_name, timeline_node_id), project_name)
        windows = v1_cut_windows(project, clip_seconds, before_cut)
        if not 0 <= cut_index < len(windows):
            raise ValueError(f"V1 has {len(windows)} joins; B-roll requested join {cut_index + 1}. Generate the main singer clips first.")
        start, duration, cut = windows[cut_index]
        return io.NodeOutput(start, duration, cut, len(windows))
