# ComfyUI Apex Artist — Efficient Nodes to Make ComfyUI Convenient

A collection of efficient, easy-to-use nodes for ComfyUI that streamline image processing and prompt management.

## 🎨 Available Nodes

### Image Processing
- **ApexBlur** — 9 blur algorithms (Gaussian, Motion, Radial, Lens, Spin, Zoom, etc.)
- **ApexSharpen** — 8 sharpening methods (Unsharp Mask, High Pass, Clarity, etc.)
- **ApexLayerBlend** — 25+ blend modes for layer compositing
- **ApexDepthToNormal** — Convert depth maps to normal maps
- **ApexHDRIViewer** — Load HDRI/360° panoramas, aim a camera view, and output the captured image

### Models & Workflow
- **ApexLoraLoader** — Interactive browser with folder navigation and thumbnail preview support
- **ApexJSON** — Look up text values in JSON data
- **ApexPromptPreset** — Professional prompt presets across Environment, Lighting, Style, Color, and Camera Lens categories
- **ApexCharacterPrompt** — Character prompts from 12 preset categories (gender, age, ethnicity, face, eye color, skin tone, hair, headwear, top, bottom, shoes, hand accessory) with 13 text outputs
  - Presets include **Square Eyes**: a soft oval face with distinctive horizontally elongated rectangular-shaped eyes and pale blue-grey irises
  - Presets include **Long Silver Blonde Wispy Bangs** (hair), **White Wireless Headphones** (headwear), and **Oversized Pale Blue Hoodie** (top)

## ✨ Key Features

### Apex Character Prompt

- 12 category selectors (gender, age, ethnicity, face, eye color, skin tone, hair, headwear, top, bottom, shoes, hand accessory) and 13 STRING outputs.
- Optional free-text input leads the combined prompt without changing the individual category outputs.
- Resolution order is gender → age → ethnicity → face → eye color → skin tone → hair → headwear → top → bottom → shoes → hand accessory; combine with the downstream prompt node.
- Each category supports `Disabled`, `Random`, or an explicit preset. Random selection is seed-deterministic and weighted.
- `character_presets.json` may be edited to add or rename presets. When a category in that file is non-empty it becomes authoritative; otherwise the built-in library is used.
- A missing or malformed store never prevents the node from loading — it falls back to the built-in library and leaves the damaged file untouched for repair.

### Apex Prompt — Factory and User Presets

- **Save Preset…** saves editable text in one category: Environment, Lighting, Style, Color, or Camera Lens. Use **Copy selected category text** or **Copy input text** to fill the editor explicitly; saving does not capture the entire combined prompt or node setup.
- **Manage Presets…** provides search, category/source filters, Use, Save a Copy, and user-only Edit/Rename/Delete actions.
- Save and Manage dialogs keep **Close** in a sticky top-right header, accessible while scrolling.
- **Apex Color** is a dedicated colour-grade slot with 68 bundled presets, split between standard colour styles (Full Natural Color, Rich Vibrant Color, Soft Pastel Palette, Warm Golden Grade, Cool Blue Grade, Jewel Tone Palette, Neon Color Pop, Duotone Two Color, Cross Processed Color, Bleach Bypass Steel, Sepia Antique Tone…) and industry looks (Teal and Orange Blockbuster, Film Print Emulation 2383, ACES Neutral Grade, Rec.709 Broadcast Color, Log Flat Ungraded, Technicolor Three Strip, Two Strip Technicolor, Day for Night Blue, Cold Cyan Thriller, Kodak Portra / Ektar / Ektachrome / Gold / Kodachrome / Vision3 250D and 500T, CineStill 800T, Fujifilm Eterna / Velvia / Pro 400H, Agfa, Polaroid, Lomo, Eighties VHS Color, Nineties Music Video Color, Y2K Digicam Color, False Color Infrared, Thermal Heat Map…). Colour is a deliberate choice: **Monochrome Noir**, Sepia, and the desaturated/Low Saturation presets are only reached when you pick them. `Random` draws one weighted preset like every other category.
- Combined prompt order is input → environment → lighting → style → **color** → camera lens, so the colour grade is stated after the look. The node returns six STRING outputs: `combined_prompt`, `environment_text`, `lighting_text`, `style_text`, `camera_lens_text`, and the new `color_text`. The five original outputs keep their positions, and the new `color_preset` dropdown is appended last, so saved workflows keep their values and links.
- Factory presets remain read-only. The bundled JSON is preserved; Python defaults supply missing names without replacing existing JSON text. Existing factory names and node inputs stay unchanged.
- User presets appear as **User: Name** in the existing selectors. The same name can exist in both libraries without overriding a factory preset.
- User data is stored at `apex_artist/prompt_presets.json` beneath ComfyUI's configured user directory, outside this extension's installation directory. **This library is installation-shared, not private to a ComfyUI user profile.** All clients with access to this server can manage it.
- **Random** retains the original factory pool, order, and weights; saving a user preset does not alter seeded factory choices. User weights are stored for future user-random support; there is no user-random selector in this version.
- Saves refresh open nodes and invalidate backend output caches. Existing missing selections are not silently replaced; restore/import the preset or select another before running.
- Export backs up the **user** library only. Import accepts a version-1 export or a legacy category dictionary and adds entries as user presets. Conflicting user names are rejected without partial writes; rename the incoming entry or edit the existing one explicitly.
- Saving uses a revision check and same-directory atomic replacement. A stale editor stays open with its draft; refresh its revision and review before retrying. Corrupt user files are reported and left untouched.

