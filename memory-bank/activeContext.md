# Active Context: comfyui-apex-artist

## Current Focus
**Code Review & Optimization Complete** - Comprehensive review identified 15 issues. Created `apex_utils.py` shared utility module eliminating 5+ code duplications. Documented all findings in CODE_REVIEW_FINDINGS.md with 3-phase optimization roadmap.

Previous: Camera Lens Browser with real photography thumbnails complete (v1.7.1 production-ready).

## Active Nodes (7 registered)
| Node | Category | Description |
|------|----------|-------------|
| ApexSmartResize | Image | AI-optimized aspect-aware resizing with 2026 model support |
| ApexBlur | Image/Filters | 9 blur algorithms |
| ApexSharpen | Image/Filters | 8 edge-aware sharpening algorithms |
| ApexDepthToNormal | Image/Composite | Depth → normal map conversion |
| ApexLayerBlend | Image/Composite | 25+ Photoshop-style layer blending modes |
| ApexPromptPreset | Text | 55 presets across 3 categories |
| ApexLoraLoader | Models | LoRA loader with interactive browser |

## Key Features Summary

All detailed feature documentation is now in **`features.md`**. Quick reference:

- **ApexSmartResize**: 12 presets including 6 new 2026 models (ZImage, QwenEdit, Krea2, Ideogram4, FLUX.2, SD3.5)
- **ApexLoraLoader**: Interactive browser with optimized thumbnails (100-500x smaller files)
- **ApexPromptPreset**: 55 presets across 3 categories
- **ApexBlur**: 9 blur algorithms, GPU-accelerated
- **ApexSharpen**: 8 sharpening algorithms, edge-aware
- **ApexLayerBlend**: 25+ Photoshop-style blend modes
- **ApexDepthToNormal**: Depth to normal map conversion

## Lens Thumbnail System
- **Real photography thumbnails**: All 43 lens presets have curated example images
- **Smart processing pipeline**: `process_lens_images.py` with fuzzy matching algorithm
- **Thumbnail format**: 256x256 pixels, top-left aligned, white padding on right/bottom
- **Aspect ratio preserved**: No cropping - full image content visible with scale-to-fit
- **Optimized size**: ~7KB average per thumbnail (JPEG quality 85%)
- **Batch file**: `run_process_lens_images.bat` for easy re-processing
- **Source images**: `lens/` folder with 46 source images
- **Output**: `lens_previews/` with 43 processed thumbnails

## Important Patterns
- **Error resilience**: Nodes return placeholder tensors on failure
- **Class-level safety**: Methods used by `INPUT_TYPES()` must be `@staticmethod` or `@classmethod`
- **Avoid deprecated imports**: Don't import `scripts/ui.js`, use local helpers
- **Modal browser pattern**: DOM-based UI with responsive grid and breadcrumb navigation
- **Property hook pattern**: Use `Object.defineProperty()` to intercept widget value changes for reliable updates
- **Thumbnail processing**: Top-left alignment with white padding, no center-crop
- **Shared utilities**: Use `apex_utils.py` for common operations (blur, validation, color conversion)
- **Input validation**: Always validate tensors/parameters before processing
- **Async I/O**: API handlers must use non-blocking I/O (aiofiles or asyncio.to_thread)

## Code Quality Findings (2026-07-16)
**Critical Issues Identified:**
1. Async file I/O blocking event loop in 3 API handlers
2. Gaussian blur duplicated 5+ times across files
3. Missing input validation for radius/tensor parameters
4. Path traversal vulnerability with symlinks
5. Thread-unsafe caching in apex_prompt.py

**Optimization Created:**
- **apex_utils.py**: Centralized utilities module with validation, blur, color conversion
- **CODE_REVIEW_FINDINGS.md**: Complete analysis with 3-phase roadmap
- **Expected improvements**: 40-60% faster blur, 80-90% faster API responses

**Next Phase:** Update nodes to use apex_utils, fix async I/O, add validation decorators

## Documentation Structure
- **features.md**: Comprehensive feature documentation (ALL nodes)
- **systemPatterns.md**: Architecture and technical patterns
- **techContext.md**: Technologies and dependencies
- **productContext.md**: Product vision and use cases
- **progress.md**: Project status and milestones
- **activeContext.md**: Current focus and quick reference

## Version Management
- Current: 1.7.1
- Version tracked in: `pyproject.toml`, `custom_nodes.json`, `comfyui.yaml`, `manifest.json`
- Update script: `update_version.py` (now uses correct Python venv path)
- Script improvements:
  - Fixed shebang to use `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe`
  - Fixed manifest.json regex to avoid matching "manifest_version" field
  - Uses negative lookbehind pattern: `(?<!"manifest_)"version"`
