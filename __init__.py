
from .apex_smart_resize import ApexSmartResize
from .apex_depth_to_normal import ApexDepthToNormal
from .apex_layer_blend import ApexLayerBlend
from .apex_blur import ApexBlur
from .apex_sharpen import ApexSharpen
from .apex_rgb_curve import ApexRGBCurve
from .apex_upscale import ApexUpscaleBy
from .apex_random_prompt import ApexPromptPreset
from .apex_load_image import ApexLoadImage
from .apex_latent_noise import ApexLatentNoise
from .apex_last_frame import ApexLastFrame, ApexGetFrame, ApexBatchInfo
from .apex_json_node import ApexJSON
from .apex_palette import ApexPalette

# Import API server to initialize routes
try:
    from . import apex_prompt_preset_api
except ImportError:
    print("Warning: Could not import apex_prompt_preset_api")

NODE_CLASS_MAPPINGS = {
    "ApexSmartResize": ApexSmartResize,
    "ApexDepthToNormal": ApexDepthToNormal,
    "ApexLayerBlend": ApexLayerBlend,
    "ApexBlur": ApexBlur,
    "ApexSharpen": ApexSharpen,
    "ApexRGBCurve": ApexRGBCurve,
    "ApexUpscaleBy": ApexUpscaleBy,
    "ApexPromptPreset": ApexPromptPreset,
    "ApexLoadImage": ApexLoadImage,
    "ApexPalette": ApexPalette,
    "ApexLatentNoise": ApexLatentNoise,
    "ApexLastFrame": ApexLastFrame,
    "ApexGetFrame": ApexGetFrame,
    "ApexBatchInfo": ApexBatchInfo,
    "ApexJSON": ApexJSON,
    
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexSmartResize": "Apex Smart Resize",
    "ApexDepthToNormal": "Apex Depth to Normal",
    "ApexLayerBlend": "Apex Layer Blend",
    "ApexBlur": "Apex Blur",
    "ApexSharpen": "Apex Sharpen",
    "ApexRGBCurve": "Apex RGB Curve",
    "ApexPalette": "Apex Palette",
    "ApexUpscaleBy": "Apex Upscale By Ratio",
    "ApexPromptPreset": "Apex Random Prompt",
    # ApexAutoPrompt removed
    "ApexLoadImage": "Apex Load Image",
    "ApexImageToPrompt": "Apex Image → Prompt",
    "ApexLastFrame": "Apex Last Frame",
    "ApexGetFrame": "Apex Get Frame",
    "ApexBatchInfo": "Apex Batch Info",
    "ApexJSON": "Apex JSON Lookup",
    
}

WEB_DIRECTORY = "./web"
