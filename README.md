# ComfyUI Apex Artist

Professional VFX and post-production nodes for ComfyUI with advanced image processing, LoRA management, and AI model optimization.

## 🎨 Nodes Overview

### Image Processing
- **ApexSmartResize** — AI-model-optimized resizing with 12 presets (SDXL, Flux, 2026 models: ZImage, QwenEdit, Krea2, Ideogram4, FLUX.2, SD3.5)
- **ApexBlur** — 9 professional blur algorithms (Gaussian, Motion, Radial, Lens, Spin, Zoom, etc.)
- **ApexSharpen** — 8 edge-aware sharpening methods (Unsharp Mask, High Pass, Clarity, etc.)
- **ApexLayerBlend** — 25+ Photoshop-style blend modes (Multiply, Screen, Overlay, Color, etc.)
- **ApexDepthToNormal** — Convert depth maps to normal maps with adaptive processing

### LoRA & Workflow
- **ApexLoraLoader** — Interactive browser with folder navigation and optimized thumbnails (100-500x smaller file sizes!)
- **ApexPromptPreset** — 55 professional presets across Environment, Lighting, and Style categories

## ✨ Key Features

### ApexLoraLoader
- **Interactive Modal Browser**: Navigate folders, view thumbnails in responsive grid
- **Optimized Thumbnails**: Automatic 256px/512px caching reduces load times 100-200x
- **Smart Detection**: Automatically finds preview images with multiple naming patterns
- **Pagination**: Handles 1000+ LoRA collections smoothly

### ApexSmartResize
- **2026 Model Support**: Presets for Z-Image Turbo, Qwen Edit, Krea2, Ideogram4, FLUX.2, SD3.5
- **Divisibility Control**: Ensure dimensions compatible with VAE/ControlNet/Upscalers (8/16/32/64)
- **5 Snap Methods**: keep_proportion, closest_area, closest_ratio, prefer_larger, prefer_smaller
- **Console Analytics**: Detailed JSON output with memory estimates and processing stats

### Professional VFX
- **GPU Accelerated**: All image operations use PyTorch GPU tensors
- **Batch Processing**: Process multiple images efficiently
- **Error Resilient**: Graceful fallbacks with placeholder returns
- **Mask Support**: Selective processing with mask inputs

## 📦 Installation

1. Navigate to ComfyUI custom_nodes directory
2. Clone this repository:
   ```bash
   git clone https://github.com/ApexArtist/comfyui-apex-artist.git
   ```
3. Restart ComfyUI
4. Nodes appear under "Apex Artist" in the Add Node menu

## 📚 Documentation

For detailed feature documentation, architecture patterns, and technical implementation:
- See `memory-bank/features.md` for comprehensive node documentation
- See `memory-bank/` for project architecture and patterns

## 🚀 Quick Start

### Smart Resize for 2026 Models
```
Add Node → Apex Artist → Image → Apex Smart Resize
- Preset: ZImage (or QwenEdit, Krea2, etc.)
- Snap Method: keep_proportion
- Enforce Divisibility: 64
```

### LoRA with Visual Browser
```
Add Node → Apex Artist → Models → Apex LoRA Loader
- Click "Click to browse LoRAs" button
- Navigate folders with breadcrumb
- Click thumbnail to select
```

### Professional Blur Effects
```
Add Node → Apex Artist → Image → Filters → Apex Blur
- Blur Type: Motion, Radial, Lens, etc.
- Radius: 5-50 (adjust to taste)
- Optional: Connect mask for selective blur
```

## 📊 Performance

Optimized for real-time creative work (RTX 3080, 1024×1024):
- **ApexBlur**: 15-80ms depending on type
- **ApexSharpen**: 18-25ms
- **ApexLayerBlend**: 2-25ms depending on mode
- **ApexSmartResize**: 8ms
- **ApexDepthToNormal**: 12ms

## 🔧 Requirements

- ComfyUI (latest stable)
- Python 3.8+
- PyTorch (as provided by ComfyUI)
- No additional dependencies required

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Issues and feature requests welcome on GitHub!
