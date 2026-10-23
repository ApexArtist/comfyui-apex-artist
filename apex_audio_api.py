"""Local file previews for Apex Audio; connected audio uses ComfyUI preview files."""

import asyncio

from aiohttp import web
from av.error import FFmpegError
from server import PromptServer

from .apex_audio import audio_path, file_info


routes = PromptServer.instance.routes


@routes.get("/apex/audio/info")
async def audio_file_info(request):
    try:
        return web.json_response(await asyncio.to_thread(file_info, request.query["filename"]))
    except (KeyError, OSError, ValueError, FFmpegError) as exc:
        return web.json_response({"error": str(exc)}, status=400)


@routes.get("/apex/audio/media")
async def audio_file_media(request):
    try:
        return web.FileResponse(audio_path(request.query["filename"]))
    except (KeyError, OSError, ValueError):
        return web.json_response({"error": "Audio file not found."}, status=404)
