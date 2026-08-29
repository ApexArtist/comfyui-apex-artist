# Active Context: comfyui-apex-artist

## Current Focus (2026-08-29) - ApexHDRIViewer Server-Side Preview ✅

### Root Cause
Client-side preview via browser `new Image()` + canvas reprojection was fundamentally broken
for the node's main file types: **browsers cannot decode `.hdr`/`.exr`**, so `onload` never fired
(`onerror` was unhandled) and the preview never rendered → "preview gone, no drag visual".

### Fix (this session)
Preview is now rendered **server-side** and served as a browser-displayable PNG, so it works for
every format the node supports (.hdr/.exr/PNG/JPEG):
- **NEW `apex_hdri_preview_api.py`** — registers GET `/apex/hdri_preview?filename=..&yaw=&pitch=&roll=&fov=&lens=`.
  Reuses `ApexHDRIViewer._load_hdri_tensor` + `equirect_to_camera_view` to render a 512x288 camera
  view and returns PNG bytes via `web.Response(body=..., content_type="image/png")`.
  Registered in `__init__.py` (import pattern same as `apex_lora_api`).
- **Rewrote `web/apex_hdri_viewer.js` (251 lines, `node --check` clean)** — removed all broken
  client-side decoding/reprojection; the widget now `drawImage`s the fetched preview PNG, stretches
  to the widget, and overlays a HUD. Drag = yaw/pitch, Shift+drag = roll, wheel = FOV; changes
  debounce-refresh the preview (120ms) and `commitWidgetChange` fires widget callbacks to re-run
  the IMAGE output. Preview uses a **fixed comfortable height (~520px, min 360/max 720)** instead of mirroring the wide output aspect, and the node is resized once at creation so the panel is actually visible — not a thin strip.
- Verified end-to-end: backend rendering to PNG works for both lens types; Node harness confirms
  module load, preview fetch, widget sizing, and drag (yaw 10→20).

### Reminder for user on cache
ComfyUI caches web extensions: a hard refresh (Ctrl+Shift+R) or a full server restart is required
to load new `web/` JS and the new `/apex/hdri_preview` route.

## Previous Focus (2026-08-29) - ApexHDRIViewer Frontend Fix ✅

### Problem Fixed
The `web/apex_hdri_viewer.js` module had **multiple JS syntax errors** that prevented the
`ApexArtist.HDRIViewer` extension from ever loading. Because `WEB_DIRECTORY = "./web"` is set,
ComfyUI imports every `.js` in that folder as an ES module, so one syntax error killed the whole
extension — the node rendered with **no interactive 3D drag-to-rotate preview**.

Root causes found:
- `return /view?filename= ...` — leading `/` parsed as an unterminated regex literal → syntax error.
- `Yaw:  + ... + ° Pitch: ...` — unquoted `Yaw:` identifier and raw `°` byte → syntax error.
- The drag handler only wrote widget values but never drew a live rendered camera view.

### Fix (this session)
Cleanly rewrote `web/apex_hdri_viewer.js` (313 lines, `node --check` exit 0):
- Correct URL builder: `/view?filename=...&type=...&subfolder=` (proper string concat).
- `drawCameraView()` — live rectilinear/fisheye equirect→perspective reprojection on the widget
  canvas, mirroring backend math (`R = Ry@Rx@Rz`, `lon=atan2(wx,-wz)`, `lat=asin(wy)`, forward = -Z).
- `decodePanorama()` — decodes the selected panorama **once** into an `ImageData` frame buffer
  (fast, no per-pixel canvas allocation); `sampleFrame()` does bilinear sampling with modular
  horizontal seam wrap to match backend `grid_sample`.
- Drag handler: drag = yaw/pitch, **Shift+drag = roll**, wheel = FOV; HUD overlay shows values.
- Commits widget values to the backend `render()` on pointer-up / wheel so the full-res IMAGE
  output stays in sync; fisheye lens now read as raw string (fixes `Number("fisheye")` → NaN bug).

## Current Focus (2026-08-29) - ApexHDRIViewer JS Full Rewrite âœ…

### Problem Fixed
The previous session's refactor left `web/apex_hdri_viewer.js` broken:
- `drawCameraPreview` was disconnected / missing (the function call existed but the implementation was gone)
- The draggable panorama preview window was not working
- The file was partially truncated by a bad PowerShell write

### Full Rewrite Summary
`web/apex_hdri_viewer.js` was cleanly rewritten from scratch (328 lines, syntax-verified clean):

