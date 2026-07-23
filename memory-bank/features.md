# Features: comfyui-apex-artist

## ApexLoraLoader

### Overview
Professional LoRA loader with interactive folder browser and optimized thumbnail system.

### Key Features
- **Interactive Modal Browser**: Full-screen modal with folder navigation
- **Folder Navigation**: Breadcrumb navigation, subfolder support, parent navigation
- **Thumbnail Grid**: Responsive CSS Grid layout (auto-fill, 100px min)
- **Optimized Thumbnails**: Two-tier system (256px for grid, 512px for preview)
- **Central Cache**: `.thumbnails` folder at loras root (~10-30 KB per thumbnail)
- **Smart Processing**: Handles all image formats, animated GIFs (first frame), transparency
- **Security**: Path validation prevents directory traversal
- **Single Strength**: Unified slider applies to both MODEL and CLIP

### Technical Implementation
- **Backend**: `apex_lora_loader.py` - Node class with preview detection
- **Frontend**: `web/apex_lora_loader.js` - Modal browser with responsive grid
- **API**: `apex_lora_api.py` - Three endpoints (list_folder, preview, image serving)
- **Thumbnail Generation**: Pillow/PIL with LANCZOS resampling, center-crop to 1:1 square
- **Caching**: Persistent JPEG thumbnails with 24-hour browser cache headers
- **Selected Preview Rendering**: Frontend loads the selected preview as a browser `Image`, assigns `node.imgs = [img]`, sets `node.imageIndex = 0`, redraws the canvas, and clears with `node.imgs = []` when unavailable. It intentionally preserves node size on image changes, matching native Load Image behavior.

### Bug Fixes (v1.7.0)
- **Node Freeze Fix**: Deferred browser collapse with 50ms setTimeout
- **Error Boundaries**: Try-catch blocks prevent crashes
- **Canvas Updates**: requestAnimationFrame prevents race conditions
- **Loading State**: Prevents preview display during loading phase

### Bug Fixes (2026-07-21)
- **Native Selected Preview Rendering**: The selected LoRA preview on the node now uses ComfyUI's native `node.imgs` preview renderer instead of a custom `addCustomWidget()` canvas draw. This matches native Preview Image / Load Image behavior and fixes messy stretched, shifted, or clipped previews.
- **Native Load Image-like Sizing**: LoRA preview changes no longer call `node.setSize(node.computeSize())`; the preview redraws inside the existing node bounds so manually resized nodes stay stable across different preview images.

### Preview Image Support
Priority order:
1. `<lora_name>.preview.png`
2. `<lora_name>.preview.jpg`
3. `<lora_name>.png`
4. `<lora_name>.jpg`

### Performance
- File size reduction: 100-500x smaller (2-5 MB → 10-30 KB for grid)
- Loading speed: 100-200x faster for 50 thumbnails
- Grid loading: Instant with cached thumbnails
- Supports 1000+ LoRA collections with pagination (100 items/page)

---

## ApexPromptPreset

### Overview
Preset-based prompt selector with 55 professionally-crafted prompts across 3 categories.

### Categories & Counts
- **Environment** (27 presets): Outdoor, indoor, and scene-setting prompts
- **Lighting** (29 presets): Professional lighting setups and moods
- **Style** (11 presets): Artistic styles and rendering approaches

### Features
- **Weighted Random Selection**: Uses deterministic seeding
- **Dynamic Dropdowns**: Populated from static method
- **Preset Caching**: Class-level cache for performance
- **Bracket Syntax**: Supports ComfyUI weight brackets `(text:weight)`

### Technical Implementation
- **Backend**: `apex_prompt.py` - 643 lines with preset data
- **Frontend**: `web/apex_prompt.js` - UI extensions
- **API**: `apex_prompt_api.py` - Preset management endpoints
- **Storage**: `prompt_presets.json` - User custom presets

### Camera Lens Browser

#### Overview
Interactive lens preset browser with visual thumbnails showing framing characteristics. Integrated directly into ApexPromptPreset node for professional camera lens effect selection.

