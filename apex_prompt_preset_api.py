"""
Apex Prompt Preset API Server
Handles preset management via HTTP endpoints
"""

import os
import json
from aiohttp import web
from server import PromptServer

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
                    presets = self.get_default_presets()
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
                    all_presets = self.get_default_presets()
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

    def get_default_presets(self):
        """Default presets for initialization"""
        return {
            "General": {
                "High Quality": {
                    "prompt": "masterpiece, best quality, ultra-detailed, 8k resolution, professional photography",
                    "description": "General high-quality enhancement prompt",
                    "tags": ["quality", "detail", "professional"],
                    "weight": 1.2
                },
                "Cinematic": {
                    "prompt": "cinematic lighting, dramatic composition, film grain, depth of field, bokeh",
                    "description": "Cinematic movie-like aesthetic",
                    "tags": ["cinematic", "dramatic", "film"],
                    "weight": 1.1
                }
            },
            "Photography": {
                "Portrait Professional": {
                    "prompt": "professional portrait, studio lighting, sharp focus, 85mm lens, natural skin texture, high resolution",
                    "description": "Professional portrait photography setup",
                    "tags": ["portrait", "professional", "studio"],
                    "weight": 1.2
                }
            },
            "Negative": {
                "Quality Issues": {
                    "prompt": "worst quality, low quality, blurry, out of focus, pixelated, low resolution, jpeg artifacts",
                    "description": "Common quality issues to avoid",
                    "tags": ["negative", "quality", "avoid"],
                    "weight": 1.0
                }
            }
        }

# Initialize the API
api_instance = ApexPromptPresetAPI()