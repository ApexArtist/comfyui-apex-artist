"""Audio loading, sample-accurate selection and gain with standard AUDIO outputs."""

import math
import os
from pathlib import Path

import folder_paths
import torch.nn.functional as F
from comfy_api.latest import io, ui
from comfy_extras.nodes_audio import load


NO_FILE = "(none — use audio input)"


def audio_path(filename):
    path = Path(folder_paths.get_annotated_filepath(filename))
    if not path.is_file() or not folder_paths.filter_files_content_types([path.name], ["audio", "video"]):
        raise ValueError("Choose an audio file in ComfyUI's input folder or connect AUDIO.")
    return path


def audio_info(audio):
    waveform, rate = audio["waveform"], audio["sample_rate"]
    samples = waveform.shape[-1]
    if samples == 0:
        raise ValueError("The audio contains no samples.")
    size = max(1, math.ceil(samples / 1200))
    peak = waveform.reshape(-1, samples).abs().amax(dim=0)
    peak = F.pad(peak, (0, (-samples) % size)).reshape(-1, size).amax(dim=1)
    return {"source_duration": samples / rate, "sample_rate": rate,
            "channels": waveform.shape[-2], "source_samples": samples,
            "peaks": peak.cpu().tolist()}


def file_info(filename):
    path = audio_path(filename)
    waveform, rate = load(str(path))
    stat = path.stat()
    return {**audio_info({"waveform": waveform, "sample_rate": rate}),
            "filename": filename, "version": f"{stat.st_mtime_ns}-{stat.st_size}"}


class ApexAudio(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        directory = Path(folder_paths.get_input_directory())
        files = [str(p.relative_to(directory)).replace(os.sep, "/") for p in directory.rglob("*") if p.is_file()]
        files = folder_paths.filter_files_content_types(files, ["audio", "video"])
        return io.Schema(
            node_id="ApexAudio", display_name="Apex Audio", category="Apex Artist/Audio",
            description="Load or connect audio, trim with waveform handles, adjust volume and read selection metadata. Connected AUDIO takes priority over the file.",
            inputs=[
                io.Combo.Input("audio_file", options=[NO_FILE, *sorted(files)], default=NO_FILE),
                io.Float.Input("start_seconds", default=0.0, min=0.0, max=86400.0, step=0.01),
                io.Float.Input("duration_seconds", default=0.0, min=0.0, max=86400.0, step=0.01,
                               tooltip="0 uses the remaining source. Outputs describe the trimmed selection."),
                io.Float.Input("volume_percent", default=100.0, min=0.0, max=200.0, step=1.0),
                io.Boolean.Input("preview", default=True,
                                 tooltip="Show a waveform and playable source preview after execution. Disable to skip preview encoding for connected AUDIO."),
                io.Audio.Input("audio", optional=True),
            ],
            outputs=[io.Audio.Output(display_name="AUDIO"), io.Float.Output(display_name="duration_seconds"),
                     io.Int.Output(display_name="sample_rate"), io.Int.Output(display_name="channels"),
                     io.Int.Output(display_name="samples")],
            is_output_node=True,
        )

    @classmethod
    def fingerprint_inputs(cls, audio_file=NO_FILE, audio=None, **kwargs):
        if audio is not None or audio_file == NO_FILE:
            return None
        path = audio_path(audio_file)
        stat = path.stat()
        return (str(path), stat.st_mtime_ns, stat.st_size)

    @classmethod
    def execute(cls, audio_file=NO_FILE, start_seconds=0.0, duration_seconds=0.0,
                volume_percent=100.0, preview=True, audio=None):
        from_file = audio is None
        if from_file:
            waveform, rate = load(str(audio_path(audio_file)))
            audio = {"waveform": waveform.unsqueeze(0), "sample_rate": rate}
        waveform, rate = audio["waveform"], audio["sample_rate"]
        total = waveform.shape[-1]
        start = max(0, min(total, round(start_seconds * rate)))
        end = total if duration_seconds == 0 else min(total, start + round(duration_seconds * rate))
        if end <= start:
            raise ValueError("The trim selection contains no audio. Move its start before the source ends.")
        selected = waveform[..., start:end]
        selected = selected.clone() if volume_percent == 100 else selected * (volume_percent / 100)
        output = {**audio, "waveform": selected}
        display = {}
        if preview:
            data = audio_info(audio)
            data["selection"] = {"start_seconds": start / rate, "duration_seconds": (end - start) / rate,
                                 "volume_percent": volume_percent}
            if from_file:
                data["filename"] = audio_file
                stat = audio_path(audio_file).stat()
                data["version"] = f"{stat.st_mtime_ns}-{stat.st_size}"
            else:
                data["media"] = ui.PreviewAudio({**audio, "waveform": waveform[:1]}).as_dict()["audio"][0]
            display["apex_audio"] = [data]
        return io.NodeOutput(output, (end - start) / rate, rate, waveform.shape[-2], end - start, ui=display)
