"""
Apex Prompt API Server
Handles preset management via HTTP endpoints
Preset data is imported from apex_prompt.py (single source of truth).
"""

import os
import json
from aiohttp import web
from server import PromptServer
from .apex_prompt import ApexPromptPreset

class ApexPromptPresetAPI:
    def __init__(self):
        self.presets_file = os.path.join(os.path.dirname(__file__), "prompt_presets.json")
        self.setup_routes()

    def setup_routes(self):
        """Setup API routes for preset management"""
        
        @PromptServer.instance.routes.get("/apex/prompt_presets")
        async def get_presets(request):
            """Get all presets"""
            try:
                if os.path.exists(self.presets_file):
                    with open(self.presets_file, 'r', encoding='utf-8') as f:
                        presets = json.load(f)
                else:
                    presets = ApexPromptPreset.get_default_presets()
                return web.json_response(presets)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/apex/prompt_presets")
        async def save_presets(request):
            """Save all presets"""
            try:
                presets = await request.json()
                with open(self.presets_file, 'w', encoding='utf-8') as f:
                    json.dump(presets, f, indent=2, ensure_ascii=False)
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.get("/apex/prompt_presets/{category}")
        async def get_category_presets(request):
            """Get presets for a specific category"""
            try:
                category = request.match_info['category']
                if os.path.exists(self.presets_file):
                    with open(self.presets_file, 'r', encoding='utf-8') as f:
                        all_presets = json.load(f)
                        category_presets = all_presets.get(category, {})
                else:
                    all_presets = ApexPromptPreset.get_default_presets()
                    category_presets = all_presets.get(category, {})
                return web.json_response(category_presets)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/apex/prompt_presets/{category}/{name}")
        async def save_preset(request):
            """Save a specific preset"""
            try:
                category = request.match_info['category']
                name = request.match_info['name']
                preset_data = await request.json()
                
                # Load existing presets
                if os.path.exists(self.presets_file):
                    with open(self.presets_file, 'r', encoding='utf-8') as f:
                        presets = json.load(f)
                else:
                    presets = {}
                
                # Update preset
                if category not in presets:
                    presets[category] = {}
                presets[category][name] = preset_data
                
                # Save
                with open(self.presets_file, 'w', encoding='utf-8') as f:
                    json.dump(presets, f, indent=2, ensure_ascii=False)
                
                return web.json_response({"status": "success"})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.delete("/apex/prompt_presets/{category}/{name}")
        async def delete_preset(request):
            """Delete a specific preset"""
            try:
                category = request.match_info['category']
                name = request.match_info['name']
                
                # Load existing presets
                if os.path.exists(self.presets_file):
                    with open(self.presets_file, 'r', encoding='utf-8') as f:
                        presets = json.load(f)
                else:
                    return web.json_response({"error": "Presets file not found"}, status=404)
                
                # Delete preset
                if category in presets and name in presets[category]:
                    del presets[category][name]
                    
                    # Remove empty category
                    if not presets[category]:
                        del presets[category]
                    
                    # Save
                    with open(self.presets_file, 'w', encoding='utf-8') as f:
                        json.dump(presets, f, indent=2, ensure_ascii=False)
                    
                    return web.json_response({"status": "success"})
                else:
                    return web.json_response({"error": "Preset not found"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

# Initialize the API
api_instance = ApexPromptPresetAPI()
