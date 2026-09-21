"""Preset routes: factory data is read-only, user mutations are revisioned."""
import asyncio
import json
import logging
from aiohttp import web
from server import PromptServer
from .apex_prompt_store import CATEGORIES, MAX_BYTES, PresetError, get_store


class ApexPromptPresetAPI:
    def __init__(self):
        self.setup_routes()

    async def snapshot(self):
        return await asyncio.get_running_loop().run_in_executor(None, get_store().snapshot)

    async def modify(self, request, operation):
        try:
            raw = bytearray()
            async for chunk in request.content.iter_chunked(65536):
                raw.extend(chunk)
                if len(raw) > MAX_BYTES:
                    return web.json_response({"error": "Preset request exceeds 4 MiB."}, status=413)
            payload = json.loads(raw)
            result = await asyncio.get_running_loop().run_in_executor(
                None, get_store().mutate, operation, payload)
            # A notification failure must not turn a successful save into an error.
            try:
                PromptServer.instance.send_sync("apex-presets-changed", {"revision": result["revision"]})
            except Exception:
                logging.exception("[Apex Prompt] Could not broadcast preset refresh")
            return web.json_response(result)
        except PresetError as exc:
            return web.json_response({"error": str(exc)}, status=exc.status)
        except (ValueError, UnicodeError) as exc:
            return web.json_response({"error": "Invalid JSON: " + str(exc)}, status=400)
        except OSError:
            logging.exception("[Apex Prompt] Failed to persist user presets")
            return web.json_response({"error": "Could not save user presets. Check server logs and directory permissions."}, status=500)

    def setup_routes(self):
        routes = PromptServer.instance.routes

        @routes.get("/apex/prompt_library")
        async def library(request):
            try:
                return web.json_response(await self.snapshot())
            except PresetError as exc:
                return web.json_response({"error": str(exc)}, status=exc.status)

        @routes.post("/apex/prompt_library/save")
        async def save(request):
            return await self.modify(request, "save")

        @routes.post("/apex/prompt_library/delete")
        async def delete(request):
            return await self.modify(request, "delete")

        @routes.post("/apex/prompt_library/import")
        async def import_presets(request):
            return await self.modify(request, "import")

        @routes.get("/apex/prompt_presets")
        async def get_presets(request):
            try:
                return web.json_response((await self.snapshot())["presets"])
            except PresetError as exc:
                return web.json_response({"error": str(exc)}, status=exc.status)

        @routes.get("/apex/prompt_presets/{category}")
        async def get_category(request):
            category = request.match_info["category"]
            if category not in CATEGORIES:
                return web.json_response({"error": "Unknown category."}, status=404)
            try:
                return web.json_response((await self.snapshot())["presets"][category])
            except PresetError as exc:
                return web.json_response({"error": str(exc)}, status=exc.status)

        @routes.post("/apex/prompt_presets")
        @routes.post("/apex/prompt_presets/{category}/{name}")
        @routes.delete("/apex/prompt_presets/{category}/{name}")
        async def legacy_write(request):
            return web.json_response({"error": "Factory presets are read-only. Refresh your browser and use Save Preset / Manage Presets."}, status=403)


api_instance = ApexPromptPresetAPI()