"""
Apex Character Prompt API Server
Preset CRUD for the character preset library (character_presets.json).

Mirrors the route layout of apex_prompt_api.py but operates on the character store, so the
character preset library stays fully isolated from the environment/lighting/style presets.
"""

import json
import os

import aiofiles
from aiohttp import web
from server import PromptServer

from .apex_character_prompt import ApexCharacterPrompt


class ApexCharacterPresetAPI:
    def __init__(self):
        self.presets_file = os.path.join(
            os.path.dirname(__file__), ApexCharacterPrompt.PRESET_FILE_NAME
        )
        self.setup_routes()

    async def _read_presets(self):
        """Read the character preset store (empty dict when the file does not exist yet)."""
        if os.path.exists(self.presets_file):
            async with aiofiles.open(self.presets_file, "r", encoding="utf-8") as f:
                content = await f.read()
            return json.loads(content)
        return {}

    async def _write_presets(self, presets):
        """Write the character preset store as pretty JSON."""
        async with aiofiles.open(self.presets_file, "w", encoding="utf-8") as f:
            await f.write(json.dumps(presets, indent=2, ensure_ascii=False))

    def setup_routes(self):
        """Setup API routes for character preset management."""

        @PromptServer.instance.routes.get("/apex/character_presets")
        async def get_presets(request):
            """Get all character presets"""
            try:
                presets = await self._read_presets()
                if not presets:
                    presets = ApexCharacterPrompt.get_default_presets()
                return web.json_response(presets)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/apex/character_presets")
        async def save_presets(request):
            """Save all character presets"""
            try:
                presets = await request.json()
                await self._write_presets(presets)
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.get("/apex/character_presets/{category}")
        async def get_category_presets(request):
            """Get presets for a specific character category"""
            try:
                category = request.match_info["category"]
                presets = await self._read_presets()
                if not presets:
                    presets = ApexCharacterPrompt.get_default_presets()
                return web.json_response(presets.get(category, {}))
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/apex/character_presets/{category}/{name}")
        async def save_preset(request):
            """Save a single character preset"""
            try:
                category = request.match_info["category"]
                name = request.match_info["name"]
                preset_data = await request.json()

                presets = await self._read_presets()
                if not presets:
                    presets = ApexCharacterPrompt.get_default_presets()

                if category not in presets:
                    presets[category] = {}
                presets[category][name] = preset_data

                await self._write_presets(presets)
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.delete("/apex/character_presets/{category}/{name}")
        async def delete_preset(request):
            """Delete a single character preset"""
            try:
                category = request.match_info["category"]
                name = request.match_info["name"]

                presets = await self._read_presets()
                if not presets:
                    return web.json_response({"error": "Character presets file not found"}, status=404)

                if category in presets and name in presets[category]:
                    del presets[category][name]

                    # Remove the category when it becomes empty
                    if not presets[category]:
                        del presets[category]

                    await self._write_presets(presets)
                    return web.json_response({"status": "success"})

                return web.json_response({"error": "Preset not found"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)


# Initialize the API
api_instance = ApexCharacterPresetAPI()
