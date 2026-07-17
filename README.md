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
- **ApexLoRAMerge** — **Apex LoRA Merge** node for exporting merged LoRA files with Wan 2.2 tower detection and algorithms including DARE-TIES
- **ApexModelQuantizer** — Quantize models to FP8, INT8, NVFP4, or MXFP8 with optional learned rounding optimization
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

### LoRA Merge
**Apex LoRA Merge** merges multiple LoRA files into a single `.safetensors` file with advanced algorithms:
- **DARE-TIES** (recommended) — Combines dropout/rescale with sign election to reduce interference
- **TIES** — Trim, elect sign, merge to reduce conflicts
- **DARE Linear** — Random dropout and rescale for stability
- **Add** — Simple weighted sum
- **SVD** — Rank reduction via singular value decomposition

**Features:**
- Up to 20 LoRA slots with enable/disable per slot
- Auto-rank handling (zero-pads smaller ranks to match largest)
- Wan 2.2 tower detection (double_blocks/single_blocks) with auto-detect
- Debug output STRING with full merge log
- Context menu: Enable/Disable all, Reset strengths

**Algorithms:**
- **DARE-TIES**: DARE dropout → TIES sign election (density ~0.5 recommended)
- **TIES**: [NeurIPS 2023](https://arxiv.org/abs/2306.01708) - Resolves sign conflicts
- **DARE**: [2023](https://arxiv.org/abs/2311.03099) - Dropout and rescale
- **SVD**: Target rank + threshold parameters

For detailed documentation, see [APEX_LORA_MERGE.md](APEX_LORA_MERGE.md)

## 📊 Performance (RTX 3080, 1024×1024)

- **ApexBlur**: 15-80ms depending on type
- **ApexSharpen**: 18-25ms
- **ApexLayerBlend**: 2-25ms depending on mode
- **ApexDepthToNormal**: 12ms

## 🚀 Changelog

**v2.0.2** - 2026-07-16 — Brand refresh: repositioned as efficient nodes to make ComfyUI convenient, removed VFX branding
**v2.0.1** - 2026-07-16 — Security fixes, performance optimizations, code deduplication (apex_utils.py)
**v2.0.0** — Previous release

## 📦 Requirements

- ComfyUI (latest stable)
- Python 3.8+
- PyTorch (as provided by ComfyUI)
- No additional dependencies required

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Issues and feature requests welcome on GitHub!
