# ComfyUI Apex Artist — Efficient Nodes to Make ComfyUI Convenient

A collection of efficient, easy-to-use nodes for ComfyUI that streamline image processing and prompt management.

## 🎨 Available Nodes

### Image Processing
- **ApexBlur** — 9 blur algorithms (Gaussian, Motion, Radial, Lens, Spin, Zoom, etc.)
- **ApexSharpen** — 8 sharpening methods (Unsharp Mask, High Pass, Clarity, etc.)
- **ApexLayerBlend** — 25+ blend modes for layer compositing
- **ApexDepthToNormal** — Convert depth maps to normal maps

### Models & Workflow
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

**v2.1.1** - 2026-07-23 — Patch: version bump, removed stale ApexLoadModel references from metadata files
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
