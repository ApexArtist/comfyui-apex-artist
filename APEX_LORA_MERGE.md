# Apex LoRA Merge

Advanced LoRA file merging node with support for multiple merge algorithms and automatic rank handling.

## Overview

Merges multiple LoRA files into a single new `.safetensors` file on disk. Supports 5 advanced merge algorithms and automatically handles LoRAs with different ranks through zero-padding.

**Category**: Apex Artist/Models  
**Node Type**: Output Node  
**ComfyUI Class**: `ApexLoRAStack`

## Features

- **5 Merge Algorithms**: Add, TIES, DARE Linear, DARE-TIES (recommended), SVD
- **Auto-rank handling**: Zero-pads smaller LoRAs to match the largest rank (e.g., rank 32 → rank 128)
- **Up to 20 LoRA slots**: Dynamically show/hide slots based on `lora_count`
- **Transformer block tagging**: Metadata tags for double_blocks/single_blocks (useful for Wan 2.2, but works with all LoRA types)
- **Debug output**: Second STRING output with full merge log
- **No model loading**: Operates directly on raw LoRA tensor files

## Inputs

### Required

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `save_path` | STRING | `""` | Subfolder path within your LoRAs directory to save the merged file. Leave empty to save in loras root. Example: `"merges/test"` |
| `lora_count` | INT | `3` | Number of LoRA slots to display (1–20) |

### Optional

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `merge_algorithm` | COMBO | `"DARE-TIES"` | Merge algorithm: Add / TIES / DARE Linear / DARE-TIES / SVD |
| `merge_density` | FLOAT | `0.5` | Density/keep-rate for TIES/DARE algorithms (0.0–1.0). Higher = keep more parameters. Not used by Add or SVD. |
| `merge_rank` | INT | `64` | Target rank for SVD algorithm only (1–512) |
| `merge_threshold` | FLOAT | `0.01` | Singular value threshold for SVD only (0.0–1.0) |

### Dynamic LoRA Slots (per slot 0–19)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lora_X_enabled` | BOOLEAN | `False` | Enable this LoRA slot |
| `lora_X_name` | COMBO | `""` | LoRA file to use |
| `lora_X_strength` | FLOAT | `1.0` | Merge weight/strength (-2.0–2.0) |
| `lora_X_tower` | COMBO | `"Auto-detect"` | Transformer block tag (metadata only): Auto-detect / double_blocks / single_blocks / double_blocks + single_blocks / Unknown |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `merge_path` | STRING | Full path to the saved merged `.safetensors` file |
| `debug_output` | STRING | Full merge log (algorithm used, LoRAs merged, padding applied, etc.) |

## Merge Algorithms

### Add / Weighted Sum
Simple scaled addition. Fast but can cause interference between LoRAs.

```
result = Σ(LoRA_i × strength_i)
```

### TIES - Trim, Elect Sign, Merge
Trims low-magnitude values, elects a consensus sign across LoRAs, then merges. Reduces sign conflicts.

**Reference**: Yadav et al., "TIES-Merging: Resolving Interference When Merging Models" (NeurIPS 2023)  
**Paper**: [https://arxiv.org/abs/2306.01708](https://arxiv.org/abs/2306.01708)

### DARE Linear - Drop And REscale
Randomly drops parameters and rescales to maintain expected magnitude. Reduces redundancy.

**Reference**: Yu et al., "Language Models are Super Mario: Absorbing Abilities from Homologous Models" (2023)  
**Paper**: [https://arxiv.org/abs/2311.03099](https://arxiv.org/abs/2311.03099)

### DARE-TIES (Recommended)
Applies DARE dropout first, then TIES sign election. Best balance of quality and conflict reduction. This is a community hybrid combining both papers' methods.

### SVD - Rank Reduction
Decomposes tensors via Singular Value Decomposition and reconstructs at a lower rank. Useful for compression.

## Rank Mismatch Handling

When merging LoRAs with different ranks (e.g., 10 LoRAs with rank 128 and 2 with rank 32), the node automatically **zero-pads** smaller tensors to match the largest shape. This is mathematically safe because the extra dimensions contribute zero weight (no effect), preserving all LoRA information.

Example log output:
```
[Apex LoRA Stack] Padded tensor 3 for key 'double_blocks.0.img_attn.qkv.lora_up.weight': 
  torch.Size([32, 5120]) -> torch.Size([128, 5120])
```

## Usage Example

1. **Set `lora_count`** to the number of LoRAs you want to merge (e.g., 5)
2. **Enable and select LoRAs** in the visible slots
3. **Set strengths** (typically 1.0, adjust as needed)
4. **Choose algorithm** (DARE-TIES recommended)
5. **Set `save_path`** (e.g., `"merged_loras"`)
6. **Run** — the merged file is saved and the path is output

## Compatibility

- ✅ Works with all LoRA types (Wan 2.2, SD 1.5, SDXL, Flux, Krea 2, etc.)
- ✅ Handles LoRAs with different ranks automatically
- ✅ Backwards compatible with existing workflows
- ✅ No model or clip connection required

## Context Menu Options

Right-click the node for quick actions:
- **Enable All LoRAs** — Turn on all visible slots
- **Disable All LoRAs** — Turn off all visible slots
- **Reset All Strengths to 1.0** — Reset all strength values

## License

MIT License - Copyright (c) 2024 ApexArtist

See [license.md](license.md) for full license text.

## Technical Notes

- All merge math performed in FP32 for precision, then cast back to original dtype
- Uses `torch.stack()` for efficient tensor operations
- Outputs `.safetensors` format (or `.pt` if safetensors library not available)
- Timestamp appended to filenames to prevent overwrites

## Version History

- **v1.1.0** (2026-07-18): Added zero-padding for rank mismatch handling, debug output, renamed tower labels to technical names
- **v1.0.0**: Initial release with 5 merge algorithms and Wan 2.2 tower detection