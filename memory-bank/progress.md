# Progress

## What Works
- **9 registered nodes** (v2.2.0 prepared locally): ApexBlur (9 algorithms), ApexSharpen (8 methods), ApexLayerBlend (27 modes), ApexDepthToNormal, ApexHDRIViewer, ApexLoraLoader, ApexPromptPreset, ApexCharacterPrompt, ApexJSON
- **Core image processing**: All blur/sharpen/blend operations functional
- **Shared utilities**: Separable Gaussian blur (tested vs dense reference), device/dtype-aware masks, luminance/HSL conversion
- **LoRA system**: Modal browser with folder navigation, 256×256 JPEG thumbnails, native node.imgs preview, path boundary validation
- **Prompt preset system**: Read-only factory JSON with missing Python names supplemented; separate installation-shared user store; Save/Manage UI, atomic writes, revision conflicts, import/export, live dropdown refresh and execution invalidation. Existing factory random pool preserved.
- **Character prompt node**: 12 preset categories with weighted seed-deterministic Random, an independent character store, 13 STRING outputs, and an optional free-text input box that leads the combined prompt (appended last in INPUT_TYPES so existing workflows keep their widget values)
- **Security**: Resolved component path checks prevent directory traversal
- **Testing**: September 20: 10 prompt-preset Python tests, frontend Node.js harness, full character validator (library, dropdowns, 13 outputs, seeding, brackets, API CRUD, damaged/missing-store fallback, package registration) and 7 core unittest methods all pass; real package import verified against actual `folder_paths` (9 nodes registered). Character library is 221 presets (18 face) with **Square Eyes** stored verbatim and confirmed in `character_presets.json`; September 21 additions are **Long Silver Blonde Wispy Bangs** (hair), **White Wireless Headphones** (headwear), and **Oversized Pale Blue Hoodie** (top), regenerated and verified in sync with the validator total updated to 221. Live browser smoke tests for the new controls remain pending. September 21, 2026: the validator grew to 105 checks covering the character node's new `input_text` box (position, spec, merge order, output isolation, empty-box regression, brackets) and passes 105 / 0 FAIL; the box appears in the UI only after a ComfyUI restart.

## What's Left to Build
### Critical Issues
1. **HDRI viewer**: Repaired September 21; 11 frontend checks and 6 backend tests pass. Separate source panorama metadata, correct back yaw, unique temporary files, per-node async state, matching lens/exposure/aspect. Live browser verification pending.
4. **Preset follow-up**: Live browser smoke test pending; character API remains separate and unchanged
5. **Registry metadata**: Reconciled nine node IDs/display names/categories, manifest outputs, and OpenCV dependency for 2.2.0; publication deferred

### Known Issues
- **Known gap**: The character node ships dropdowns and a working API but no in-canvas preset manager UI, so preset changes require editing `character_presets.json` directly. `web/apex_preset_manager.js` is a reusable manager that nothing currently imports.
- **Known gap**: `/apex/character_presets` still writes non-atomically and can overwrite the extension's JSON in place, unlike the prompt preset store.
- HDRI/LoRA thumbnail rendering blocks async handlers
- Character prompt registration and inherited-store regression fixed September 20; standalone/API/package-registration validator passes. Live UI restart verification pending.
- Sampled IS_CHANGED hashing can miss changes outside samples
- Legacy uncommitted HDRI height-control harness targets absent controls; use the new test_hdri_socket.py/.mjs regressions for the current socket contract
- requirements.txt vs metadata dependency reconciliation needed

## Current Status
2.2.0 prepared for local commit, not publication. Current automated regressions pass; live browser and clean-install checks remain pending. Legacy HDRI height diagnostics are preserved but excluded from the current regression suite. See CHANGELOG.md.

## Evolution of Project Decisions
- **July 2026**: Standardized categories, created shared utilities, built LoRA modal/thumbnail system; removed extraction/merge/quantizer/smart-resize nodes
- **August 2026**: Removed motion/media nodes; introduced HDRI reprojection + server PNG preview for HDR formats
- **September 2026**: Refined photographic preset wording (Atmospheric Moonlight, Golden Rays, etc.); socket-based HDRI work in progress; consolidated documentation from 22 files to 6 core Memory Bank files
