# Active Context: comfyui-apex-artist

## Current Focus (2026-07-23) - v2.1.0 Cleanup & Optimization

### ApexLoadModel Removed ✅
The `ApexLoadModel` node has been **removed entirely** from the project:
- `apex_load_model.py` deleted — the node was redundant with ComfyUI's native `CheckpointLoaderSimple` and other model loaders
- `__init__.py` updated — import and mappings removed
- `web/apex_load_model.js` already deleted in previous cleanup
- `apex_load_model_fixes.md` moved to `memory-bank/` for historical reference

### Completed Tasks (2026-07-23)
1. ✅ **ApexLoadModel removed**: Deleted node file, cleaned up registration, moved fix docs to memory-bank
2. ✅ **Apex Prompt Lens JS cleanup**: Deleted `web/apex_prompt_lens.js` — it was a complete no-op (empty `beforeRegisterNodeDef` hook, no functional code)
3. ✅ **Stale references cleaned**: Removed deleted `apex_prompt_lens.js` mentions from memory-bank files
4. ✅ **`.gitignore` updated**: Added `.clineignore` entry

## Recent Changes (2026-07-23)
- **apex_load_model.py**: DELETED — node removed (redundant with native ComfyUI loaders)
- **__init__.py**: Removed ApexLoadModel import and mappings
- **web/apex_load_model.js**: Already deleted in previous cleanup
- **web/apex_prompt_lens.js**: DELETED — was a no-op extension
- **apex_load_model_fixes.md**: MOVED to `memory-bank/apex_load_model_fixes.md`

## Active Nodes (6 registered)
| Node | Display Name | Category | Description |
|------|--------------|----------|-------------|
| | ApexPromptPreset | **Apex Prompt** | Text | 55 presets across Environment/Lighting/Style/Camera Lens categories |
| | ApexLoraLoader | Apex LoRA Loader | Models | LoRA loader with interactive browser and native `node.imgs` preview |
| | ApexBlur | Apex Blur | Image/Filters | 9 blur algorithms |
| | ApexSharpen | Apex Sharpen | Image/Filters | 8 edge-aware sharpening algorithms |
| | ApexLayerBlend | Apex Layer Blend | Image/Composite | 25+ Photoshop-style blend modes |
| | ApexDepthToNormal | Apex Depth to Normal | Image/Composite | Depth → normal map conversion |

## Important Patterns (Updated)
- **Error resilience**: Nodes return placeholder tensors on failure
- **Class-level safety**: Methods used by `INPUT_TYPES()` must be `@staticmethod` or `@classmethod`
- **Native-first rule**: Always use ComfyUI's native mechanisms and conventions when available. Do not invent custom UI/rendering/layout behavior when a native ComfyUI/LiteGraph path exists.
- **Property hook pattern**: Use `Object.defineProperty()` to intercept widget value changes
- **Native node image preview pattern**: For frontend node preview images, load a browser `Image`, then assign `node.imgs = [img]` and `node.imageIndex = 0`; clear with `node.imgs = []`. Redraw with `node.setDirtyCanvas(true, true)` or `node.graph?.setDirtyCanvas(true, true)`. Do **not** call `node.setSize(node.computeSize())` on every image change; preserve the user's node size like native Load Image behavior.
- **Shared utilities**: Use `apex_utils.py` for common operations (blur, validation, color conversion)
- **Async I/O**: API handlers use aiofiles for non-blocking file operations
- **Tuple returns from presets**: All `_get_preset_text()` calls now return `(name, text)` tuples

## Documentation Structure
- **features.md**: Comprehensive feature documentation
- **systemPatterns.md**: Architecture and technical patterns  
- **techContext.md**: Technologies and dependencies
- **progress.md**: Project status and milestones
- **PUBLISH.md**: Publishing workflow guide

## Version Management
- **Current**: 2.1.0
- **Script**: `update_version.py` with `--patch`, `--minor`, `--major`, `--commit`, `--tag` flags
