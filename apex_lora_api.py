"""
Apex LoRA API Server
Handles LoRA preview image serving via HTTP endpoints with optimized thumbnail generation
"""

import os
import hashlib
import aiofiles
from aiohttp import web
from server import PromptServer
import folder_paths
from .apex_lora_loader import ApexLoraLoader

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("[Apex LoRA API] Warning: Pillow not available. Thumbnails will not be optimized.")

class ApexLoraAPI:
    def __init__(self):
        self.setup_routes()
    
    def generate_thumbnail(self, source_path, output_path):
        """
        Generate an optimized 256x256 square thumbnail from source image
        
        Supports all image formats including GIF (extracts first frame).
        Intelligently upscales small images and downscales large images.
        Creates square thumbnails with proper centering.
        
        Args:
            source_path: Path to original image (any format: PNG, JPG, GIF, WEBP, etc.)
            output_path: Path to save thumbnail (always JPEG at 256x256)
        
        Returns:
            True if successful, False otherwise
        """
        if not PIL_AVAILABLE:
            return False
        
        try:
            # Open image
            with Image.open(source_path) as img:
                # For animated images (GIF, WEBP), extract first frame
                if hasattr(img, 'is_animated') and img.is_animated:
                    img.seek(0)  # Go to first frame
                    img = img.copy()  # Create a copy of the first frame
                
                # Convert to RGB (handles RGBA, P, L, CMYK, etc.)
                if img.mode != 'RGB':
                    # For transparency (RGBA, LA, P with transparency), use white background
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        # Create white background
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Get original dimensions
                width, height = img.size
                
                # Create 1:1 square thumbnail
                # Step 1: Crop to square (center crop)
                if width != height:
                    # Find the smaller dimension
                    size = min(width, height)
                    
                    # Calculate crop box for center crop
                    left = (width - size) // 2
                    top = (height - size) // 2
                    right = left + size
                    bottom = top + size
                    
                    img = img.crop((left, top, right, bottom))
                
                # Step 2: Resize to 256x256
                current_size = img.size[0]  # Now it's square, so width = height
                
                if current_size != 256:
                    # Resize using LANCZOS for quality (handles both upscale and downscale)
                    img = img.resize((256, 256), Image.Resampling.LANCZOS)
                
                # Save as optimized JPEG
                img.save(output_path, 'JPEG', quality=85, optimize=True)
                
            return True
        except Exception as e:
            print(f"[Apex LoRA API] Error generating thumbnail: {e}")
            return False
    
    def get_thumbnail_path(self, original_path):
        """
        Get the path for a 256px thumbnail, creating it if it doesn't exist
        
        Thumbnails are stored in a .thumbnails subfolder in the same directory
        as the original preview image.
        
        Args:
            original_path: Path to original preview image
        
        Returns:
            Path to thumbnail file, or original path if thumbnail generation fails
        """
        if not PIL_AVAILABLE or not original_path or not os.path.exists(original_path):
            return original_path
        
        try:
            # Get the directory containing the original image
            source_dir = os.path.dirname(original_path)
            
            # Create .thumbnails subdirectory in the same folder
            thumbnails_dir = os.path.join(source_dir, ".thumbnails")
            
            if not os.path.exists(thumbnails_dir):
                try:
                    os.makedirs(thumbnails_dir)
                    print(f"[Apex LoRA API] Created thumbnails directory: {thumbnails_dir}")
                except Exception as e:
                    print(f"[Apex LoRA API] Error creating thumbnails directory: {e}")
                    return original_path
            
            # Create thumbnail filename (just the base name with .jpg extension)
            base_name = os.path.splitext(os.path.basename(original_path))[0]
            thumbnail_name = f"{base_name}.jpg"
            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_name)
            
            # Check if thumbnail already exists
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            
            # Generate thumbnail (always 256x256)
            if self.generate_thumbnail(original_path, thumbnail_path):
                print(f"[Apex LoRA API] Generated thumbnail: {thumbnail_name}")
                return thumbnail_path
            else:
                return original_path
                
        except Exception as e:
            print(f"[Apex LoRA API] Error in get_thumbnail_path: {e}")
            return original_path

    def setup_routes(self):
        """Setup API routes for LoRA preview management"""
        
        @PromptServer.instance.routes.post("/apex/lora_list_folder")
        async def list_lora_folder(request):
            """List folders and LoRAs in a specific folder"""
            try:
                data = await request.json()
                folder_path = data.get("folder_path", "")  # Relative to loras root
                
                # Get loras root directories
                lora_folders = folder_paths.get_folder_paths("loras")
                if not lora_folders:
                    return web.json_response({"error": "No loras folder configured"}, status=500)
                
                # Use first loras folder as base
                loras_root = lora_folders[0]
                
                # Build full path
                if folder_path:
                    full_path = os.path.join(loras_root, folder_path)
                else:
                    full_path = loras_root
                
                # Security check: resolve symlinks and ensure path is within loras directory
                full_path_real = os.path.realpath(full_path)
                loras_root_real = os.path.realpath(loras_root)
                
                if not full_path_real.startswith(loras_root_real):
                    return web.json_response({"error": "Invalid path"}, status=403)
                
                # Use the resolved path for operations
                full_path = full_path_real
                
                if not os.path.exists(full_path):
                    return web.json_response({"error": "Folder not found"}, status=404)
                
                # List directory contents
                folders = []
                loras = []
                
                try:
                    entries = os.listdir(full_path)
                    for entry in sorted(entries):
                        entry_path = os.path.join(full_path, entry)
                        
                        if os.path.isdir(entry_path):
                            folders.append(entry)
                        elif entry.endswith(('.safetensors', '.ckpt', '.pt', '.pth')):
                            # Build relative path for this LoRA
                            if folder_path:
                                lora_relative = os.path.join(folder_path, entry).replace('\\', '/')
                            else:
                                lora_relative = entry
                            
                            # Get preview path
                            preview_path = ApexLoraLoader.get_preview_path(lora_relative)
                            has_preview = preview_path is not None
                            
                            loras.append({
                                "name": entry,
                                "relative_path": lora_relative,
                                "has_preview": has_preview,
                                "size": os.path.getsize(entry_path)
                            })
                except Exception as e:
                    print(f"[Apex LoRA API] Error reading folder: {e}")
                    return web.json_response({"error": str(e)}, status=500)
                
                # Determine parent folder
                parent_folder = None
                if folder_path:
                    parent_parts = folder_path.replace('\\', '/').split('/')
                    if len(parent_parts) > 1:
                        parent_folder = '/'.join(parent_parts[:-1])
                    else:
                        parent_folder = ""
                
                return web.json_response({
                    "current_folder": folder_path,
                    "parent_folder": parent_folder,
                    "folders": folders,
                    "loras": loras,
                    "total_loras": len(loras)
                })
                
            except Exception as e:
                print(f"[Apex LoRA API] Error listing folder: {e}")
                return web.json_response({"error": str(e)}, status=500)
        
        @PromptServer.instance.routes.post("/apex/lora_preview")
        async def get_lora_preview(request):
            """Get the preview image path for a LoRA file"""
            try:
                data = await request.json()
                lora_name = data.get("lora_name")
                
                if not lora_name:
                    return web.json_response({"error": "No lora_name provided"}, status=400)
                
                # Use the static method from ApexLoraLoader to find preview
                preview_path = ApexLoraLoader.get_preview_path(lora_name)
                
                if preview_path and os.path.exists(preview_path):
                    return web.json_response({"preview_path": preview_path})
                else:
                    return web.json_response({"preview_path": None})
                    
            except Exception as e:
                print(f"[Apex LoRA API] Error getting preview: {e}")
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.get("/apex/lora_image")
        async def serve_lora_image(request):
            """Serve optimized 256px thumbnail"""
            try:
                image_path = request.query.get("path")
                
                if not image_path:
                    return web.Response(status=400, text="No path provided")
                
                if not os.path.exists(image_path):
                    return web.Response(status=404, text="Image not found")
                
                # Security check: resolve symlinks and ensure the path is within the loras directory
                lora_folders = folder_paths.get_folder_paths("loras")
                
                # Normalize and resolve symlinks
                try:
                    image_path_real = os.path.realpath(os.path.abspath(image_path))
                except (OSError, ValueError):
                    return web.Response(status=403, text="Invalid path")
                
                is_safe = False
                
                for lora_folder in lora_folders:
                    try:
                        lora_folder_real = os.path.realpath(os.path.abspath(lora_folder))
                        # Use startswith with os.sep to prevent path traversal
                        # Ensure we check for directory boundary (path separator)
                        if image_path_real.startswith(lora_folder_real + os.sep) or image_path_real == lora_folder_real:
                            is_safe = True
                            break
                    except (OSError, ValueError):
                        continue
                
                if not is_safe:
                    return web.Response(status=403, text="Access denied")
                
                # Get optimized 256px thumbnail
                optimized_path = self.get_thumbnail_path(image_path)
                if optimized_path != image_path:
                    image_path = optimized_path
                
                # Determine content type based on extension
                ext = os.path.splitext(image_path)[1].lower()
                content_type = {
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                }.get(ext, 'application/octet-stream')
                
                # Read and serve the file using aiofiles for async I/O
                async with aiofiles.open(image_path, 'rb') as f:
                    image_data = await f.read()
                
                return web.Response(
                    body=image_data,
                    content_type=content_type,
                    headers={
                        'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                    }
                )
                
            except Exception as e:
                print(f"[Apex LoRA API] Error serving image: {e}")
                return web.Response(status=500, text=str(e))

# Initialize the API
api_instance = ApexLoraAPI()
