# Product Context

## Why This Exists
ComfyUI users need convenient image processing and prompt management without external tools or long node chains. This package provides professional-grade image effects, flexible prompt systems, and efficient LoRA workflows directly in the ComfyUI interface.

## How It Should Work
Users add nodes from the "Apex Artist" category, configure parameters through native ComfyUI widgets, and connect them in workflows. LoRA selection happens through an interactive browser with thumbnails. Prompt presets offer categorized options (Environment, Lighting, Style, Color, Camera Lens) with seeded randomization. Image processing nodes handle batched tensors with device-aware operations.

## User Experience Goals
- Discoverable through ComfyUI's native add-node menu
- Familiar widget interfaces that preserve user-controlled node sizes
- Fast LoRA browsing with folder navigation and lightweight thumbnails
- Repeatable prompt generation with editable preset libraries
- Photographic presets use photographic language; artistic styles retain their vocabulary
- Preview images using ComfyUI's native node.imgs system

## Known Limitations
- No diffusion model loader, quantizer, or RGB curve editor (removed features)
- Panoramas can't reveal unseen geometry or true parallax
- HDRI interactive preview requires connecting IMAGE and running once; first frame is a downscaled 8-bit approximation, final outputs retain tensor dynamic range
- Prompt user library is shared across the installation; private per-profile libraries and whole-node setup saves are not implemented
