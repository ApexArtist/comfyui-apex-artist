# Product Context: comfyui-apex-artist

## Purpose
Provides professional-grade VFX and post-production nodes that integrate naturally into ComfyUI workflows, plus advanced diffusion model loading with dtype selection.

## Problems It Solves
- **Limited artistic controls**: ComfyUI's built-in nodes don't cover professional VFX effects (multiple blur algorithms, depth-to-normal conversion, RGB curves, layer blending)
- **Workflow complexity**: Users previously needed to chain multiple basic nodes or use external tools
- **Batch processing**: Nodes support batch modes for video frame sequences
- **Interactive UI**: JavaScript extensions provide interactive widgets (RGB curve editors, LoRA browser with thumbnails)

## User Experience
- **Discoverability**: Nodes grouped under "Apex Artist" category with subcategories
- **Consistency**: Follow ComfyUI's established UI/UX patterns
- **Composability**: Nodes chain together naturally
- **Performance**: GPU-accelerated via PyTorch; FP8 optimizations reduce VRAM usage

## Node Inventory (6 registered)
1. ApexPromptPreset — 55 presets across Environment/Lighting/Style/Camera Lens categories
2. ApexLoraLoader — Interactive browser with folder navigation and thumbnails
3. ApexBlur — 9 blur algorithms
4. ApexSharpen — 8 edge-aware sharpening algorithms
5. ApexDepthToNormal — Depth → normal map conversion
6. ApexLayerBlend — 25+ Photoshop-style blending modes

## Key Design Principles
- **Native-first rule**: Always use ComfyUI's native mechanisms and conventions when available (e.g., node.imgs for previews, folder_paths.get_full_path_or_raise for path resolution)
- **Error resilience**: Nodes return placeholder tensors on failure
- **Class-level safety**: Methods used by INPUT_TYPES() must be @staticmethod or @classmethod
