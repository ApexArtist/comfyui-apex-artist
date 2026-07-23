
## Architecture
- **Python backend**: Individual `apex_*.py` files at root level
- **JavaScript frontend**: Custom widgets in `web/` directory (where needed)
- **API routes**: Initialized via module import (e.g., `apex_lora_api`)
- **Registration**: Via `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` in `__init__.py`

## Node Definition Pattern
```python
class ApexNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"image": ("IMAGE",)},
            "optional": {}
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "Apex Artist/Subcategory"
    
    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        """Optional: Validate inputs dynamically at execution time"""
        return True
```

### Dynamic Input Validation Pattern
When a node's input values can be set programmatically (e.g., via browser UI) and need validation beyond a static list, use the `VALIDATE_INPUTS` classmethod:

```python
@classmethod
def VALIDATE_INPUTS(cls, input_name, **kwargs):
    """
    Validate input at execution time instead of against static INPUT_TYPES list.
    This allows browser/API to set values not in the initial dropdown.
    
    Returns:
        True if valid
        Error string if invalid
    """
    if not folder_paths.get_full_path("folder_type", input_name):
        return f"Invalid file: {input_name}"
    return True
```

**Use case**: ApexLoraLoader uses this to validate LoRA files selected from the browser. The `INPUT_TYPES` provides the initial dropdown list, but `VALIDATE_INPUTS` allows any valid path including subdirectories.

## Key Patterns

### Native-First ComfyUI Integration Rule
Always prefer ComfyUI's native mechanisms and LiteGraph conventions before adding custom frontend behavior. If native nodes already solve a rendering, widget, sizing, upload, preview, or execution-sync problem, follow that path instead of inventing a custom one.

**Examples:**
- Use `node.imgs` for node image previews rather than a custom canvas widget.
- Preserve user-controlled node size when changing preview images, matching native Load Image behavior.
- Use ComfyUI widget metadata such as `{ "image_upload": True }` for upload behavior.
- Use native canvas dirty/redraw calls for refreshes instead of forcing layout recomputation.

**Avoid:** custom draw/layout logic, forced resizing, invisible DOM overlays, or custom state machines when native ComfyUI APIs already provide the behavior.

### Class-Level Input Population
- `INPUT_TYPES()` called at class level during node discovery
- Use `@staticmethod` or `@classmethod` for methods called by `INPUT_TYPES()`

### Category Convention
- Top-level: `"Apex Artist"`
- Subcategories: `Image`, `Image/Filters`, `Image/Composite`, `Models`, `Text`, `Video`

### Input/Output Types
- **IMAGE**: `torch.Tensor` (B,H,W,3), float32 [0,1]
- **MASK**: `torch.Tensor` (B,H,W), float32
- **MODEL/CLIP/VAE**: ComfyUI wrapper objects (see MODEL Socket Data below)
- **INT/FLOAT/STRING**: Python primitives

### MODEL Socket Data (Critical for LoRA Extraction)
When a MODEL is passed through sockets (from CheckpointLoader, Kijai's loader, ApexLoadModel, etc.):

**What the MODEL object contains:**
- `model.model.diffusion_model` - The actual UNet/DiT neural network
  - `.state_dict()` - Returns model weights with their **current in-memory dtypes**
  - `.dtype` - Current weight precision (torch.float8_e4m3fn, torch.float16, torch.bfloat16, torch.float32)
- `model.model_config` - Model configuration (architecture, latent format, etc.)
- `model.model.manual_cast_dtype` - Manual casting dtype if set
- `model.set_model_compute_dtype(dtype)` - Method to set computation precision
- `model.force_cast_weights` - Boolean flag for forced casting on forward pass

**What model_options passes during loading:**
- `dtype` - Weight storage precision (FP8, FP16, BF16, FP32)
- `fp8_optimizations` - Enable FP8 fast path (bool)
- Model-specific architecture options

**Critical for nodes that process models:**
1. **Always access** `model.model.diffusion_model.state_dict()` for weights
2. **Check tensor dtypes** - they reflect the loader's choices (FP8, FP16, etc.)
3. **Handle mixed precision** - finetuned and base models may have different dtypes
4. **Use safe conversions** - FP8 requires two-step conversion (FP8→FP16→target) to avoid access violations on Windows
5. **Respect upstream choices** - don't force conversions unless necessary

### Error Handling
```python
try:
    # process
except Exception as e:
    print(f"[Apex] Error: {e}")
    return (torch.zeros((1,1,1,3), dtype=torch.float32),)
```

### Modal Browser Pattern (ApexLoraLoader)
- Interactive modal with overlay
- Responsive CSS Grid: `repeat(auto-fill, minmax(100px, 1fr))`
- DOM-based navigation (folders, breadcrumbs)
- State management in node instance

### Native Node Image Preview Pattern
For image previews displayed on a ComfyUI node, prefer ComfyUI/LiteGraph's native image preview renderer instead of a custom `addCustomWidget()` canvas draw function. Match native Load Image behavior: changing the image should redraw the preview but should not auto-resize the node.

**Use this pattern:**
```javascript
function refreshNodePreview(node) {
    if (node.setDirtyCanvas) node.setDirtyCanvas(true, true);
    else node.graph?.setDirtyCanvas(true, true);
}

const img = new Image();
img.onload = () => {
    node.imgs = [img];
    node.imageIndex = 0;
    refreshNodePreview(node);
};
img.onerror = () => {
    node.imgs = [];
    refreshNodePreview(node);
};
img.src = imageUrl;
```

Clear the preview when no image is available:
```javascript
node.imgs = [];
refreshNodePreview(node);
```

**Important:** Avoid manually drawing node image previews with `ctx.drawImage()` inside custom widgets. Manual widget drawing can become misaligned with ComfyUI's node layout, causing stretched, shifted, overlapped, or clipped previews. Also avoid `node.setSize(node.computeSize())` during image changes unless explicitly implementing a one-time initial sizing behavior; repeated calls cause unwanted auto-resizing. `ApexLoraLoader` now uses `node.imgs` for selected LoRA preview images and only dirties the canvas on image changes.

### Widget Value Change Detection
```javascript
// Property hook to intercept ALL value changes
const internalKey = '_apexValue';
widget[internalKey] = widget.value || "";

Object.defineProperty(widget, 'value', {
    get: function() { return this[internalKey]; },
    set: function(newValue) {
        const oldValue = this[internalKey];
        this[internalKey] = newValue;
        if (oldValue !== newValue) {
            onValueChanged(newValue);
        }
    }
});
```

### Thumbnail Optimization
- **Storage**: `.thumbnails/` subfolder in each LoRA directory
- **Size**: 256x256px square thumbnails only
- **Process**: Center crop → resize (LANCZOS) → save JPEG quality 85
- **Formats**: All image types (PNG, JPG, GIF, WEBP, BMP, TIFF)
- **On-demand generation**: Created when first requested

### Secure File Serving
- Path normalization and validation
- Restrict to specific directories
- Prevent directory traversal
- Proper MIME types and caching headers

## Component Files

### Nodes
- `apex_blur.py`, `apex_sharpen.py`
- `apex_depth_to_normal.py`, `apex_layer_blend.py`
- `apex_prompt.py`, `apex_lora_loader.py`

### APIs
- `apex_prompt_api.py` - Prompt preset CRUD
- `apex_lora_api.py` - LoRA folder listing and image serving

### Web UI
- `web/apex_prompt.js` - Prompt preset UI
- `web/apex_lora_loader.js` - Interactive LoRA browser