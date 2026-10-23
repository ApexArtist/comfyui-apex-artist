"""B-roll source windows derived from the saved main-video cuts."""

from comfy_api.latest import io

from .apex_timeline import get_timeline_store


def v1_cut_windows(project, clip_seconds, before_cut):
    clips = sorted((clip for track in project["tracks"] if track["index"] == 0
                    for clip in track["clips"] if clip["duration"] > 0), key=lambda clip: clip["start"])
    if len(clips) < 2:
        return []
    fps = float(project["fps"])
    end_frame = round(max(clip["start"] + clip["duration"] for clip in clips) * fps)
    length = max(1, round(clip_seconds * fps))
    lead = round(before_cut * fps)
    windows = []
    for clip in clips[1:]:
        cut = round(clip["start"] * fps)
        start = max(0, cut - lead)
        stop = min(end_frame, start + length)
        if not start < cut < stop:
            raise ValueError("The B-roll duration and lead must leave picture on both sides of each V1 cut.")
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
            description="Read the actual V1 clip joins before generating B-roll. Use the same start for audio cropping and timeline placement.",
            inputs=[io.String.Input("project_name", default="Apex Timeline"),
                    io.String.Input("timeline_node_id", default="6841"),
                    io.Int.Input("cut_index", default=0, min=0),
                    io.Float.Input("clip_seconds", default=5.0, min=0.01, max=86400.0),
                    io.Float.Input("before_cut", default=2.0, min=0.0, max=86400.0)],
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
