"""Disk-backed, autogrowing video timeline nodes for ComfyUI."""

from __future__ import annotations

import hashlib
import copy
import json
import math
import os
import re
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import av
import folder_paths
import torch
from comfy.audio import resample
from comfy_api.latest import InputImpl, Types, io
from comfy_execution.graph_utils import is_link
from comfy_extras.nodes_audio import load as load_audio
from .apex_timeline_fades import clamp_fades, clear_auto_fades, join_fades, available_start, fade_spans, fade_value, render_fade_span


TIMELINE_TYPE = io.Custom("APEX_TIMELINE")
PROJECT_VERSION = 1
MAX_TRACKS = 16
AUDIO_SUFFIXES = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: Any, fallback: str) -> str:
    value = _SAFE_NAME.sub("-", str(value or "").strip()).strip("-._")
    return value[:80] or fallback


def _scalar(value: Any, default: Any = None) -> Any:
    """Normalize values when a V3 node is registered through the V1 loader."""
    if isinstance(value, list):
        return value[0] if value else default
    return default if value is None else value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _ffmpeg(arguments: list) -> None:
    executable = shutil.which("ffmpeg")
    if not executable:
        raise ValueError("Install FFmpeg on PATH to import videos or render timeline gaps.")
    result = subprocess.run([executable, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *arguments],
                            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if result.returncode:
        raise ValueError(result.stderr[-2000:] or "FFmpeg could not process this video.")


def write_audio(path, audio):
    temporary = path.with_name(uuid.uuid4().hex + ".wav")
    samples = audio["waveform"][0].detach().cpu().float().contiguous().numpy()
    rate = int(audio["sample_rate"])
    try:
        with av.open(str(temporary), "w", format="wav") as container:
            stream = container.add_stream("pcm_f32le", rate=rate)
            stream.layout = "mono" if samples.shape[0] == 1 else f"{samples.shape[0]}c"
            frame = av.AudioFrame.from_ndarray(samples, format="fltp", layout=stream.layout)
            frame.sample_rate = rate
            for packet in stream.encode(frame): container.mux(packet)
            for packet in stream.encode(None): container.mux(packet)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


class TimelineStore:
    """Revisioned project storage under the configured ComfyUI output directory."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else Path(folder_paths.get_output_directory()) / "Apex" / "timelines"
        self._legacy_root = None if root is not None else Path(folder_paths.get_user_directory()) / "apex_artist" / "timelines"
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks_guard = threading.Lock()
        self._waveform_lock = threading.Lock()
        self._project_locks: dict[str, threading.RLock] = {}

    def project_lock(self, project_id: str) -> threading.RLock:
        """Serialize one project without blocking unrelated timelines."""
        safe_id = _slug(project_id, "timeline")
        with self._locks_guard:
            return self._project_locks.setdefault(safe_id, threading.RLock())

    def project_id(self, project_name: str, node_id: Any) -> str:
        return f"{_slug(project_name, 'timeline')}__node-{_slug(node_id, 'unknown')}"

    def project_dir(self, project_id: str) -> Path:
        path = (self.root / _slug(project_id, "timeline")).resolve()
        root = self.root.resolve()
        if root != path and root not in path.parents:
            raise ValueError("Timeline project path is outside the storage root.")
        if self._legacy_root is not None:
            with self.project_lock(project_id):
                legacy = (self._legacy_root / _slug(project_id, "timeline")).resolve()
                legacy_root = self._legacy_root.resolve()
                if legacy_root not in legacy.parents:
                    raise ValueError("Legacy timeline project path is outside the storage root.")
                if not path.exists() and (legacy / "project.json").is_file():
                    temporary = root / f".migrate-{uuid.uuid4().hex}"
                    shutil.copytree(legacy, temporary)
                    os.replace(temporary, path)
        return path

    def _new_project(self, project_id: str, project_name: str, mode: str, target_duration: float) -> dict:
        now = _utc_now()
        return {
            "version": PROJECT_VERSION,
            "project_id": project_id,
            "name": project_name.strip() or "Apex Timeline",
            "mode": mode,
            "target_duration": float(target_duration),
            "revision": 0,
            "created_at": now,
            "updated_at": now,
            "assets": {},
            "tracks": [],
            "audio_tracks": [],
            "fps": 24.0,
            "bin": [],
            "overflow_by_track": {},
        }

    def load(self, project_id: str, project_name: str = "Apex Timeline", mode: str = "Single",
             target_duration: float = 180.0) -> dict:
        path = self.project_dir(project_id) / "project.json"
        with self.project_lock(project_id):
            if not path.exists():
                return self._new_project(project_id, project_name, mode, target_duration)
            with path.open("r", encoding="utf-8") as handle:
                project = json.load(handle)
            if project.get("project_id") != project_id:
                raise ValueError("Timeline project identity does not match its directory.")
            self.initialize_audio(project)
            project.setdefault("fps", 24.0)
            return project

    def save(self, project: dict) -> dict:
        project_dir = self.project_dir(project["project_id"])
        project_dir.mkdir(parents=True, exist_ok=True)
        with self.project_lock(project["project_id"]):
            project["revision"] = int(project.get("revision", 0)) + 1
            project["updated_at"] = _utc_now()
            temporary = project_dir / f"project.{uuid.uuid4().hex}.tmp"
            destination = project_dir / "project.json"
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                json.dump(project, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        return project

    @staticmethod
    def ensure_track(project: dict, track_index: int) -> dict:
        project["removed_tracks"] = [index for index in project.get("removed_tracks", []) if index != track_index]
        for track in project["tracks"]:
            if int(track["index"]) == track_index:
                return track
        track = {"id": f"video-{track_index + 1}", "index": track_index,
                 "name": f"Video {track_index + 1}", "clips": []}
        project["tracks"].append(track)
        project["tracks"].sort(key=lambda item: int(item["index"]))
        return track

    @staticmethod
    def track_end(track: dict) -> float:
        return max((float(clip["start"]) + float(clip["duration"]) for clip in track["clips"]), default=0.0)

    @classmethod
    def duration(cls, project: dict) -> float:
        return max((cls.track_end(track) for track in project["tracks"] + project.get("audio_tracks", [])), default=0.0)

    @staticmethod
    def clip_count(project: dict) -> int:
        return sum(len(track["clips"]) for track in project["tracks"])

    def capture_video(self, project: dict, track_index: int, video: Any, capture_policy: str,
                      target_duration: float, overflow: str, placement_start: float = -1,
                      capture_clip_audio: bool = True, placement_offset: float = 0.0) -> tuple[dict | None, str]:
        assets_dir = self.project_dir(project["project_id"]) / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        temp_path = assets_dir / f"capture-{uuid.uuid4().hex}.mp4"
        try:
            video.save_to(temp_path, format=Types.VideoContainer.MP4, codec=Types.VideoCodec.H264)
            fingerprint = _sha256(temp_path)
            duration = max(0.0, float(video.get_duration()))
            width, height = video.get_dimensions()
            frame_rate = float(video.get_frame_rate())
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        track = self.ensure_track(project, track_index)
        duplicate_asset_ids = {clip["asset_id"] for clip in track["clips"]}
        duplicate_asset_ids.update(project.get("overflow_by_track", {}).get(str(track_index), []))
        if capture_policy == "New Results Only" and any(
            project["assets"].get(asset_id, {}).get("fingerprint") == fingerprint
            for asset_id in duplicate_asset_ids
        ):
            temp_path.unlink(missing_ok=True)
            return None, "duplicate"

        asset_id = fingerprint
        asset = project["assets"].get(asset_id)
        if asset is None:
            filename = f"{fingerprint}.mp4"
            destination = assets_dir / filename
            if destination.exists():
                temp_path.unlink(missing_ok=True)
            else:
                os.replace(temp_path, destination)
            asset = {"id": asset_id, "filename": filename, "fingerprint": fingerprint,
                     "duration": duration, "width": int(width), "height": int(height),
                     "frame_rate": frame_rate, "created_at": _utc_now()}
            project["assets"][asset_id] = asset
        else:
            destination = assets_dir / asset["filename"]
            if destination.is_file():
                temp_path.unlink(missing_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(temp_path, destination)
                asset.update(duration=duration, width=int(width), height=int(height), frame_rate=frame_rate)

        start = (self.track_end(track) if placement_start < 0 else float(placement_start)) + placement_offset
        if target_duration > 0 and start + duration > target_duration + 1e-6:
            changed = False
            if asset_id not in project["bin"]:
                project["bin"].append(asset_id)
                changed = True
            track_overflow = project.setdefault("overflow_by_track", {}).setdefault(str(track_index), [])
            if asset_id not in track_overflow:
                track_overflow.append(asset_id)
                changed = True
            if not changed:
                return None, "unchanged_full"
            return None, "full" if overflow == "Stop" else "bin"

        clip = {"id": uuid.uuid4().hex, "asset_id": asset_id, "track_index": track_index,
                "start": start, "source_in": 0.0, "duration": duration, "created_at": _utc_now()}
        if placement_start >= 0 or placement_offset > 0:
            track["sparse"] = True
        track["clips"].append(clip)
        if capture_clip_audio:
            self.link_clip_audio(project, clip)
        project.pop("undo", None)
        project.pop("redo", None)
        return clip, "appended"

    @staticmethod
    def remember_edit(project: dict) -> None:
        project.setdefault("undo", []).append(copy.deepcopy({"tracks": project["tracks"], "bin": project["bin"],
                                                           "removed_tracks": project.get("removed_tracks", []), "audio_tracks": project.get("audio_tracks", []),
                                                           "fps":project.get("fps",24.0), "input_audio_fingerprint":project.get("input_audio_fingerprint"), "input_audio_clip":project.get("input_audio_clip")}))
        project["undo"] = project["undo"][-50:]
        project["redo"] = []

    def restore_edit(self, project_id: str, operation: str, revision=None) -> dict:
        with self.project_lock(project_id):
            project = self.load(project_id)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            if operation not in ("undo", "redo"):
                raise ValueError("Unknown history operation.")
            history = project.setdefault(operation, [])
            if not history:
                return project
            restored = history.pop()
            current = copy.deepcopy({"tracks": project["tracks"], "bin": project["bin"],
                                     "removed_tracks": project.get("removed_tracks", []), "audio_tracks": project.get("audio_tracks", []),
                                     "fps":project.get("fps",24.0), "input_audio_fingerprint":project.get("input_audio_fingerprint"), "input_audio_clip":project.get("input_audio_clip")})
            if "assets" in restored:
                current["assets"] = copy.deepcopy(project["assets"])
                restored["assets"] = {**project["assets"], **restored["assets"]}
            if "audio_tracks" not in restored:
                legacy = {**project, "tracks":restored["tracks"], "assets":restored.get("assets", project["assets"])}
                legacy.pop("audio_tracks", None)
                self.initialize_audio(legacy)
                for track in project["audio_tracks"]:
                    independent = [copy.deepcopy(clip) for clip in track["clips"] if not clip.get("link_id")]
                    if independent:
                        target = self.audio_track(legacy, track["index"])
                        target["clips"].extend(independent)
                        target.update(muted=track.get("muted", False), volume=track.get("volume", 1))
                restored["audio_tracks"] = legacy["audio_tracks"]
            project.setdefault("redo" if operation == "undo" else "undo", []).append(current)
            project.update(removed_tracks=restored.get("removed_tracks", []))
            project.update(restored)
            return self.save(project)

    def edit_track(self, project_id: str, track_index: int, operation: str, revision=None,
                   project_name: str = "Apex Timeline") -> dict:
        with self.project_lock(project_id):
            project = self.load(project_id, project_name)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            if not 0 <= track_index < MAX_TRACKS or operation not in ("add", "delete"):
                raise ValueError("Invalid track or operation.")
            if operation == "delete" and track_index == 0:
                raise ValueError("V1 is the permanent base track and cannot be deleted.")
            self.remember_edit(project)
            if operation == "delete":
                groups = {clip.get("link_id") for track in project["tracks"] if track["index"] == track_index for clip in track["clips"]} - {None}
                for track in project["audio_tracks"]:
                    track["clips"] = [clip for clip in track["clips"] if clip.get("link_id") not in groups]
                project["tracks"] = [track for track in project["tracks"] if track["index"] != track_index]
                project["removed_tracks"] = sorted(set(project.get("removed_tracks", [])) | {track_index})
            else:
                self.ensure_track(project, track_index)
            return self.save(project)

    def place_asset(self, project_id: str, asset_id: str, track_index: int, start: float, revision=None, kind="video", placement_options=None) -> dict:
        with self.project_lock(project_id):
            project = self.load(project_id)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            asset = project["assets"][asset_id]
            if not 0 <= track_index < MAX_TRACKS or not math.isfinite(start) or start < 0:
                raise ValueError("Invalid clip position or track.")
            if asset.get("kind") == "audio": kind = "audio"
            if kind == "audio" and not asset.get("has_audio", False): raise ValueError("This source has no audio stream.")
            self.remember_edit(project)
            track = self.audio_track(project, track_index) if kind == "audio" else self.ensure_track(project, track_index)
            track["sparse"] = True
            clip = {"id": uuid.uuid4().hex, "asset_id": asset_id, "track_index": track_index,
                "kind":kind, "start": start, "source_in": 0.0, "duration": asset["duration"], "created_at": _utc_now()}
            self.place_clip(project, track, clip, placement_options)
            track["clips"].sort(key=lambda item: item["start"])
            return self.save(project)

    def place_clip(self, project, track, clip, options=None):
        options = options or {}
        if options.get("snap"):
            clip["start"] = available_start(track, clip["start"], clip["duration"])
        track["clips"].append(clip)
        if clip["kind"] == "video": self.link_clip_audio(project, clip)
        if options.get("auto_fade"):
            for lane in project["tracks"] + project["audio_tracks"]:
                for item in lane["clips"]:
                    if item is clip or clip.get("link_id") and item.get("link_id") == clip["link_id"]:
                        join_fades(lane, item, float(project.get("fps", 24)))

    @staticmethod
    def source_metadata(source: Path) -> dict:
        source = source.expanduser()
        if not source.is_absolute():
            raise ValueError("Choose the original file using its full path.")
        source = source.resolve(strict=True)
        if not source.is_file() or source.suffix.lower() not in VIDEO_SUFFIXES | AUDIO_SUFFIXES:
            raise ValueError("Choose a supported video or audio file.")
        try:
            with av.open(str(source)) as container:
                has_audio = bool(container.streams.audio)
                is_video = bool(container.streams.video)
            if is_video:
                video = InputImpl.VideoFromFile(str(source))
                width, height = video.get_dimensions()
                duration, fps = float(video.get_duration()), float(video.get_frame_rate())
            else:
                samples, rate = load_audio(str(source))
                width, height, fps = 0, 0, 24.0
                duration = samples.shape[-1] / rate
        except av.FFmpegError as exc:
            raise ValueError(f"Cannot read media: {source.name}") from exc
        if duration <= 0 or not is_video and not has_audio:
            raise ValueError("The selected file has no usable media.")
        stat = source.stat()
        return {"source_path": str(source), "source_name": source.name, "filename": source.name,
                "source_size": stat.st_size, "source_modified_ns": stat.st_mtime_ns,
                "duration": duration, "width": int(width), "height": int(height), "frame_rate": fps,
                "kind":"video" if is_video else "audio", "has_audio":has_audio}

    def import_video(self, project_id: str, source: Path, name: str, track_index: int, start: float,
                     project_name: str = "Apex Timeline", kind: str = "video", placement_options=None) -> dict:
        metadata = self.source_metadata(source)
        if kind == "video" and metadata["kind"] == "audio": kind = "audio"
        if kind == "audio" and not metadata["has_audio"]: raise ValueError("This file has no audio stream.")
        if not 0 <= track_index < MAX_TRACKS or not math.isfinite(start) or start < 0:
            raise ValueError("Invalid clip position or track.")
        with self.project_lock(project_id):
            project = self.load(project_id, project_name, target_duration=0)
            self.remember_edit(project)
            asset_id = "linked-" + hashlib.sha256(os.path.normcase(metadata["source_path"]).encode()).hexdigest()
            if asset_id not in project["assets"]:
                project["assets"][asset_id] = {"id": asset_id, "name": name or metadata["source_name"],
                    "created_at": _utc_now(), "media_revision": 0, **metadata}
            track = self.audio_track(project, track_index) if kind == "audio" else self.ensure_track(project, track_index)
            track["sparse"] = True
            clip = {"id": uuid.uuid4().hex, "asset_id": asset_id, "track_index": track_index,
                "kind":kind, "start": start, "source_in": 0.0, "duration": metadata["duration"], "created_at": _utc_now()}
            self.place_clip(project, track, clip, placement_options)
            track["clips"].sort(key=lambda clip: clip["start"])
            return self.save(project)

    def source_path(self, project: dict, asset: dict) -> Path:
        if asset.get("source_path"):
            path = Path(asset["source_path"])
            if not path.is_absolute():
                raise ValueError("Linked media needs an absolute source path.")
            return path
        root = (self.project_dir(project["project_id"]) / "assets").resolve()
        path = (root / asset["filename"]).resolve()
        if root not in path.parents:
            raise ValueError("Timeline asset path is outside its media folder.")
        return path

    def asset_path(self, project_id: str, asset_id: str) -> Path:
        project = self.load(project_id)
        asset = project["assets"].get(asset_id)
        if not asset:
            raise FileNotFoundError("Timeline media was not found.")
        path = self.source_path(project, asset)
        if not path.is_file():
            raise FileNotFoundError(f"Missing clip: {asset.get('source_name', asset['filename'])}. Locate its source file.")
        return path

    @staticmethod
    def validate_relink(project: dict, asset_id: str, metadata: dict) -> None:
        required = max((clip.get("source_in", 0) + clip["duration"] for track in project["tracks"] + project["audio_tracks"]
                        for clip in track["clips"] if clip["asset_id"] == asset_id), default=0)
        asset = project["assets"][asset_id]
        if asset.get("kind", "video") != metadata["kind"]:
            raise ValueError("Choose the same media type as the missing source.")
        if any(clip["asset_id"] == asset_id for track in project["audio_tracks"] for clip in track["clips"]) and not metadata["has_audio"]:
            raise ValueError("Replacement media has no audio stream for its sound placements.")
        if metadata["duration"] + 1 / metadata["frame_rate"] < required:
            raise ValueError("Replacement video is shorter than the existing source trims. Choose the correct file.")

    def relink_asset(self, project_id: str, asset_id: str, source: Path, revision=None) -> dict:
        metadata = self.source_metadata(source)
        with self.project_lock(project_id):
            project = self.load(project_id)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before relinking.")
            asset = project["assets"][asset_id]
            self.validate_relink(project, asset_id, metadata)
            self.remember_edit(project)
            project["undo"][-1]["assets"] = copy.deepcopy(project["assets"])
            asset.update(metadata, media_revision=asset.get("media_revision", 0) + 1)
            return self.save(project)

    def search_missing(self, project_id: str, directory: Path, recursive: bool, revision=None) -> tuple:
        if not directory.is_absolute() or not directory.is_dir():
            raise ValueError("Choose a search folder using its full path.")
        project = self.load(project_id)
        expected_revision = project["revision"] if revision is None else int(revision)
        missing = {key: asset for key, asset in project["assets"].items()
                   if not self.source_path(project, asset).is_file()}
        names = {asset.get("source_name", asset["filename"]).casefold() for asset in missing.values()}
        matches = {name: [] for name in names}
        skipped = []
        if recursive:
            files = (Path(root) / name for root, _, files in os.walk(directory, followlinks=False,
                onerror=lambda exc: skipped.append(str(exc.filename))) for name in files)
        else:
            files = directory.iterdir()
        for source in files:
            if source.name.casefold() in matches and source.is_file():
                matches[source.name.casefold()].append(source)
        replacements, unresolved = {}, []
        for key, asset in missing.items():
            candidates = matches[asset.get("source_name", asset["filename"]).casefold()]
            if asset.get("source_size") is not None:
                candidates = [path for path in candidates if path.stat().st_size == asset["source_size"]]
            if len(candidates) != 1:
                unresolved.append({"asset_id": key, "name": asset.get("source_name", asset["filename"]),
                    "reason": "ambiguous" if candidates else "not found", "candidates": [str(path) for path in candidates]})
                continue
            try:
                metadata = self.source_metadata(candidates[0])
                self.validate_relink(project, key, metadata)
                replacements[key] = metadata
            except (OSError, ValueError) as exc:
                unresolved.append({"asset_id":key, "name":asset.get("name", key), "reason":str(exc)})
        with self.project_lock(project_id):
            project = self.load(project_id)
            if project["revision"] != expected_revision:
                raise ValueError("Timeline changed. Reload before searching again.")
            if replacements:
                self.remember_edit(project)
                project["undo"][-1]["assets"] = copy.deepcopy(project["assets"])
                for key, metadata in replacements.items():
                    asset = project["assets"][key]
                    asset.update(metadata, media_revision=asset.get("media_revision", 0) + 1)
                project = self.save(project)
        return project, {"relinked":len(replacements), "unresolved":unresolved, "skipped_folders":skipped[:20]}

    def render_asset_path(self, project: dict, asset_id: str, reference: dict) -> Path:
        source = self.asset_path(project["project_id"], asset_id)
        asset = project["assets"][asset_id]
        width, height = max(2, reference["width"] // 2 * 2), max(2, reference["height"] // 2 * 2)
        fps = reference["frame_rate"]
        if (asset["width"], asset["height"]) == (width, height) and abs(asset["frame_rate"] - fps) < 1e-6:
            return source
        stat = source.stat()
        key = hashlib.sha256(f"{source}:{stat.st_size}:{stat.st_mtime_ns}:{width}:{height}:{fps}".encode()).hexdigest()
        directory = self.project_dir(project["project_id"]) / "render_cache"
        directory.mkdir(exist_ok=True)
        destination = directory / (key + ".mp4")
        if not destination.is_file():
            temporary = directory / (key + "." + uuid.uuid4().hex + ".mp4")
            try:
                _ffmpeg(["-i", str(source), "-map", "0:v:0", "-map", "0:a?", "-vf",
                    f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", str(temporary)])
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return destination

    @staticmethod
    def audio_track(project, index):
        for track in project.setdefault("audio_tracks", []):
            if track["index"] == index:
                return track
        track = {"id":f"audio-{index + 1}", "index":index, "name":f"Audio {index + 1}",
                 "kind":"audio", "muted":False, "volume":1.0, "clips":[]}
        project["audio_tracks"].append(track)
        project["audio_tracks"].sort(key=lambda item:item["index"])
        return track

    def link_clip_audio(self, project, clip):
        asset = project["assets"][clip["asset_id"]]
        if "has_audio" not in asset:
            path = self.source_path(project, asset)
            if not path.is_file():
                return
            with av.open(str(path)) as container:
                asset["has_audio"] = bool(container.streams.audio)
        if not asset["has_audio"]:
            return
        clip["link_id"] = clip["id"]
        track = self.audio_track(project, min(MAX_TRACKS - 1, clip["track_index"] + 1))
        track["clips"].append({**clip, "id":uuid.uuid4().hex, "kind":"audio", "track_index":track["index"]})

    def initialize_audio(self, project):
        if "audio_tracks" not in project:
            project["audio_tracks"] = []
            for track in project["tracks"]:
                for clip in track["clips"]:
                    self.link_clip_audio(project, clip)

    def capture_audio(self, project, audio):
        waveform = audio["waveform"].detach().cpu().float()
        if waveform.ndim != 3 or waveform.shape[0] != 1 or waveform.shape[-1] == 0:
            raise ValueError("Timeline audio needs one nonempty audio batch.")
        rate = int(audio["sample_rate"])
        samples = waveform[0].contiguous().numpy()
        digest = hashlib.sha256(str(rate).encode() + samples.tobytes()).hexdigest()
        if project.get("input_audio_fingerprint") == digest:
            return False
        asset_id = "audio-" + digest
        directory = self.project_dir(project["project_id"]) / "assets"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (asset_id + ".wav")
        if not path.exists():
            write_audio(path, audio)
        self.remember_edit(project)
        project["assets"][asset_id] = {"id":asset_id, "filename":path.name, "name":"Audio input", "kind":"audio",
            "duration":samples.shape[-1] / rate, "frame_rate":24.0, "has_audio":True, "created_at":_utc_now()}
        previous = project.get("input_audio_clip")
        for track in project["audio_tracks"]:
            track["clips"] = [clip for clip in track["clips"] if clip["id"] != previous]
        clip = {"id":uuid.uuid4().hex, "asset_id":asset_id, "kind":"audio", "track_index":0,
                "start":0.0, "source_in":0.0, "duration":samples.shape[-1] / rate, "created_at":_utc_now()}
        self.audio_track(project, 0)["clips"].append(clip)
        project.update(input_audio_fingerprint=digest, input_audio_clip=clip["id"])
        return True

    def edit_audio_track(self, project_id, index, operation, changes=None, revision=None, project_name="Apex Timeline"):
        with self.project_lock(project_id):
            project = self.load(project_id, project_name)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            if not 0 <= index < MAX_TRACKS or operation not in ("add", "delete", "update"):
                raise ValueError("Invalid audio track or operation.")
            changes = changes or {}
            volume = float(changes.get("volume", 1.0))
            if not math.isfinite(volume) or not 0 <= volume <= 4:
                raise ValueError("Audio volume must be between 0 and 400 percent.")
            self.remember_edit(project)
            track = self.audio_track(project, index)
            if operation == "delete":
                groups = {clip.get("link_id") for clip in track["clips"]} - {None}
                project["audio_tracks"].remove(track)
                for other in project["tracks"] + project["audio_tracks"]:
                    for clip in other["clips"]:
                        if clip.get("link_id") in groups: clip.pop("link_id", None)
            elif operation == "update":
                if "muted" in changes: track["muted"] = bool(changes["muted"])
                if "volume" in changes: track["volume"] = volume
            return self.save(project)

    def edit_settings(self, project_id, fps, revision=None):
        fps = float(fps)
        if not math.isfinite(fps) or not 1 <= fps <= 240:
            raise ValueError("Project FPS must be between 1 and 240.")
        with self.project_lock(project_id):
            project = self.load(project_id)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            self.remember_edit(project)
            project["fps"] = fps
            return self.save(project)

    @staticmethod
    def prune_preview_cache(directory, pattern, limit):
        files = sorted(directory.glob(pattern), key=lambda path:path.stat().st_mtime_ns, reverse=True)
        for path in files[limit:]:
            try:
                path.unlink()
            except OSError:
                pass  # A browser may still have an older preview open on Windows.

    def clear_video_cache(self, project_id):
        with self.project_lock(project_id):
            project_dir = self.project_dir(project_id).resolve()
            directory = (project_dir / "render_cache").resolve()
            if project_dir not in directory.parents:
                raise ValueError("Video cache is outside the project folder.")
            count = 0
            if directory.is_dir():
                for path in directory.glob("*.mp4"):
                    path.unlink()
                    count += 1
            return count

    def waveform(self, project_id, asset_id):
        path = self.asset_path(project_id, asset_id)
        stat = path.stat()
        key = hashlib.sha256(f"waveform-1200:{path}:{stat.st_size}:{stat.st_mtime_ns}".encode()).hexdigest()
        directory = self.project_dir(project_id) / "render_cache"
        with self._waveform_lock:
            destination = directory / ("waveform-" + key + ".json")
            if destination.is_file():
                return json.loads(destination.read_text(encoding="utf-8"))
            samples, rate = load_audio(str(path))
            samples = samples.abs().amax(dim=0)
            size = max(1, math.ceil(samples.numel() / 1200))
            padded = torch.nn.functional.pad(samples, (0, (-samples.numel()) % size))
            data = {"peaks":padded.reshape(-1, size).amax(dim=1).tolist(), "duration":samples.numel() / rate}
            directory.mkdir(parents=True, exist_ok=True)
            temporary = directory / (key + "." + uuid.uuid4().hex + ".tmp")
            try:
                temporary.write_text(json.dumps(data), encoding="utf-8")
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            self.prune_preview_cache(directory, "waveform-*.json", 128)
            return data

    def audio_preview(self, project_id):
        with self.project_lock(project_id):
            project = self.load(project_id)
            sources = [self.asset_path(project_id, clip["asset_id"]) for track in project["audio_tracks"]
                       if not track.get("muted") and track.get("volume", 1) > 0 for clip in track["clips"] if clip.get("volume", 1) > 0]
            sources = sorted(set(sources))
            audio_state = [(track.get("muted", False), track.get("volume", 1),
                            [(clip["asset_id"], clip["start"], clip.get("source_in", 0), clip["duration"],
                              clip.get("volume", 1), clip.get("fade_in", 0), clip.get("fade_out", 0)) for clip in track["clips"]])
                           for track in project["audio_tracks"]]
            key = hashlib.sha256(str((audio_state, self.duration(project), project.get("fps", 24),
                                     [(str(path), path.stat().st_size, path.stat().st_mtime_ns) for path in sources])).encode()).hexdigest()
            directory = self.project_dir(project_id) / "render_cache"
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / ("audio-" + key + ".wav")
            if not path.exists():
                audio = mix_timeline_audio(project, self)
                if audio is None: raise ValueError("The timeline has no audio lanes.")
                write_audio(path, audio)
                self.prune_preview_cache(directory, "audio-*.wav", 4)
            return path


    def edit_clip(self, project_id: str, clip_id: str, operation: str, changes=None, revision=None) -> dict:
        with self.project_lock(project_id):
            project = self.load(project_id)
            if revision is not None and project["revision"] != int(revision):
                raise ValueError("Timeline changed. Reload before editing again.")
            tracks = project["tracks"] + project["audio_tracks"]
            source = next((track for track in tracks if any(c["id"] == clip_id for c in track["clips"])), None)
            if source is None: raise KeyError("Timeline clip was not found.")
            clip = next(c for c in source["clips"] if c["id"] == clip_id)
            group = [(track, c) for track in tracks for c in track["clips"]
                     if c["id"] == clip_id or clip.get("link_id") and c.get("link_id") == clip["link_id"]]
            changes = changes or {}
            self.remember_edit(project)
            if operation == "fade":
                side = changes["side"]
                value = float(changes["duration"])
                if side not in ("in", "out") or not math.isfinite(value) or value < 0:
                    raise ValueError("Choose a finite, non-negative fade length.")
                clear_auto_fades(source, clip)
                clip["fade_" + side] = min(value, clip["duration"])
            elif operation == "volume":
                volume = float(changes["volume"])
                if clip.get("kind") != "audio" or not math.isfinite(volume) or not 0 <= volume <= 4:
                    raise ValueError("Choose an audio clip and a volume between 0 and 400 percent.")
                clip["volume"] = volume
            elif operation == "unlink":
                for _, item in group: item.pop("link_id", None)
            elif operation == "delete":
                for track, item in group:
                    clear_auto_fades(track, item)
                    track["clips"].remove(item)
            elif operation in ("update", "up", "down"):
                start = float(changes.get("start", clip["start"]))
                source_in = float(changes.get("source_in", clip.get("source_in", 0)))
                duration = float(changes.get("duration", clip["duration"]))
                target_index = int(changes.get("track_index", source["index"]))
                if operation in ("up", "down"):
                    target_index = max(0, min(MAX_TRACKS - 1, source["index"] + (1 if operation == "up" else -1)))
                if not all(map(math.isfinite, [start, source_in, duration])) or min(start, source_in) < 0 or duration <= 0:
                    raise ValueError("Clip positions and trims must be finite, positive ranges.")
                if not 0 <= target_index < MAX_TRACKS:
                    raise ValueError("The track is out of range.")
                for _, item in group:
                    if source_in + duration > float(project["assets"][item["asset_id"]]["duration"]) + .001:
                        raise ValueError("Trim exceeds the source media.")
                target = self.audio_track(project, target_index) if source.get("kind") == "audio" else self.ensure_track(project, target_index)
                if changes.get("snap") and any(other["id"] != clip_id and start < other["start"] + other["duration"] - 1e-6
                        and start + duration > other["start"] + 1e-6 for other in target["clips"]):
                    raise ValueError("SNAP is on. Turn it off to overlap clips.")
                for track, item in group:
                    clear_auto_fades(track, item)
                    item.update(start=start, source_in=source_in, duration=duration)
                    clamp_fades(item)
                    track["sparse"] = True
                source["clips"].remove(clip)
                target["sparse"] = True
                clip["track_index"] = target_index
                target["clips"].append(clip)
                if changes.get("auto_fade"):
                    for track, item in group:
                        join_fades(target if item is clip else track, item, float(project.get("fps", 24)))
            elif operation in ("duplicate", "split"):
                length = float(changes["position"]) - clip["start"] if operation == "split" else clip["duration"]
                if operation == "split" and (not math.isfinite(length) or not 0 < length < clip["duration"]):
                    raise ValueError("Place the playhead inside the clip to split it.")
                new_link = uuid.uuid4().hex if clip.get("link_id") else None
                for track, item in group:
                    right = {**item, "id":uuid.uuid4().hex, "start":item["start"] + length}
                    if new_link: right["link_id"] = new_link
                    if operation == "split":
                        right.update(source_in=item.get("source_in", 0) + length, duration=item["duration"] - length)
                        item["duration"] = length
                        item["fade_out"] = right["fade_in"] = 0
                        right.pop("auto_fade_in", None)
                        following = item.pop("auto_fade_out", None)
                        for partner in track["clips"]:
                            if partner["id"] == following and partner.get("auto_fade_in") == item["id"]:
                                partner["auto_fade_in"] = right["id"]
                    else:
                        right.pop("auto_fade_in", None)
                        right.pop("auto_fade_out", None)
                    clamp_fades(item)
                    clamp_fades(right)
                    track["clips"].append(right)
                    track["sparse"] = True
            elif operation in ("left", "right"):
                index = source["clips"].index(clip)
                target = index + (-1 if operation == "left" else 1)
                if not 0 <= target < len(source["clips"]): return project
                source["clips"][index], source["clips"][target] = source["clips"][target], clip
                cursor = 0.0
                for item in source["clips"]:
                    item["start"] = cursor
                    cursor += item["duration"]
                    if item.get("link_id"):
                        for track in tracks:
                            for partner in track["clips"]:
                                if partner is not item and partner.get("link_id") == item["link_id"]: partner["start"] = item["start"]
            else:
                raise ValueError("Unknown timeline edit operation.")
            for track in project["tracks"] + project["audio_tracks"]:
                if operation not in ("left", "right"): track["clips"].sort(key=lambda item:float(item["start"]))
            return self.save(project)


    def clear(self, project_id: str) -> dict:
        with self.project_lock(project_id):
            project = self.load(project_id)
            if not project["tracks"] and not project["audio_tracks"] and not project["bin"]:
                return project
            self.remember_edit(project)
            project["tracks"] = []
            project["audio_tracks"] = []
            project.pop("input_audio_fingerprint", None)
            project.pop("input_audio_clip", None)
            project["bin"] = []
            project["overflow_by_track"] = {}
            return self.save(project)


_STORE: TimelineStore | None = None


def get_timeline_store() -> TimelineStore:
    global _STORE
    if _STORE is None:
        _STORE = TimelineStore()
    return _STORE


def project_summary(project: dict) -> dict:
    store = get_timeline_store()
    assets = {}
    for key, asset in project["assets"].items():
        path = store.source_path(project, asset)
        assets[key] = {**asset, "source_path": str(path), "missing": not path.is_file()}
    return {"project_id": project["project_id"], "name": project["name"], "mode": project["mode"],
            "target_duration": project["target_duration"], "duration": TimelineStore.duration(project),
            "clip_count": TimelineStore.clip_count(project), "revision": project["revision"],
            "audio_tracks": project.get("audio_tracks", []), "fps":project.get("fps", 24.0), "fade_support":True,
            "tracks": project["tracks"], "removed_tracks": [index for index in project.get("removed_tracks", []) if index > 0],
            "assets": assets, "bin": project["bin"],
            "can_undo": bool(project.get("undo")), "can_redo": bool(project.get("redo"))}


class ApexTimelineEditor(io.ComfyNode):
    @classmethod
    def fingerprint_inputs(cls, **kwargs):
        # Placements and requested output sockets can change without input changes.
        return float("nan")

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="ApexTimelineEditor", display_name="Apex Timeline Editor",
            category="Apex Artist/Video",
            description="Each autogrowing VIDEO socket maps to a persistent timeline layer. Repeated runs append clips.",
            inputs=[
                io.Autogrow.Input("video_tracks", template=io.Autogrow.TemplatePrefix(
                    io.Video.Input("video", optional=True, tooltip="A generated clip for this timeline layer."),
                    prefix="video_track_", min=1, max=MAX_TRACKS)),
                io.String.Input("project_name", default="Apex Timeline"),
                io.Combo.Input("mode", options=["Single", "Multi"], default="Single"),
                io.Combo.Input("capture_policy", options=["New Results Only", "Every Queue", "Read Saved"], default="New Results Only"),
                io.Float.Input("target_duration", default=180.0, min=0.0, max=86400.0, step=1.0),
                io.Combo.Input("overflow", options=["Keep in Bin", "Stop"], default="Keep in Bin"),
                io.Float.Input("placement_start", default=-1.0, min=-1.0, max=86400.0,
                               optional=True, advanced=True, tooltip="-1 appends to each track; otherwise place at this timeline time."),
                io.Float.Input("placement_offset", default=0.0, min=0.0, max=86400.0, step=0.01,
                               optional=True, advanced=True, tooltip="Extra seconds before each incoming clip. 0 leaves no gap when appending."),
                io.Boolean.Input("capture_clip_audio", default=True, optional=True, advanced=True,
                                 tooltip="Add each video's audio as a linked audio clip. Disable when using a separate master audio input."),
                io.Boolean.Input("prepare_outputs", default=True, optional=True, advanced=True,
                                 tooltip="Prepare VIDEO/IMAGE/AUDIO outputs. In a loop, connect is_last to assemble media only after the final capture."),
                io.Audio.Input("audio", optional=True, tooltip="Capture audio as an editable clip on A1. Audio lanes mix independently."),
            ],
            hidden=[io.Hidden.unique_id, io.Hidden.prompt, io.Hidden.dynprompt],
            outputs=[io.Video.Output("video", display_name="VIDEO"),
                     io.Image.Output("images", display_name="IMAGE"),
                     io.Audio.Output("audio", display_name="AUDIO"),
                     io.Float.Output("fps", display_name="FPS"),
                     TIMELINE_TYPE.Output("timeline", display_name="timeline"),
                     io.Float.Output("duration", display_name="duration"),
                     io.Int.Output("clip_count", display_name="clip count")],
            is_input_list=True, is_output_node=True, not_idempotent=True,
        )

    @classmethod
    def execute(cls, video_tracks, project_name, mode, capture_policy, target_duration, overflow, placement_start=-1.0,
                audio=None, capture_clip_audio=True, placement_offset=0.0, prepare_outputs=True):
        project_name = str(_scalar(project_name, "Apex Timeline"))
        mode = str(_scalar(mode, "Single"))
        capture_policy = str(_scalar(capture_policy, "New Results Only"))
        target_duration = float(_scalar(target_duration, 180.0))
        overflow = str(_scalar(overflow, "Keep in Bin"))
        placement_start = float(_scalar(placement_start, -1.0))
        placement_offset = float(_scalar(placement_offset, 0.0))
        capture_clip_audio = bool(_scalar(capture_clip_audio, True))
        prepare_outputs = bool(_scalar(prepare_outputs, True))
        unique_id = _scalar(cls.hidden.unique_id, "unknown")
        graph = cls.hidden.dynprompt
        node_id = graph.get_display_node_id(unique_id) if graph is not None else unique_id
        store = get_timeline_store()
        project_id = store.project_id(project_name, node_id)
        with store.project_lock(project_id):
            project = store.load(project_id, project_name, mode, target_duration)
            if capture_policy != "Read Saved":
                changed = (
                    not (store.project_dir(project_id) / "project.json").exists()
                    or project.get("name") != project_name
                    or project.get("mode") != mode
                    or float(project.get("target_duration", 0.0)) != target_duration
                )
                project.update(name=project_name, mode=mode, target_duration=target_duration)
                if audio is not None:
                    changed = store.capture_audio(project, _scalar(audio)) or changed
                for socket_name, group in sorted(video_tracks.items()):
                    match = re.search(r"(\d+)$", socket_name)
                    track_index = int(match.group(1)) if match else 0
                    if mode == "Single" and track_index != 0:
                        continue
                    for video in group if isinstance(group, list) else [group]:
                        if video is None:
                            continue
                        clip, status = store.capture_video(project, track_index, video, capture_policy,
                                                           target_duration, overflow, placement_start, capture_clip_audio, placement_offset)
                        changed = changed or clip is not None or status in ("bin", "full")
                if changed:
                    project = store.save(project)
        summary = project_summary(project)
        try:
            from server import PromptServer
            PromptServer.instance.send_sync("apex-timeline-changed", {"node": str(node_id), **summary})
        except Exception:
            pass
        definitions = (graph.get_node(key) for key in graph.all_node_ids()) if graph is not None else (cls.hidden.prompt or {}).values()
        connected = {value[1] for definition in definitions for value in definition["inputs"].values()
                     if is_link(value) and str(value[0]) == str(unique_id)} if prepare_outputs else set()
        video, images, audio_out, fps = timeline_media(project, store, connected)
        return io.NodeOutput(video, images, audio_out, fps, summary, summary["duration"], summary["clip_count"])


def composite_spans(project: dict, base_index: int) -> list:
    """Resolve visible full-frame cuts on a shared frame grid without decoding the song."""
    base = next((track for track in project["tracks"] if int(track["index"]) == base_index), None)
    if not base or not base["clips"]:
        base = next((track for track in project["tracks"] if int(track["index"]) >= base_index and track["clips"]), None)
    if base is None:
        raise ValueError("The timeline has no clips to render.")
    first = project["assets"][base["clips"][0]["asset_id"]]
    fps = float(project.get("fps", 24.0))
    total = round(TimelineStore.duration(project) * fps)
    layers = []
    boundaries = {0, total}
    for track in sorted(project["tracks"], key=lambda track: int(track["index"])):
        if int(track["index"]) < base_index:
            continue
        for clip in track["clips"]:
            start = max(0, round(float(clip["start"]) * fps))
            end = min(total, round((float(clip["start"]) + float(clip["duration"])) * fps))
            if end > start:
                boundaries.update((start, end))
                layers.append((clip, start, end))
    boundaries = sorted(boundaries)
    spans = []
    for start, end in zip(boundaries, boundaries[1:]):
        selected = next((item for item in reversed(layers) if item[1] <= start and item[2] >= end), None)
        if selected is None:
            spans.append((None, 0, (end - start) / fps))
            continue
        clip, clip_start, _ = selected
        source_in = float(clip.get("source_in", 0)) + (start - clip_start) / fps
        duration = (end - start) / fps
        if spans and spans[-1][0] is not None and spans[-1][0]["id"] == clip["id"] and abs(spans[-1][1] + spans[-1][2] - source_in) < 1e-6:
            spans[-1] = (clip, spans[-1][1], spans[-1][2] + duration)
        else:
            spans.append((clip, source_in, duration))
    return spans


def timeline_video(project, store, track_index=0, composite=True, complete_audio=None):
    selected = next((item for item in project["tracks"] if int(item["index"]) == track_index), None)
    if composite and (not selected or not selected["clips"]):
        selected = next((item for item in project["tracks"] if int(item["index"]) >= track_index and item["clips"]), None)
    if not selected or not selected["clips"]:
        raise ValueError(f"Timeline track {track_index + 1} has no clips to render.")
    reference = {**project["assets"][selected["clips"][0]["asset_id"]], "frame_rate":project.get("fps", 24.0)}
    if composite and any(clip.get("fade_in") or clip.get("fade_out") for track in project["tracks"] for clip in track["clips"]):
        videos = []
        for start, duration, layers in fade_spans(project, reference["frame_rate"], TimelineStore.duration(project), track_index):
            if layers and min(fade_value(layers[-1][0], start, layers[-1][1]),
                              fade_value(layers[-1][0], start + duration, layers[-1][1])) >= 1:
                clip = layers[-1][0]
                video = InputImpl.VideoFromFile(str(store.render_asset_path(project, clip["asset_id"], reference)))
                videos.append(video.as_trimmed(clip.get("source_in", 0) + start - clip["start"], duration, strict_duration=False))
            else:
                path = render_fade_span(project, store, layers, start, duration, reference, _ffmpeg)
                videos.append(InputImpl.VideoFromFile(str(path)))
        return InputImpl.VideoFromList(videos, complete_audio, codec=Types.VideoCodec.H264)
    if composite:
        spans = composite_spans(project, track_index)
        videos = []
        for clip, source_in, duration in spans:
            if clip is None:
                reference = {**project["assets"][selected["clips"][0]["asset_id"]], "frame_rate":project.get("fps", 24.0)}
                directory = store.project_dir(project["project_id"]) / "render_cache"
                directory.mkdir(exist_ok=True)
                path = directory / f"black-{reference['width']}-{reference['height']}-{reference['frame_rate']}-{duration:.8f}.mp4"
                if not path.exists():
                    _ffmpeg(["-f", "lavfi", "-i", f"color=c=black:s={reference['width']}x{reference['height']}:r={reference['frame_rate']}",
                             "-t", str(duration), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)])
                videos.append(InputImpl.VideoFromFile(str(path)))
                continue
            video = InputImpl.VideoFromFile(str(store.render_asset_path(project, clip["asset_id"], reference)))
            videos.append(video.as_trimmed(source_in, duration, strict_duration=False))
        return InputImpl.VideoFromList(videos, complete_audio, codec=Types.VideoCodec.H264)
    videos = []
    for clip in selected["clips"]:
        asset = project["assets"].get(clip["asset_id"])
        if not asset:
            raise ValueError(f"Timeline clip {clip['id']} references a missing asset record.")
        video = InputImpl.VideoFromFile(str(store.render_asset_path(project, clip["asset_id"], reference)))
        source_in, duration = float(clip.get("source_in", 0.0)), float(clip["duration"])
        if source_in or duration < float(asset["duration"]):
            video = video.as_trimmed(source_in, duration, strict_duration=False)
            if video is None:
                raise ValueError(f"Timeline clip {clip['id']} has an invalid trim range.")
        videos.append(video)
    return InputImpl.VideoFromList(videos, complete_audio, codec=Types.VideoCodec.H264)


def timeline_media(project, store, connected):
    if not connected.intersection({0, 1, 2, 3}):
        return None, None, None, 0.0
    video_clips = [clip for track in project["tracks"] for clip in track["clips"]]
    if not video_clips and not any(track["clips"] for track in project["audio_tracks"]):
        raise ValueError("The timeline has no clips. Import media before exporting.")
    fps = float(project.get("fps", 24.0))
    if not connected.intersection({0, 1, 2}):
        return None, None, None, fps
    mixed = mix_timeline_audio(project, store, fps)
    video, images = None, None
    if connected.intersection({0, 1}):
        if not video_clips: raise ValueError("Add a video clip to use VIDEO or IMAGE. Audio-only edits can use AUDIO.")
        video = timeline_video(project, store, complete_audio=mixed)
        if mixed is None:
            # A fully muted edit must not fall back to embedded source sound.
            video.complete_audio = {"waveform":torch.zeros((1, 1, round(TimelineStore.duration(project) * 48000))), "sample_rate":48000}
        if 1 in connected:
            components = video.get_components()
            images = components.images
    return video, images, mixed, fps


def mix_timeline_audio(project, store, fps=None):
    fps = float(project.get("fps", 24.0) if fps is None else fps)
    placements = [(track, clip) for track in project["audio_tracks"] if not track.get("muted") and track.get("volume", 1) > 0
                  for clip in track["clips"] if clip.get("volume", 1) > 0]
    sample_rate = 48000
    count = round(round(TimelineStore.duration(project) * fps) / fps * sample_rate)
    if not project["audio_tracks"]:
        return None
    decoded = {}
    for _, clip in placements:
        if clip["asset_id"] not in decoded:
            samples, rate = load_audio(str(store.asset_path(project["project_id"], clip["asset_id"])))
            decoded[clip["asset_id"]] = resample(samples, rate, sample_rate)
    channels = max((samples.shape[0] for samples in decoded.values()), default=1)
    waveform = torch.zeros((1, channels, count))
    for track, clip in placements:
        begin = round(clip["start"] * sample_rate)
        end = min(count, round((clip["start"] + clip["duration"]) * sample_rate))
        source_in = round(clip.get("source_in", 0) * sample_rate)
        samples = decoded[clip["asset_id"]][:, source_in:source_in + max(0, end - begin)]
        if samples.shape[0] == 1:
            samples = samples.expand(channels, -1)
        if clip.get("fade_in") or clip.get("fade_out"):
            local = torch.arange(samples.shape[-1], dtype=samples.dtype) / sample_rate
            envelope = torch.ones_like(local)
            if clip.get("fade_in"):
                envelope *= (local / clip["fade_in"]).clamp(0, 1)
            if clip.get("fade_out"):
                envelope *= ((clip["duration"] - local) / clip["fade_out"]).clamp(0, 1)
            samples = samples * envelope
        waveform[0, :samples.shape[0], begin:begin + samples.shape[-1]] += samples * track.get("volume", 1.0) * clip.get("volume", 1.0)
    return {"waveform":waveform.clamp(-1, 1), "sample_rate":sample_rate}
