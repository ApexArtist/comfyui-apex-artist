"""
Apex Camera Lens Preview API Server
Handles lens preview image serving via HTTP endpoints
"""

import os
import json
from aiohttp import web
from server import PromptServer

class ApexLensAPI:
    def __init__(self):
        self.lens_previews_dir = os.path.join(os.path.dirname(__file__), "lens_previews")
        self.setup_routes()
    
    def get_lens_presets(self):
        """Get all lens presets from apex_prompt.py"""
        try:
            from .apex_prompt import ApexPromptPreset
            instance = ApexPromptPreset()
            presets = instance.get_default_presets()
            
            # Extract just the camera lens presets
            if "Apex Camera Lens" in presets:
                return presets["Apex Camera Lens"]
            return {}
        except Exception as e:
            print(f"[Apex Lens API] Error loading presets: {e}")
            return {}
    
    def get_preview_path(self, lens_name):
        """
        Get the preview image path for a lens preset
        
        Args:
            lens_name: Lens preset name (e.g., "85mm Portrait Classic")
            
        Returns:
            Full path to preview image, or None if not found
        """
        if not lens_name or not os.path.exists(self.lens_previews_dir):
            return None
        
        # Direct filename match: lens name with .jpg extension
        # Files have been renamed to match exact preset names
        filename = lens_name + ".jpg"
        preview_path = os.path.join(self.lens_previews_dir, filename)
        
        if os.path.exists(preview_path):
            return preview_path
        
        return None
    
    def setup_routes(self):
        """Setup API routes for lens preview management"""
        
        @PromptServer.instance.routes.post("/apex/lens_list")
        async def list_lenses(request):
            """List all available lens presets with metadata"""
            try:
                lens_presets = self.get_lens_presets()
                
                # Build response with preview availability
                lenses = []
                for lens_name, lens_data in lens_presets.items():
                    preview_path = self.get_preview_path(lens_name)
                    has_preview = preview_path is not None
                    
                    lenses.append({
                        "name": lens_name,
                        "description": lens_data.get("description", ""),
                        "tags": lens_data.get("tags", []),
                        "weight": lens_data.get("weight", 1.0),
                        "has_preview": has_preview
                    })
                
                return web.json_response({
                    "lenses": lenses,
                    "total": len(lenses)
                })
                
            except Exception as e:
                print(f"[Apex Lens API] Error listing lenses: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        @PromptServer.instance.routes.post("/apex/lens_preview")
        async def get_lens_preview(request):
            """Get the preview image path for a specific lens"""
            try:
                data = await request.json()
                lens_name = data.get("lens_name")
                
                if not lens_name:
                    return web.json_response({"error": "No lens_name provided"}, status=400)
                
                preview_path = self.get_preview_path(lens_name)
                
                if preview_path and os.path.exists(preview_path):
                    return web.json_response({"preview_path": preview_path})
                else:
                    return web.json_response({"preview_path": None})
                    
            except Exception as e:
                print(f"[Apex Lens API] Error getting preview: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        @PromptServer.instance.routes.get("/apex/lens_image")
        async def serve_lens_image(request):
            """Serve lens preview image"""
            try:
                image_path = request.query.get("path")
                
                if not image_path:
                    return web.Response(status=400, text="No path provided")
                
                if not os.path.exists(image_path):
                    return web.Response(status=404, text="Image not found")
                
                # Security check: ensure the path is within the lens_previews directory
                image_path_normalized = os.path.normpath(os.path.abspath(image_path))
                lens_previews_normalized = os.path.normpath(os.path.abspath(self.lens_previews_dir))
                
                if not image_path_normalized.startswith(lens_previews_normalized):
                    return web.Response(status=403, text="Access denied")
                
                # Determine content type
                ext = os.path.splitext(image_path)[1].lower()
                content_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                }.get(ext, 'application/octet-stream')
                
                # Read and serve the file
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                return web.Response(
                    body=image_data,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                    }
                )
                
            except Exception as e:
                print(f"[Apex Lens API] Error serving image: {e}")
                return web.Response(status=500, text=str(e))

# Initialize the API
api_instance = ApexLensAPI()
