from .apex_depth_to_normal import ApexDepthToNormal
from .apex_layer_blend import ApexLayerBlend
from .apex_blur import ApexBlur
from .apex_sharpen import ApexSharpen
from .apex_prompt import ApexPromptPreset
from .apex_lora_loader import ApexLoraLoader
from .apex_lora_merge import ApexLoRAMerge

# Import quantizer nodes (optional dependency)
try:
    from .apex_quantizer import NODE_CLASS_MAPPINGS as QUANT_NODE_CLASS_MAPPINGS
    from .apex_quantizer import NODE_DISPLAY_NAME_MAPPINGS as QUANT_NODE_DISPLAY_NAME_MAPPINGS
    QUANTIZER_AVAILABLE = True
except ImportError:
    QUANTIZER_AVAILABLE = False
    QUANT_NODE_CLASS_MAPPINGS = {}
    QUANT_NODE_DISPLAY_NAME_MAPPINGS = {}

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
    "ApexLoRAMerge": ApexLoRAMerge,
}
NODE_CLASS_MAPPINGS.update(QUANT_NODE_CLASS_MAPPINGS)

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexDepthToNormal": "Apex Depth to Normal",
    "ApexLayerBlend": "Apex Layer Blend",
    "ApexBlur": "Apex Blur",
    "ApexSharpen": "Apex Sharpen",
    "ApexPromptPreset": "Apex Prompt Preset Selector",
    "ApexLoraLoader": "Apex LoRA Loader",
    "ApexLoRAMerge": "Apex LoRA Merge",
}
NODE_DISPLAY_NAME_MAPPINGS.update(QUANT_NODE_DISPLAY_NAME_MAPPINGS)

WEB_DIRECTORY = "./web"