- **[UPDATE 2026-08-29]:** Switched from native LiteGraph canvas widgets (which didn't honor `computeSize()` height on restore) to a DOM-based `canvas` widget via `node.addDOMWidget()`. The DOM widget has CSS `height: 220px` applied directly to it, effectively pinning its size.
- `drawCameraPreview()` â€” equirectangular â†’ perspective reprojection with per-frame render cache (skips recompute when params unchanged). Supports rectilinear and fisheye lens types.
- `getSampleCanvas()` â€” downscales source HDRI to â‰¤512px working copy for speed
- `drawAimWidget()` â€” three non-overlapping zones: semi-transparent header bar (help text), clipped preview band (panorama + guide grid + FOV ring), semi-transparent footer bar (live yaw/pitch/roll/fov values)
- `computeSize()` â€” derives widget height from `output_width`/`output_height` ratio via closure over `node`, capped 80â€“600px
- `mouse()` handler â€” drag for yaw/pitch, Shift+drag for roll, scroll wheel for FOV; all pointer event types covered including `pointerleave` to cancel drag on cursor exit
- Cache invalidation on image widget change (clears `previewUrl`, `sampleCanvas`, `renderCanvas`)

### ApexHDRIViewer UI Polish (also completed this session) âœ…
1. **Default output ratio changed to 16:9** (`apex_hdri_viewer.py`) â€” `output_width`: 1024â†’1280, `output_height`: 1024â†’720
2. **`.hdri` file format support** (`apex_hdri_viewer.py`) â€” added to `SUPPORTED_EXTENSIONS`, routed through OpenCV HDR path
3. **Widget aspect ratio** (`web/apex_hdri_viewer.js`) â€” preview panel height mirrors output dimensions ratio



### ApexHDRIViewer Implementation âœ…
Added a new Load Image-style node for selecting HDRI/equirectangular panorama files, aiming a camera view, and outputting the captured image:
- `apex_hdri_viewer.py` loads selected input images and implements rectilinear/equidistant fisheye reprojection with PyTorch `grid_sample`
- `web/apex_hdri_viewer.js` adds an in-node panorama camera viewer that updates yaw/pitch/roll/FOV values
- `__init__.py`, `custom_nodes.json`, `manifest.json`, `README.md`, and feature docs updated
- `opencv-python` added for true `.hdr`/`.exr` loading; reprojection still uses PyTorch rather than `cv2.remap`

## Previous Focus (2026-08-18) - Project Cleanup

### ApexMotionBlur & MediaAccumulatorStitch Removed âœ…
Removed video-related nodes to refocus project on core VFX and image processing:
- `apex_motion_blur.py` and `apex_media_stitch.py` deleted
- `__init__.py` updated â€” imports and mappings removed
- `custom_nodes.json` and `manifest.json` updated â€” node entries and video/motion-blur tags removed
- Project now has 6 core nodes focused on essential functionality

## Previous Focus (2026-07-25) - v2.1.2 Patch Release

### ApexLoadModel Removed âœ…
The `ApexLoadModel` node has been **removed entirely** from the project:
- `apex_load_model.py` deleted â€” the node was redundant with ComfyUI's native `CheckpointLoaderSimple` and other model loaders
- `__init__.py` updated â€” import and mappings removed
- `web/apex_load_model.js` already deleted in previous cleanup
- `apex_load_model_fixes.md` moved to `memory-bank/` for historical reference

### Completed Tasks (2026-07-23)
1. âœ… **ApexLoadModel removed**: Deleted node file, cleaned up registration, moved fix docs to memory-bank
2. âœ… **Apex Prompt Lens JS cleanup**: Deleted `web/apex_prompt_lens.js` â€” it was a complete no-op (empty `beforeRegisterNodeDef` hook, no functional code)
3. âœ… **Stale references cleaned**: Removed deleted `apex_prompt_lens.js` mentions from memory-bank files
4. âœ… **`.gitignore` updated**: Added `.clineignore` entry

## Recent Changes (2026-07-23)
- **apex_load_model.py**: DELETED â€” node removed (redundant with native ComfyUI loaders)
- **__init__.py**: Removed ApexLoadModel import and mappings
- **web/apex_load_model.js**: Already deleted in previous cleanup
- **web/apex_prompt_lens.js**: DELETED â€” was a no-op extension
- **apex_load_model_fixes.md**: MOVED to `memory-bank/apex_load_model_fixes.md`

## Active Nodes (7 registered)
| Node | Display Name | Category | Description |
|------|--------------|----------|-------------|
| | ApexPromptPreset | **Apex Prompt** | Text | 55 presets across Environment/Lighting/Style/Camera Lens categories |
| | ApexLoraLoader | Apex LoRA Loader | Models | LoRA loader with interactive browser and native `node.imgs` preview |
| | ApexBlur | Apex Blur | Image/Filters | 9 blur algorithms |
| | ApexSharpen | Apex Sharpen | Image/Filters | 8 edge-aware sharpening algorithms |
| | ApexLayerBlend | Apex Layer Blend | Image/Composite | 25+ Photoshop-style blend modes |
| | ApexDepthToNormal | Apex Depth to Normal | Image/Composite | Depth â†’ normal map conversion |
| | ApexHDRIViewer | Apex HDRI Viewer | Image | Load HDRI/panorama, aim camera, output captured view |

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
- **Current**: 2.1.3
- **Script**: `update_version.py` with `--patch`, `--minor`, `--major`, `--commit`, `--tag` flags


## HDRI Viewer - preview polish
- Preview draw uses cover fit (fill + center-crop) - no portrait stretching.
- Node widened to min 420px at widget creation.
- Drag debounce 120ms -> 60ms with stale-response token guard => near-realtime.
- Frontend-only; hard refresh browser to apply.

- Restored realtime client-side 3D preview: panorama decoded once to ImageData (PANO_MAX_W cap), precomputed per-pixel ray lon/lat maps keyed by size/fov/roll, per-frame bilinear reprojection into an offscreen canvas drawn cover-fit. Center ring+dot overlay restored. Drag/Shift-drag/wheel update widgets -> rAF local redraw (realtime); server snapshot (apex/hdri_preview) still syncs on release and serves .hdr/.exr. Fixed lon mapping to backend convention (u = lon/2pi + 0.5).
