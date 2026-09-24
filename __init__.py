NODE_VERSION = "2.3.0"

from .apex_depth_to_normal import ApexDepthToNormal
from .apex_layer_blend import ApexLayerBlend
from .apex_blur import ApexBlur
from .apex_sharpen import ApexSharpen
from .apex_prompt import ApexPromptPreset
from .apex_character_prompt import ApexCharacterPrompt
from .apex_lora_loader import ApexLoraLoader
from .apex_hdri_viewer import ApexHDRIViewer
from .apex_json_node import ApexJSON

# Import API servers to initialize routes
try:
    from . import apex_character_prompt_api
except ImportError:
    print("Warning: Could not import apex_character_prompt_api")

try:
    from . import apex_prompt_api
except ImportError:
    print("Warning: Could not import apex_prompt_api")

try:
    from . import apex_lora_api
except ImportError:
    print("Warning: Could not import apex_lora_api")

try:
    from . import apex_prompt_lens_api
except ImportError:
    print("Warning: Could not import apex_prompt_lens_api")

try:
    from . import apex_hdri_preview_api
except ImportError:
    print("Warning: Could not import apex_hdri_preview_api")

NODE_CLASS_MAPPINGS = {
    "ApexDepthToNormal": ApexDepthToNormal,
    "ApexLayerBlend": ApexLayerBlend,
    "ApexBlur": ApexBlur,
    "ApexSharpen": ApexSharpen,
    "ApexPromptPreset": ApexPromptPreset,
    "ApexCharacterPrompt": ApexCharacterPrompt,
    "ApexLoraLoader": ApexLoraLoader,
    "ApexHDRIViewer": ApexHDRIViewer,
    "ApexJSON": ApexJSON,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexDepthToNormal": "Apex Depth to Normal",
    "ApexLayerBlend": "Apex Layer Blend",
    "ApexBlur": "Apex Blur",
    "ApexSharpen": "Apex Sharpen",
    "ApexPromptPreset": "Apex Prompt",
    "ApexCharacterPrompt": "Apex Character Prompt",
    "ApexLoraLoader": "Apex LoRA Loader",
    "ApexHDRIViewer": "Apex HDRI Viewer",
    "ApexJSON": "Apex JSON Lookup",
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]