#### Key Features
- **43 Lens Presets**: Professional camera lens configurations across 6 categories
- **Visual Thumbnails**: 256×256 generated diagrams showing framing characteristics
- **Color-Coded Categories**: Visual organization by lens type
- **Interactive Grid Browser**: Expandable/collapsible interface embedded in node
- **Smart Visibility**: Browser toggle hidden when "Disabled" or "Random" selected
- **Preview Display**: Large preview on selection with lens metadata

#### Lens Categories & Color Coding
1. **Standard Lenses** (Green) - 35mm, 50mm, Macro
2. **Wide Angle** (Cyan) - 24mm, 28mm, Ultra-wide
3. **Portrait Lenses** (Magenta) - 85mm, 135mm variations
4. **Telephoto** (Yellow) - 200mm, 300mm, 400mm
5. **Special Effects** (Orange) - Tilt-shift, Fisheye, Lensbaby
6. **Cinema** (Red) - Anamorphic, Cinema aspect ratios

#### Technical Implementation

**Thumbnail Generation**: `generate_lens_thumbnails.py`
- PIL/Pillow-based visual diagram generation
- 256×256 resolution for optimal grid display
- Framing indicators: rectangles, ovals, cinema markers, grid overlays
- Color-coded borders by category (5px width)
- Saved as JPG to `lens_previews/` directory
- Filename convention: `{lens_name_with_underscores}.jpg`

**Backend API**: `apex_prompt_lens_api.py`
- Three endpoints:
  - `/apex/lens_list` - Returns all 43 lens presets with metadata
  - `/apex/lens_preview?lens=<name>` - Returns preview path for specific lens
  - `/apex/lens_image/<filename>` - Serves thumbnail images
- Security: Path validation prevents directory traversal
- Filename conversion: Spaces → underscores for filesystem compatibility

**Frontend Browser**: `web/apex_prompt_lens.js` (500+ lines)
- DOM-based modal browser integrated into ApexPromptPreset node
- Responsive CSS Grid: 90px minmax with auto-fill
- Property hooking: Intercepts `camera_lens_preset` value changes
- **Smart Widget Visibility**: `updateToggleButtonVisibility(lensValue)` function
  - Hides toggle button when "Disabled" or "Random" selected
  - Shows toggle button for all other lens presets
- Features:
  - Expandable/collapsible browser interface
  - Large preview display on selection
  - Selection highlighting with visual feedback
  - Grid layout with thumbnail + label

#### Integration
- Embedded directly in `ApexPromptPreset` node
- No separate node required
- Works alongside existing preset system
- Browser state persists across selections
- Complements prompt generation workflow

#### Performance
- 43 thumbnails at ~10-15KB each (~500KB total)
- Instant grid loading with cached images
- Browser collapse: 50ms setTimeout prevents node freeze
- Thumbnail generation: One-time setup (~5 seconds for all 43 presets)

#### File Structure
```
comfyui-apex-artist/
├── generate_lens_thumbnails.py      # Thumbnail generator script
├── apex_prompt_lens_api.py          # Backend API endpoints
├── web/apex_prompt_lens.js          # Frontend browser UI
├── lens_previews/                   # Generated thumbnails
│   ├── 35mm_Standard.jpg
│   ├── 50mm_Standard.jpg
│   ├── 85mm_Portrait_Classic.jpg
│   └── ... (43 total)
└── __init__.py                      # Imports lens API
```

---

## ApexBlur

### Overview
9 professional blur algorithms with GPU acceleration.

### Blur Types
1. **Gaussian** - Standard smooth blur
2. **Gaussian Strong** - Higher sigma values
3. **Box** - Fast uniform blur
4. **Motion** - Directional motion blur with angle control
5. **Radial** - Radial zoom blur from center
6. **Surface** - Bilateral-style edge-preserving blur
7. **Lens** - Depth-of-field lens blur
8. **Spin** - Rotational blur around center
9. **Zoom** - Zoom burst effect

### Technical Details
- GPU-accelerated with PyTorch
- Separable convolutions where possible
- Iterative sampling for radial/spin/zoom effects
- Mask support for selective blurring
- Error handling with placeholder returns

