# System Patterns: comfyui-apex-artist

## Architecture
- **Python backend**: Individual `apex_*.py` files at root level
- **JavaScript frontend**: Custom widgets in `web/` directory
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
```

## Key Patterns

### Class-Level Input Population
- `INPUT_TYPES()` called at class level during node discovery
- Use `@staticmethod` or `@classmethod` for methods called by `INPUT_TYPES()`

### Category Convention
- Top-level: `"Apex Artist"`
- Subcategories: `Image`, `Image/Filters`, `Image/Composite`, `Models`, `Text`, `Video`

### Input/Output Types
- **IMAGE**: `torch.Tensor` (B,H,W,3), float32 [0,1]
- **MASK**: `torch.Tensor` (B,H,W), float32
- **MODEL/CLIP**: ComfyUI objects
- **INT/FLOAT/STRING**: Python primitives

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
- `apex_smart_resize.py`, `apex_blur.py`, `apex_sharpen.py`
- `apex_depth_to_normal.py`, `apex_layer_blend.py`
- `apex_prompt.py`, `apex_lora_loader.py`

### APIs
- `apex_prompt_api.py` - Prompt preset CRUD
- `apex_lora_api.py` - LoRA folder listing and image serving

### Web UI
- `web/apex_prompt.js` - Prompt preset UI
- `web/apex_lora_loader.js` - Interactive LoRA browser
