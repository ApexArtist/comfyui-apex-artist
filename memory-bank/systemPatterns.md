# System Patterns

## System Architecture
- **Node modules**: apex_*.py files define node classes with INPUT_TYPES/FUNCTION/RETURN_TYPES contracts
- **API modules**: apex_*_api.py files register HTTP routes via PromptServer
- **Registration**: __init__.py exports NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS, WEB_DIRECTORY
- **Frontend**: ComfyUI auto-loads web/*.js; scripts/ contains tests/utilities; preset JSON files are editable data stores
- **Assets**: lens/ contains source images; lens_previews/ serves generated assets (preserve both)

## Key Technical Decisions
- **Native ComfyUI integration**: Use folder_paths for path management, native upload/preview APIs, standard tensor shapes
- **Security model**: Validate paths using resolved component checks against storage roots, not string prefixes; recheck after user selection
- **Preview pattern**: Use node.imgs=[img], node.imageIndex=0, setDirtyCanvas() for LoRA thumbnails; don't resize node per image change
- **Shared utilities**: apex_utils.py provides Gaussian blur (separable convolution), device/dtype-aware masks, luminance/HSL conversion
- **Error handling**: Varies per node (raise/pass-through/placeholder); no universal contract established
- **RNG management**: Seed local generators, never modify global random state

## Design Patterns in Use
### Image Processing Nodes
- **Tensor shape**: IMAGE=[batch, H, W, channels], MASK=[batch, H, W]
- **Device/dtype**: Match mask to image device/dtype before operations
- **Gaussian blur**: Separable 1D convolutions preserve existing sigma/padding behavior; float64 kernels for accuracy

### LoRA System
- Modal browser with folder navigation
- Generate 256×256 JPEG thumbnails on demand
- Display using native node.imgs preview (no custom canvas)
- Path validation: resolve all components, check against loras root

### Preset System
- Four categories: Environment, Lighting, Style, Camera
- Seeded random selection returns (name, text) tuples
- Bracket expansion for variations
- Prompt factory JSON is read-only; Python defaults supplement missing names. User entries use `User: ` tokens, preventing factory shadowing.
- Shared `apex_prompt_store.py` backs prompt API, INPUT_TYPES and execution. User store under configured ComfyUI user root, `apex_artist/prompt_presets.json`; installation-shared, not per-profile.
- Prompt writes serialize the full read/check/write transaction with RLock and atomically replace a same-directory temp file after fsync. Revision conflicts reject stale clients. Multi-process writers are not supported.
- Prompt execution reloads snapshots; IS_CHANGED returns content/order revision. Websocket events refresh tracked frontend nodes without replacing selections or resizing them.
- Legacy Random uses original JSON order/pool; user additions and fallback-only factory names do not enter it. Character preset API has not adopted these changes. Character node is a standalone class borrowing only stateless text helpers; it must not inherit prompt-store methods. Character execution reloads its own JSON and IS_CHANGED hashes that file. `ApexCharacterPrompt` mirrors Apex Prompt's `input_text` convention (empty multiline STRING, comma-joined ahead of the preset categories, `[option a, option b]` bracket support), but its widget is appended last in INPUT_TYPES because ComfyUI maps `widgets_values` positionally and reordering would corrupt saved workflows.

### HDRI Viewer
- **Backend**: PyTorch grid_sample reprojection, camera forward=-Z/up=+Y, R=Ry@Rx@Rz
- **Coordinates**: lon=atan2(x,-z), lat=asin(y) for equirectangular
- **Socket contract**: `ui.hdri_source` contains a bounded first-frame source PNG descriptor; `hdri_source_scale` restores its normalized HDR range before exposure. `ui.images` is exclusively projected outputs. Never decode node.imgs as the panorama.
- **Lifetime/cache**: UUID temporary previews; per-node load tokens/timers with removal guards; native ComfyUI dependency caching rather than sampled tensor IS_CHANGED.
- **Preview source**: Must preview original panorama, not projected output
- **Interaction**: Drag yaw/pitch, Shift-drag roll, wheel FOV (when working)

### DOM Widget Patterns
- Start optional widgets collapsed
- Defer visibility setup 2 RAFs until wrappers exist (ComfyUI wrapping behavior)
- Hide with display:none + pointer-events:none on both widget.element AND wrapper parent
- Restore only owned styles when showing
- Clean up listeners, timers, pending async on removal
- Guard image loads against stale results/cross-node interference
- Preserve existing hooks with original arguments/receiver

## Component Relationships
- Nodes consume apex_utils for shared image operations
- APIs serve preset/thumbnail data to frontend modules
- Frontend modules enhance nodes with interactive UI
- Tests validate nodes without full ComfyUI runtime (synthetic package)

## Critical Implementation Details
- **Blocking I/O**: HDRI decode/render and LoRA scans currently block async handlers
- **Frontend state**: HDRI refresh timers/load tokens are isolated per node
- **Cache invalidation**: Sampled IS_CHANGED hashing misses changes outside samples
- **Python output authoritative**: JS preview must match backend lens/orientation math
- **Manual testing required**: Syntax tests ≠ ComfyUI/browser integration tests
