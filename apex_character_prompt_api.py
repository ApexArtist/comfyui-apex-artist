"""Character preset API with validated, revision-checked user storage."""

import asyncio
import copy
import json

from aiohttp import web
from server import PromptServer

from .apex_prompt_store import MAX_BYTES, PresetError, PresetConflict, PresetNotFound, get_character_store, validate_name


class ApexCharacterPresetAPI:
    def __init__(self):
        self.setup_routes()

    def change(self, revision, operation, payload, category=None, name=None):
        store = get_character_store()
        snapshot = store.snapshot()
        if revision != snapshot["revision"]:
            raise PresetConflict("Character presets changed. Reload the manager before saving.")
        presets = copy.deepcopy(snapshot["presets"])
        if operation == "replace":
            presets = payload
        else:
            if category not in store.categories:
                raise PresetError("Unknown character category.")
            validate_name(name)
            if operation == "save":
                presets[category][name] = payload
            else:
                if name not in presets[category]:
                    raise PresetNotFound("Character preset not found.")
                del presets[category][name]
        return store.mutate("replace", {"revision": revision, "presets": presets})

    async def read(self, category=None):
        try:
            snapshot = await asyncio.to_thread(get_character_store().snapshot)
            if category is not None and category not in snapshot["presets"]:
                raise PresetNotFound("Character category not found.")
            data = snapshot["presets"] if category is None else snapshot["presets"][category]
            return web.json_response(data, headers={"ETag": '"' + snapshot["revision"] + '"'})
        except PresetError as exc:
            return web.json_response({"error": str(exc)}, status=exc.status)

    async def write(self, request, operation):
        try:
            payload = None
            if operation != "delete":
                raw = bytearray()
                async for chunk in request.content.iter_chunked(65536):
                    raw.extend(chunk)
                    if len(raw) > MAX_BYTES:
                        return web.json_response({"error": "Character presets exceed 4 MiB."}, status=413)
                payload = json.loads(raw)
            revision = request.headers.get("If-Match", "").strip('"')
            snapshot = await asyncio.to_thread(self.change, revision, operation, payload,
                                             request.match_info.get("category"), request.match_info.get("name"))
            PromptServer.instance.send_sync("apex-character-presets-changed", {"revision": snapshot["revision"]})
            return web.json_response({"status": "success"}, headers={"ETag": '"' + snapshot["revision"] + '"'})
        except PresetError as exc:
            return web.json_response({"error": str(exc)}, status=exc.status)
        except (ValueError, UnicodeError) as exc:
            return web.json_response({"error": "Invalid character preset JSON: " + str(exc)}, status=400)
        except OSError:
            return web.json_response({"error": "Cannot save character presets. Check user-folder permissions."}, status=500)

    def setup_routes(self):
        routes = PromptServer.instance.routes

        @routes.get("/apex/character_presets")
        async def get_presets(request):
            return await self.read()

        @routes.get("/apex/character_presets/{category}")
        async def get_category(request):
            return await self.read(request.match_info["category"])

        @routes.post("/apex/character_presets")
        async def replace(request):
            return await self.write(request, "replace")

        @routes.post("/apex/character_presets/{category}/{name}")
        async def save(request):
            return await self.write(request, "save")

        @routes.delete("/apex/character_presets/{category}/{name}")
        async def delete(request):
            return await self.write(request, "delete")


api_instance = ApexCharacterPresetAPI()
