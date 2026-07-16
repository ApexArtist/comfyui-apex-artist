#!/usr/bin/env python3
"""
Apex LoRA Loader Node - Load LoRA models with thumbnail preview
Simple, single-strength LoRA loader with visual preview support
"""
import os
import folder_paths
import comfy.utils

class ApexLoraLoader:
    """
    Professional LoRA loader with thumbnail preview support
    
    Features:
    - Single unified strength slider for model and CLIP
    - Automatic thumbnail preview (searches for .png, .jpg, .preview.png, .preview.jpg)
    - Clean, simple interface
    - Full compatibility with ComfyUI's LoRA system
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "lora_name": (folder_paths.get_filename_list("loras"), ),
                "strength": ("FLOAT", {
                    "default": 1.0,
                    "min": -10.0,
                    "max": 10.0,
                    "step": 0.01
                }),
            },
            "optional": {
                "clip": ("CLIP",),
            }
        }
    
    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("model", "clip")
    FUNCTION = "load_lora"
    CATEGORY = "Apex Artist/Models"
    DESCRIPTION = "Load LoRA models with thumbnail preview. CLIP input is optional - applies strength to model and CLIP if connected."

    def load_lora(self, model, lora_name, strength, clip=None):
        """
        Load and apply LoRA to model and optionally CLIP
        
        Args:
            model: Input MODEL
            lora_name: LoRA filename from loras folder
            strength: Strength multiplier (applied to both model and CLIP)
            clip: Input CLIP (optional)
            
        Returns:
            Tuple of (modified_model, modified_clip or None)
        """
        if strength == 0:
            return (model, clip)
        
        # Get the full path to the LoRA file
        lora_path = folder_paths.get_full_path("loras", lora_name)
        
        if lora_path is None:
            print(f"[Apex LoRA Loader] Warning: LoRA file not found: {lora_name}")
            return (model, clip)
        
        try:
            # Load the LoRA
            lora = comfy.utils.load_torch_file(lora_path, safe_load=True)
            
            # Apply to model and CLIP (if provided) with the same strength
            if clip is not None:
                model_lora, clip_lora = comfy.sd.load_lora_for_models(
                    model, 
                    clip, 
                    lora, 
                    strength,  # model strength
                    strength   # clip strength
                )
                return (model_lora, clip_lora)
            else:
                # CLIP not provided, only apply to model
                model_lora, _ = comfy.sd.load_lora_for_models(
                    model, 
                    None,  # No CLIP
                    lora, 
                    strength,  # model strength
                    0          # clip strength (ignored when clip is None)
                )
                return (model_lora, None)
            
        except Exception as e:
            print(f"[Apex LoRA Loader] Error loading LoRA '{lora_name}': {e}")
            return (model, clip)
    
    @staticmethod
    def get_preview_path(lora_name):
        """
        Find the preview image for a LoRA file
        
        Searches for preview images in this order:
        1. <lora_name>.preview.png
        2. <lora_name>.preview.jpg
        3. <lora_name>.png
        4. <lora_name>.jpg
        
        Args:
            lora_name: LoRA filename (e.g., "my_lora.safetensors")
            
        Returns:
            Full path to preview image, or None if not found
        """
        lora_path = folder_paths.get_full_path("loras", lora_name)
        if not lora_path:
            return None
        
        # Get base path without extension
        base_path = os.path.splitext(lora_path)[0]
        
        # Check for preview images in order of preference
        # Supports all common image formats
        preview_extensions = [
            ".preview.png",
            ".preview.jpg",
            ".preview.jpeg",
            ".preview.gif",
            ".preview.webp",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".bmp",
            ".tiff",
            ".tif"
        ]
        
        for ext in preview_extensions:
            preview_path = base_path + ext
            if os.path.exists(preview_path):
                return preview_path
        
        return None