### Performance
- Gaussian: ~15ms (1024×1024, RTX 3080)
- Motion: ~20ms
- Radial/Spin/Zoom: ~80ms (optimization opportunity: 2-3x faster with batch operations)

---

## ApexSharpen

### Overview
8 edge-aware sharpening algorithms for detail enhancement.

### Sharpen Types
1. **Unsharp Mask** - Classic photography sharpening
2. **High Pass** - Frequency separation sharpening
3. **Clarity** - Mid-tone contrast enhancement
4. **Detail Enhance** - Fine detail amplification
5. **Edge Enhance** - Edge detection and amplification
6. **Local Contrast** - Adaptive local sharpening
7. **Micro Contrast** - Very fine detail enhancement
8. **Adaptive** - Content-aware sharpening

### Technical Details
- GPU-accelerated edge detection
- Configurable strength and radius
- Mask support for selective sharpening
- Prevents over-sharpening with clamping
- Shared Gaussian blur implementation with ApexBlur

### Performance
- Unsharp Mask: ~18ms (1024×1024, RTX 3080)
- Adaptive: ~25ms

---

## ApexLayerBlend

### Overview
25+ Photoshop-style layer blending modes for image compositing.

### Blend Modes
**Standard**: Normal, Multiply, Screen, Overlay, Soft Light, Hard Light
**Color**: Color, Hue, Saturation, Luminosity
**Darken**: Darken, Color Burn, Linear Burn
**Lighten**: Lighten, Color Dodge, Linear Dodge (Add)
**Contrast**: Vivid Light, Linear Light, Pin Light, Hard Mix
**Difference**: Difference, Exclusion, Subtract, Divide
**Special**: Darker Color, Lighter Color

### Technical Details
- RGB and HSL color space conversions
- GPU-accelerated tensor operations
- Opacity control (0-100%)
- Proper alpha blending
- Batch processing support

### Performance
- Normal: ~2ms (500 fps)
- HSL modes: ~25ms (40 fps)

---

## ApexDepthToNormal

### Overview
Convert depth maps to normal maps with adaptive edge processing.

### Features
- Sobel operator for gradient detection
- Adaptive Z-axis scaling based on gradient magnitude
- Normalization for proper surface orientation
- Configurable strength parameter
- Batch processing support

### Technical Details
- GPU-accelerated convolutions
- Gradient-aware processing
- Output: RGB normal map (-1 to 1 range mapped to 0-255)

### Performance
- ~12ms (1024×1024, RTX 3080)
- 83 fps throughput

---

## Model Caching (Stable Normal)

### Overview
Local model storage system for StableNormal depth-to-normal models (if implemented).

### Cache Structure
```
comfyui-apex-artist/
├── models/
│   ├── torch_hub/
│   │   └── hub/Stable-X_StableNormal_main/  (~50MB)
│   └── huggingface/
│       └── hub/models--Stable-X--stable-normal-v0-1/  (~1-2GB)
```

### Benefits
- Self-contained within node directory
- Portable with easy backup/restore
- No system-wide cache pollution
- Clear disk usage tracking

### Model Sizes
- StableNormal Regular: ~2.3GB
- StableNormal Turbo: ~1.7GB
- Repository Code: ~50MB

---

## Historical Notes

### Category Optimization (July 2026)
All node categories standardized to consistent hierarchy:
- `Apex Artist/Image` - Basic operations
- `Apex Artist/Image/Filters` - Blur, sharpen
- `Apex Artist/Image/Composite` - Layer blend, depth processing
- `Apex Artist/Models` - LoRA loader
- `Apex Artist/Text` - Prompt, JSON processing

### Code Quality Improvements
- Cleaned orphaned `__pycache__` files
- Removed unused dependencies (transformers, accelerate)
- Fixed display name: "Apex Random Prompt" → "Apex Prompt Preset"
- Improved error handling across all nodes
- Added comprehensive inline documentation

### Performance Benchmarks (Completed)
Comprehensive testing on RTX 3080 with 1024×1024 images established baseline performance metrics for all nodes.
