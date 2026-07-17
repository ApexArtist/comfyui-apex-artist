# Active Context: comfyui-apex-artist

## Current Focus
**Documentation & Publishing Workflow** (2026-07-18) - Created PUBLISH.md with comprehensive version management and git workflow instructions. Enhanced update_version.py with auto-increment flags, dry-run mode, and git integration features.

Previous: v2.0.2 - Removed ApexSmartResize node (redundant functionality). Updated README.md to be more concise. Now 8 active nodes.

## Active Nodes (8 registered)
| Node | Category | Description |
|------|----------|-------------|
| ApexBlur | Image/Filters | 9 blur algorithms |
| ApexSharpen | Image/Filters | 8 edge-aware sharpening algorithms |
| ApexDepthToNormal | Image/Composite | Depth → normal map conversion |
| ApexLayerBlend | Image/Composite | 25+ Photoshop-style layer blending modes |
| ApexPromptPreset | Text | 55 presets across 3 categories |
| ApexLoraLoader | Models | LoRA loader with interactive browser |
| ApexLoRAStack | Models | Apex LoRA Merge with DARE-TIES and Wan 2.2 tower detection |
| ApexModelQuantizer | Models | Quantize models to FP8/INT8/NVFP4/MXFP8 |

## Key Features Summary

All detailed feature documentation is now in **`features.md`**. Quick reference:

- **ApexLoraLoader**: Interactive browser with optimized thumbnails (100-500x smaller files)
- **ApexLoRAStack**: LoRA merge with DARE-TIES, TIES, DARE, Add, SVD algorithms
- **ApexModelQuantizer**: FP8/INT8/NVFP4/MXFP8 quantization with learned rounding
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
- **PUBLISH.md**: Publishing workflow and version management guide

## Version Management & Publishing
- Current: 2.0.2
- Version tracked in: `pyproject.toml`, `custom_nodes.json`, `comfyui.yaml`, `manifest.json`, `__init__.py`
- **Publishing guide**: `PUBLISH.md` - Complete workflow documentation
- **Update script**: `update_version.py` - Enhanced version management tool

### update_version.py Features (370 lines)
- **Auto-increment flags**: `--patch`, `--minor`, `--major` for semantic versioning
- **Dry-run mode**: `--dry-run` to preview changes without applying
- **Git integration**: `--commit` and `--tag` flags for automated git workflow
- **Colored output**: Visual feedback with emoji indicators
- **Current version detection**: Automatically reads current version from files
- **Verification**: Confirms all files were updated consistently
- **Script improvements**:
  - Fixed shebang to use `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe`
  - Fixed manifest.json regex to avoid matching "manifest_version" field
  - Uses negative lookbehind pattern: `(?<!"manifest_)"version"`

### PUBLISH.md Contents
- **Pre-Publish Checklist**: Code quality, testing, documentation, version files
- **Version Update Process**: Semantic versioning guidelines, script usage examples
- **Git Workflow**: Staging, commit conventions, tagging, pushing procedures
- **Post-Push Verification**: GitHub, ComfyUI Registry, user testing steps
- **Troubleshooting**: Common issues and solutions (version mismatches, push rejections, tag conflicts)
- **Quick Reference**: Complete command sequences and one-command publishing
- **Release Notes Template**: Standard changelog format
