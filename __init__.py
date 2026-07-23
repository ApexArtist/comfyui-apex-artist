NODE_VERSION = "2.1.0"

from .apex_depth_to_normal import ApexDepthToNormal
from .apex_layer_blend import ApexLayerBlend
from .apex_blur import ApexBlur
from .apex_sharpen import ApexSharpen
from .apex_prompt import ApexPromptPreset
from .apex_lora_loader import ApexLoraLoader
from .apex_load_model import ApexLoadModel

# Import API servers to initialize routes
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

NODE_CLASS_MAPPINGS = {
    "ApexDepthToNormal": ApexDepthToNormal,
    "ApexLayerBlend": ApexLayerBlend,
    "ApexBlur": ApexBlur,
    "ApexSharpen": ApexSharpen,
    "ApexPromptPreset": ApexPromptPreset,
    "ApexLoraLoader": ApexLoraLoader,
    "ApexLoadModel": ApexLoadModel,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexDepthToNormal": "Apex Depth to Normal",
    "ApexLayerBlend": "Apex Layer Blend",
    "ApexBlur": "Apex Blur",
    "ApexSharpen": "Apex Sharpen",
    "ApexPromptPreset": "Apex Prompt",
    "ApexLoraLoader": "Apex LoRA Loader",
    "ApexLoadModel": "Apex Load Model",
}

WEB_DIRECTORY = "./web"