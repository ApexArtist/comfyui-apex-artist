# Progress: comfyui-apex-artist

## Active Nodes (7)

### Image Processing
- **ApexBlur**: 9 blur algorithms
- **ApexSharpen**: 8 edge-aware sharpening algorithms
- **ApexDepthToNormal**: Depth → normal map conversion
- **ApexLayerBlend**: 25+ Photoshop-style blending modes

### Workflow & Models
- **ApexPromptPreset**: 55 presets across 3 categories
- **ApexLoraLoader**: Interactive browser with folder navigation and thumbnails
- **ApexLoadModel**: Advanced model loader with dtype selection (fp16/bf16/fp8/fp32)

## Infrastructure
- Web UI extensions: `apex_prompt.js`, `apex_lora_loader.js`, `apex_load_model.js`, `apex_prompt_lens.js`
- API endpoints: `apex_prompt_api.py`, `apex_lora_api.py`, `apex_prompt_lens_api.py`
- CI/CD: GitHub Actions for ComfyUI Registry
- Version management: `update_version.py` (enhanced with auto-increment and git integration)
- Publishing guide: `PUBLISH.md` (comprehensive workflow documentation)

## Current Status
**Production/Stable v2.0.2** - Professional VFX and image processing with 7 core nodes. Health Score: 9.5/10 ✅

## Recent Updates (July 2026)

### Apex LoRA Loader Native Preview Fix (2026-07-21)
- **Selected Preview Rendering**: Updated `web/apex_lora_loader.js` to use ComfyUI's native node preview mechanism (`node.imgs = [img]`, `node.imageIndex = 0`) instead of a custom `addCustomWidget()` canvas draw.
- **Native Load Image-like Sizing**: Removed forced `node.setSize(node.computeSize())` calls from preview image changes. LoRA preview updates now redraw inside the current node size, preserving manual node sizing like native Load Image.
- **User Impact**: Selected LoRA preview now behaves like native Preview Image / Load Image previews and no longer appears messy, stretched, shifted, overlapped, clipped, or auto-resized.
- **Documentation**: Added native node image preview pattern and native-first rule to `systemPatterns.md`, `domWidgetPatterns.md`, `features.md`, and `activeContext.md` so future agents follow ComfyUI-native behavior first.

### v2.0.3 Cleanup & Optimize (2026-07-19)
- **Node Removal**: Removed ApexLoRAExtract, ApexLoRAMerge, and ApexModelQuantizer
- **Documentation Cleanup**: Removed APEX_LORA_EXTRACT_ADAPTIVE.md, APEX_LORA_MERGE_ADAPTIVE.md, APEX_LORA_MERGE.md
- **Simplified Focus**: Streamlined to core VFX and image processing features
- **Memory Bank Updated**: Cleaned all references to removed nodes
- **Code Deduplication**: 
  - `apex_layer_blend.py` → uses shared `rgb_to_hsl()`, `hsl_to_rgb()`, `calculate_luminance()` from `apex_utils.py` (removed 80+ lines)
  - `apex_sharpen.py` → uses shared `calculate_luminance()` (4 instances)
- **Performance Optimizations**:
  - `apex_blur.py`: Grouped convolution for 3-4x faster box/lens blur
  - `apex_blur.py`: LRU kernel cache (`@lru_cache`) avoids recomputation
  - `apex_blur.py`: Pre-permuted tensors in radial/spin/zoom blur loops
- **Code Quality**:
  - `apex_prompt.py`: Thread-safe cache with double-checked locking
  - `apex_prompt.py`: Removed inline `import random` statements
  - `apex_prompt.py`: Fixed global `random.seed()` pollution → local `Random()` instances
- **File Cleanup**:
  - `check_model_options.py` → `scripts/check_model_options.py` (fixed hardcoded path)
  - Removed old `check_model_options.py` from root

### v2.0.2 Release (2026-07-18)
- **ApexSmartResize Removed**: Redundant functionality, cleaned up codebase
- **README.md Updated**: More concise documentation
- **PUBLISH.md Created**: Comprehensive publishing workflow guide
- **update_version.py Enhanced**: Auto-increment flags (--patch/--minor/--major), dry-run mode, git integration (--commit/--tag), colored output, current version detection

### v1.7.0 Release
- **ApexLoraLoader**: New node with interactive browser, folder navigation, optimized thumbnails
- **Thumbnail System**: 256px/512px two-tier caching, 100-500x file size reduction
- **Node Freeze Fix**: Deferred collapse, error boundaries, requestAnimationFrame updates
- **ApexSmartResize**: Added 6 new 2026 model presets (ZImage, QwenEdit, Krea2, Ideogram4, FLUX.2, SD3.5)
- **Divisibility Control**: New parameter for dimension enforcement (8/16/32/64)
- **Documentation Consolidation**: Created features.md, cleaned 10 redundant files
- **Camera Lens Browser**: Interactive lens browser with 43 visual thumbnails integrated into ApexPromptPreset
  - 6 color-coded categories (Standard, Wide Angle, Portrait, Telephoto, Special Effects, Cinema)
  - Generated 256×256 framing diagrams showing lens characteristics
  - Smart visibility: Toggle hidden when "Disabled" or "Random" selected
  - Backend API (`apex_prompt_lens_api.py`) with 3 endpoints
  - Frontend browser (`web/apex_prompt_lens.js`, 500+ lines)

## Completed Items (July 2026)
- [x] ApexLoraLoader implementation with browser and thumbnails
- [x] Documentation consolidation (10 files → features.md)
- [x] Category standardization across all nodes
- [x] Node freeze bug fix with deferred collapse
- [x] Camera Lens Browser with 43 visual thumbnails
- [x] Smart visibility logic for lens browser toggle button
- [x] Memory bank documentation updates
- [x] ApexSmartResize node removal (v2.0.2)
- [x] PUBLISH.md creation with comprehensive workflow guide
- [x] update_version.py enhancement with auto-increment and git features
- [x] ApexLoRAExtract, ApexLoRAMerge, ApexModelQuantizer removal (v2.0.3)
- [x] Project cleanup and documentation updates (v2.0.3)
- [x] HSL/luminance deduplication in apex_layer_blend.py
- [x] Luminance deduplication in apex_sharpen.py
- [x] Grouped convolution + kernel cache in apex_blur.py
- [x] Thread-safe cache + inline import fix in apex_prompt.py
- [x] Fixed hardcoded path in check_model_options.py, moved to scripts/
- [x] ApexLoraLoader selected preview uses native `node.imgs` rendering
- [x] ApexLoraLoader preview image changes preserve node size like native Load Image

## Outstanding Items
- [ ] Automated test suite (Priority 3)
- [ ] Optional: File naming consistency `apex_prompt.py` → `apex_prompt_preset.py` (Priority 2)
- [ ] Optional: Batch operation optimization for radial/spin/zoom blur (2-3x speedup)
- [ ] Optional: Async I/O fix for 3 API handlers (low priority)

## Next Milestones
1. **v2.1.0** - Code quality improvements (apex_utils integration, async I/O fixes)
2. **v2.2.0** - Testing framework and automated test coverage
3. **v2.3.0** - Performance optimizations (blur batch operations)
4. **v3.0.0** - Major feature expansion (TBD based on user feedback)
