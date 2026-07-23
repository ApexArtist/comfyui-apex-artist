# Active Context: comfyui-apex-artist

## Current Focus (2026-07-23)
**Latest Fix**:
✅ **Apex LoRA Loader Browser Selection Fix**: Added `VALIDATE_INPUTS` classmethod to dynamically validate LoRA file paths at execution time. This fixes the "value not in list" error when selecting LoRAs from subfolders via the browser. The fix follows ComfyUI's native pattern - the widget still shows the full dropdown list at creation, but browser selections are validated against actual file existence using `folder_paths.get_full_path()` instead of a static list.

**Completed Tasks (2026-07-21)**:
1. ✅ **Node Display Name**: Changed "Apex Prompt Preset" → "Apex Prompt" in `apex_prompt.py` and `__init__.py`
2. ✅ **Fashion Preset Cleanup**: Removed all "collage"/"multi-panel"/"dual screen" references from Fashion presets in `prompt_presets.json`
3. ⚠️ **Random Lens UI Update**: Partial implementation - groundwork laid but requires deeper ComfyUI execution event integration
4. ✅ **Comprehensive Cinematic Environment Presets**: Added 53 new environment presets covering all major film genres (85 total presets now)
5. ✅ **Apex LoRA Loader Native Preview Fix**: Replaced the custom canvas preview widget in `web/apex_lora_loader.js` with ComfyUI's native `node.imgs` image preview path. Selected LoRA previews now render like the native Preview Image/Load Image node and no longer appear stretched, shifted, clipped, or auto-resized on image changes.

**Latest Addition - Cinematic Environment Expansion**:
Expanded Apex Environment presets from 32 to 85 total presets, adding comprehensive coverage for:
- Action/Thriller (7): warehouse, parking garage, subway tunnel, airport, bridge, hospital ER, courtroom
- Period/Historical (5): Victorian mansion, 1920s speakeasy, Western saloon, WWII bunker, medieval tavern
- Horror/Suspense (5): abandoned asylum, foggy cemetery, dark basement, haunted manor, isolated lighthouse
- Sci-Fi (4): cryogenic lab, alien planet, starship bridge, Mars colony
- Noir/Mystery (4): detective office, rain-soaked alley, jazz club, hotel corridor
- Romance (4): candlelit restaurant, observation deck, garden gazebo, beach bonfire
- War/Military (4): fighter jet hangar, WWI trench, command center, desert outpost
- Additional Cinematic (20): train platform, penthouse balcony, mountain cabin porch, rooftop garden, and more

All new presets use natural language prompts optimized for modern AI models (Flux, SDXL, Krea).

## Recent Changes (2026-07-20)
- **apex_prompt.py**: Modified `get_random_preset()` and `_get_preset_text()` to return `(preset_name, prompt_text)` tuples
- **apex_prompt_lens_api.py**: Added `/apex/get_selected_lens` and `/apex/set_selected_lens` API endpoints for future UI sync
- **prompt_presets.json**: Renamed "Fashion Collage Portrait" → "Fashion Studio Portrait" in Environment and Style categories
- **Node registration**: Updated NODE_DISPLAY_NAME_MAPPINGS to use "Apex Prompt"

## Active Nodes (7 registered)
| Node | Display Name | Category | Description |
|------|--------------|----------|-------------|
| ApexPromptPreset | **Apex Prompt** | Text | 55 presets across 4 categories (Environment/Lighting/Style/Camera Lens) |
| ApexLoraLoader | Apex LoRA Loader | Models | LoRA loader with interactive browser |
| ApexLoadModel | Apex Load Model | Models | Advanced model loader with dtype selection |
| ApexBlur | Apex Blur | Image/Filters | 9 blur algorithms |
| ApexSharpen | Apex Sharpen | Image/Filters | 8 edge-aware sharpening algorithms |
| ApexLayerBlend | Apex Layer Blend | Image/Composite | 25+ Photoshop-style blend modes |
| ApexDepthToNormal | Apex Depth to Normal | Image/Composite | Depth → normal map conversion |

## Apex Prompt Node Details
**Categories**: Environment (85), Lighting (50), Style (37), Camera Lens (43)
**Features**:
- Weighted random selection (deterministic by seed)
- Dynamic bracket syntax: `[option1, option2, option3]` for random text selection
- Returns: combined_prompt, environment_text, lighting_text, style_text, camera_lens_text
- Interactive camera lens browser with 43 curated preview images

**Known Limitation**: Random camera lens selection works correctly but UI doesn't auto-update to show selected lens (requires ComfyUI execution event hooks)

## Important Patterns
- **Error resilience**: Nodes return placeholder tensors on failure
- **Class-level safety**: Methods used by `INPUT_TYPES()` must be `@staticmethod` or `@classmethod`
- **Native-first rule**: Always use ComfyUI's native mechanisms and conventions when available. Do not invent custom UI/rendering/layout behavior when a native ComfyUI/LiteGraph path exists.
- **Property hook pattern**: Use `Object.defineProperty()` to intercept widget value changes
- **Native node image preview pattern**: For frontend node preview images, load a browser `Image`, then assign `node.imgs = [img]` and `node.imageIndex = 0`; clear with `node.imgs = []`. Redraw with `node.setDirtyCanvas(true, true)` or `node.graph?.setDirtyCanvas(true, true)`. Do **not** call `node.setSize(node.computeSize())` on every image change; preserve the user's node size like native Load Image behavior. Do not manually draw image previews with a custom canvas widget unless native rendering is impossible.
- **Shared utilities**: Use `apex_utils.py` for common operations (blur, validation, color conversion)
- **Async I/O**: API handlers use aiofiles for non-blocking file operations
- **Tuple returns from presets**: All `_get_preset_text()` calls now return `(name, text)` tuples

## Code Quality Status (2026-07-19)
✅ **Completed Optimizations**: HSL/luminance deduplication, grouped convolution, LRU kernel cache, thread-safe caching, fixed global random.seed() pollution

**Remaining**: Async file I/O optimization, batch operation improvements for radial/spin/zoom blur

## Documentation Structure
- **features.md**: Comprehensive feature documentation
- **systemPatterns.md**: Architecture and technical patterns  
- **techContext.md**: Technologies and dependencies
- **progress.md**: Project status and milestones
- **PUBLISH.md**: Publishing workflow guide

## Version Management
- **Current**: 2.0.2
- **Script**: `update_version.py` with `--patch`, `--minor`, `--major`, `--commit`, `--tag` flags
- **Files synced**: `pyproject.toml`, `custom_nodes.json`, `comfyui.yaml`, `manifest.json`, `__init__.py`
