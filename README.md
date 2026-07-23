# ComfyUI Apex Artist — Efficient Nodes to Make ComfyUI Convenient

A collection of efficient, easy-to-use nodes for ComfyUI that streamline image processing and prompt management.

## 🎨 Available Nodes

### Image Processing
- **ApexBlur** — 9 blur algorithms (Gaussian, Motion, Radial, Lens, Spin, Zoom, etc.)
- **ApexSharpen** — 8 sharpening methods (Unsharp Mask, High Pass, Clarity, etc.)
- **ApexLayerBlend** — 25+ blend modes for layer compositing
- **ApexDepthToNormal** — Convert depth maps to normal maps

### Models & Workflow
- **ApexLoadModel** — Advanced checkpoint loader with weight dtype selection (fp16, bf16, fp8, fp32)
- **ApexLoraLoader** — Interactive browser with folder navigation and thumbnail preview support
- **ApexPromptPreset** — Professional prompt presets across Environment, Lighting, and Style categories

## ✨ Key Features

### LoRA Loader
- Interactive modal browser with folder navigation
- Optimized thumbnails reduce load times 100-200x
- Smart preview detection (multiple naming patterns)
- Handles large collections (1000+ LoRAs)

## 📦 Installation

1. Navigate to ComfyUI custom_nodes directory
2. Clone the repository:
   ```bash
   git clone https://github.com/ApexArtist/comfyui-apex-artist.git
   ```
3. Restart ComfyUI
4. Nodes appear under "Apex Artist" in the Add Node menu

## 📚 Documentation

For detailed documentation, see `memory-bank/features.md`.

## 🚀 Quick Start

### Load Model
**Apex Load Model** is an advanced checkpoint loader with comprehensive weight dtype control and custom file browser:
- **default** — ComfyUI's default behavior
- **fp8_e4m3fn** — FP8 E4M3 format (8-bit, VRAM efficient)
- **fp8_e4m3fn_fast** — FP8 with optimization flags (faster)
- **fp8_e5m2** — FP8 E5M2 alternate format
- **int8** — 8-bit integer quantization (experimental)
- **fp16** — Half precision (16-bit, balanced)
- **bf16** — Brain float 16 (better for training)
- **fp32** — Full precision (32-bit, highest quality)

**Features:**
- **Custom file browser** — Browse and load models from anywhere on your system
- **Dual selection modes** — Use custom browser OR native dropdown (custom takes priority)
- Separate weight storage and compute dtype control
- Load weights in fp8 but compute in fp16 for quality
- Based on kijai's DiffusionModelLoaderKJ implementation
- Full MODEL/CLIP/VAE output compatibility

**Supported formats:** `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`

**Usage:**
```
Add Node → Apex Artist → Models → Apex Load Model

Option 1 - Custom Browser (Priority):
- Click "🗂️ Browse Model..." button
- Select any model file from your computer
- Shows selected file name
- Click "❌ Clear" to remove selection

Option 2 - Native Dropdown (Fallback):
- Use "Checkpoint Name" dropdown (models in ComfyUI/models/checkpoints)
- Falls back to this if no custom file selected

Additional Options:
- Choose weight_dtype (default: default)
- Optional: Set compute_dtype for computation precision
- Outputs: MODEL, CLIP, VAE
```

**Priority logic:** Custom path (top browser) takes priority over native dropdown. Both can be populated, but custom path will be used if present.

**Why use this over native loader?**
- Native loader: Only "default" and "fp8" options, limited to checkpoints folder
- Apex Load Model: 7 weight formats + separate compute dtype + load from anywhere
- More control for VRAM-constrained systems or quality optimization
- Access models outside standard checkpoints directory

### LoRA Loader
```
Add Node → Apex Artist → Models → Apex LoRA Loader
- Click "Click to browse LoRAs" button
- Navigate folders with breadcrumb
- Click thumbnail to select
```

## 📊 Performance (RTX 3080, 1024×1024)

- **ApexBlur**: 15-80ms depending on type
- **ApexSharpen**: 18-25ms
- **ApexLayerBlend**: 2-25ms depending on mode
- **ApexDepthToNormal**: 12ms

## 🚀 Changelog

**v2.0.3** - 2026-07-19 — Project cleanup: removed ApexLoRAExtract, ApexLoRAMerge, and ApexModelQuantizer to focus on core VFX features
**v2.0.2** - 2026-07-16 — Brand refresh: repositioned as efficient nodes to make ComfyUI convenient, removed VFX branding
**v2.0.1** - 2026-07-16 — Security fixes, performance optimizations, code deduplication (apex_utils.py)

## 📦 Requirements

- ComfyUI (latest stable)
- Python 3.8+
- PyTorch (as provided by ComfyUI)
- No additional dependencies required

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Issues and feature requests welcome on GitHub!