**Upgrade:** restart ComfyUI, then hard-refresh the browser. No factory-file migration or rewrite occurs. If you previously customized the bundled JSON, copy those entries into the user library and export a backup before updating/reinstalling the extension. Workflow files reference preset names; share the user-library export alongside workflows that use them.

**Scope:** concurrent clients of one ComfyUI server are supported. Do not run multiple server processes writing the same preset file; the write lock is process-local. Private per-profile libraries and whole-node setup presets are not implemented.



### LoRA Loader
- Interactive modal browser with folder navigation
- Optimized 256x256 thumbnails (100-200x faster loading)
- Smart preview detection (multiple formats: PNG, JPG, WebP, GIF, BMP, TIFF)

- Original images can be deleted after thumbnail creation to save space
- Handles large collections (1000+ LoRAs efficiently)

## 📦 Installation

1. Navigate to ComfyUI custom_nodes directory
2. Clone the repository:
   ```bash
   git clone https://github.com/ApexArtist/comfyui-apex-artist.git
   ```
3. Restart ComfyUI
4. Nodes appear under "Apex Artist" in the Add Node menu

## 📚 Documentation

See `CHANGELOG.md` for release notes, `PUBLISH.md` for release preparation, and `memory-bank/systemPatterns.md` for architecture notes.

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
- **ApexHDRIViewer**: depends on output resolution and batch size

## 🚀 Changelog

**v2.3.0** - 2026-09-24 — First published release of the 2.x line: Apex Character Prompt (12 categories, 221 presets, 13 outputs), the new Apex Color colour-grade category (68 standard and industry presets) with a sixth Apex Prompt output, separate factory/user prompt libraries with atomic writes and Save/Manage dialogs, preset colour fixes that stop unwanted black-and-white renders, HDRI socket preview fixes, and LoRA path hardening. See `CHANGELOG.md` for validation and remaining release checks.

**v2.1.2** - 2026-07-25 — LoRA thumbnail system fixes: automatic regeneration on image updates, browser cache-busting, improved back button
**v2.1.1** - 2026-07-23 — Patch: version bump, removed stale ApexLoadModel references from metadata files
**v2.0.3** - 2026-07-19 — Project cleanup: removed ApexLoRAExtract, ApexLoRAMerge, and ApexModelQuantizer to focus on core VFX features
**v2.0.2** - 2026-07-16 — Brand refresh: repositioned as efficient nodes to make ComfyUI convenient, removed VFX branding
**v2.0.1** - 2026-07-16 — Security fixes, performance optimizations, code deduplication (apex_utils.py)

## 📦 Requirements

- ComfyUI (latest stable)
- Python 3.8+
- PyTorch (as provided by ComfyUI)
- Pillow (PIL) with image format support (provided by ComfyUI)
- OpenCV (`opencv-python`) for true `.hdr` / `.exr` HDRI loading

**Note on WebP support:** WebP thumbnail generation requires Pillow to be compiled with libwebp support. If WebP processing fails, the system will gracefully fall back to serving the original WebP image directly. Most modern Pillow installations include WebP support by default.

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Issues and feature requests welcome on GitHub!
