"""HTTP routes for the Apex Timeline editor frontend."""

import asyncio
import json
import logging
import os
from pathlib import Path

import folder_paths

from aiohttp import web
from server import PromptServer

from .apex_timeline import get_timeline_store, project_summary, VIDEO_SUFFIXES, AUDIO_SUFFIXES


def _project_identity(request):
    project_name = request.query.get("project_name", "Apex Timeline")
    node_id = request.query.get("node_id", "unknown")
    store = get_timeline_store()
    return store, store.project_id(project_name, node_id), project_name


def _broadcast(node_id, project):
    try:
        PromptServer.instance.send_sync("apex-timeline-changed", {"node": str(node_id), **project_summary(project)})
    except Exception:
        logging.exception("[Apex Timeline] Could not broadcast project refresh")


routes = PromptServer.instance.routes


@routes.get("/apex/timeline/project")
async def timeline_project(request):
    try:
        store, project_id, project_name = _project_identity(request)
        project = await asyncio.to_thread(store.load, project_id, project_name)
        return web.json_response(project_summary(project))
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.get("/apex/timeline/media")
async def timeline_media(request):
    try:
        store = get_timeline_store()
        path = await asyncio.to_thread(store.asset_path, request.query["project_id"], request.query["asset_id"])
        return web.FileResponse(path)
    except (KeyError, FileNotFoundError, ValueError):
        return web.json_response({"error": "Timeline media was not found."}, status=404)


@routes.post("/apex/timeline/clip/edit")
async def timeline_clip_edit(request):
    try:
        payload = await request.json()
        store = get_timeline_store()
        project = await asyncio.to_thread(
            store.edit_clip, payload["project_id"], payload["clip_id"], payload["operation"],
            payload.get("changes"), payload.get("revision")
        )
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except KeyError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    except (TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.post("/apex/timeline/history")
async def timeline_history(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().restore_edit, payload["project_id"],
                                          payload["operation"], payload.get("revision"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.post("/apex/timeline/track/edit")
async def timeline_track_edit(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().edit_track, payload["project_id"],
                                          int(payload["track_index"]), payload["operation"], payload.get("revision"),
                                          payload.get("project_name", "Apex Timeline"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.post("/apex/timeline/asset/place")
async def timeline_place_asset(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().place_asset, payload["project_id"], payload["asset_id"],
                    int(payload["track_index"]), float(payload["start"]), payload.get("revision"), payload.get("kind", "video"), payload.get("placement_options"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.post("/apex/timeline/audio/track")
async def timeline_audio_track(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().edit_audio_track, payload["project_id"],
            int(payload["track_index"]), payload["operation"], payload.get("changes"), payload.get("revision"),
            payload.get("project_name", "Apex Timeline"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.get("/apex/timeline/waveform")
async def timeline_waveform(request):
    try:
        result = await asyncio.to_thread(get_timeline_store().waveform, request.query["project_id"], request.query["asset_id"])
        return web.json_response(result)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.post("/apex/timeline/settings")
async def timeline_settings(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().edit_settings, payload["project_id"],
            payload["fps"], payload.get("revision"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.get("/apex/timeline/audio-preview")
async def timeline_audio_preview(request):
    try:
        path = await asyncio.to_thread(get_timeline_store().audio_preview, request.query["project_id"])
        return web.FileResponse(path)
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.post("/apex/timeline/import")
async def timeline_import(request):
    try:
        if request.content_type != "application/json":
            raise ValueError("Link the original source path. Timeline imports do not upload or copy files.")
        payload = await request.json()
        source = Path(payload["source_path"])
        project = await asyncio.to_thread(get_timeline_store().import_video, payload["project_id"], source,
            source.name, int(payload.get("track_index", 1)), float(payload.get("start", 0)),
            payload.get("project_name", "Apex Timeline"), payload.get("kind", "video"), payload.get("placement_options"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.post("/apex/timeline/media/relink")
async def timeline_relink(request):
    try:
        payload = await request.json()
        project = await asyncio.to_thread(get_timeline_store().relink_asset, payload["project_id"],
            payload["asset_id"], Path(payload["source_path"]), payload.get("revision"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.post("/apex/timeline/media/search")
async def timeline_search_missing(request):
    try:
        payload = await request.json()
        project, report = await asyncio.to_thread(get_timeline_store().search_missing, payload["project_id"],
            Path(payload["directory"]), bool(payload.get("recursive", False)), payload.get("revision"))
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response({"project":project_summary(project), **report})
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


def _list_source_files(directory):
    path = Path(directory).expanduser() if directory else Path(folder_paths.get_input_directory())
    if not path.is_absolute():
        raise ValueError("Use a full folder path.")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError("Choose a folder to browse.")
    entries = []
    for child in path.iterdir():
        try:
            is_directory = child.is_dir()
            if is_directory or child.suffix.lower() in VIDEO_SUFFIXES | AUDIO_SUFFIXES:
                entries.append({"name":child.name, "path":str(child), "directory":is_directory})
        except OSError:
            continue
    entries.sort(key=lambda entry:(not entry["directory"], entry["name"].casefold()))
    roots = [f"{chr(letter)}:/" for letter in range(65,91) if Path(f"{chr(letter)}:/").is_dir()] if os.name == "nt" else ["/"]
    return {"directory":str(path), "parent":str(path.parent), "roots":roots,
            "entries":entries[:1000], "truncated":len(entries)>1000}


@routes.get("/apex/timeline/files")
async def timeline_source_files(request):
    try:
        result = await asyncio.to_thread(_list_source_files, request.query.get("directory", ""))
        return web.json_response(result)
    except (TypeError, ValueError, OSError) as exc:
        return web.json_response({"error":str(exc)}, status=400)


@routes.post("/apex/timeline/project/clear")
async def timeline_project_clear(request):
    try:
        payload = await request.json()
        store = get_timeline_store()
        project = await asyncio.to_thread(store.clear, payload["project_id"])
        _broadcast(payload.get("node_id", "unknown"), project)
        return web.json_response(project_summary(project))
    except KeyError as exc:
        return web.json_response({"error": str(exc)}, status=404)
    except (TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


def clear_video_cache_if_idle(store, project_id):
    queue = PromptServer.instance.prompt_queue
    with queue.mutex:
        running, pending = queue.get_current_queue()
        if running or pending:
            return None
        return store.clear_video_cache(project_id)


@routes.post("/apex/timeline/cache/clear")
async def timeline_cache_clear(request):
    try:
        payload = await request.json()
        store = get_timeline_store()
        count = await asyncio.to_thread(clear_video_cache_if_idle, store, payload["project_id"])
        if count is None:
            return web.json_response({"error": "Wait for the ComfyUI queue to finish before clearing video caches."}, status=409)
        project = await asyncio.to_thread(store.load, payload["project_id"])
        return web.json_response({**project_summary(project), "cleared_cache_files": count})
    except (KeyError, TypeError, ValueError, OSError) as exc:
        return web.json_response({"error": str(exc)}, status=400)
