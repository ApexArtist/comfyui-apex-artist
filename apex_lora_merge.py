#!/usr/bin/env python3
"""
Apex LoRA Merge Node - Advanced LoRA file merging for Wan 2.2 dual-tower architecture

Creates merged LoRA files using advanced tensor merging algorithms:
Add, TIES, DARE Linear, DARE-TIES, and SVD.

Wan 2.2 aware: Detects and handles high-noise/low-noise tower separation
"""

import os
import torch
import numpy as np
import folder_paths
import comfy.utils
import comfy.sd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

class ApexLoRAMerge:
    """
    Advanced LoRA merge node with Wan 2.2 tower detection.

    Reads raw LoRA .safetensors files directly from disk, merges their tensors
    with the chosen algorithm, and writes a new merged LoRA file. No model or
    clip connection is required.

    Features:
    - Dynamic LoRA list with enable/disable toggles
    - Auto-detect Wan 2.2 tower architecture (high/low/both/unknown)
    - Merge mode only: Tensor-level merging with advanced algorithms
    - All merge math in fp32 for precision
    """

    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        lora_list = folder_paths.get_filename_list("loras")

        inputs = {
            "required": {
                "save_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Subfolder in loras (e.g., mergelora/mylora)",
                    "tooltip": (
                        "Subfolder path inside your LoRA root directory where the merged file will be saved. "
                        "Leave empty to save directly into the loras root. "
                        "Example: 'merges/test' saves to <loras root>/merges/test/merged_<algorithm>_<names>_<timestamp>.safetensors"
                    ),
                }),
                "lora_count": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 20,
                    "step": 1,
                    "tooltip": (
                        "Number of LoRA slots to display. "
                        "Increase to merge more LoRAs at once (up to 20). "
                        "Only slots with 'Enabled' checked will be included in the merge."
                    ),
                }),
            },
            "optional": {
                "merge_algorithm": ([
                    "Add / Weighted Sum",
                    "TIES - Trim, Elect Sign, Merge",
                    "DARE Linear - Drop And REscale",
                    "DARE-TIES - DARE + TIES (Recommended)",
                    "SVD - Rank Reduction"
                ], {
                    "default": "DARE-TIES - DARE + TIES (Recommended)",
                    "tooltip": (
                        "Algorithm used to combine LoRA tensors:\n"
                        "• Add / Weighted Sum — simple scaled addition; fast but can cause interference between LoRAs.\n"
                        "• TIES — trims low-magnitude values, elects a consensus sign, then merges; reduces sign conflicts.\n"
                        "• DARE Linear — randomly drops parameters and rescales to maintain expected magnitude; reduces redundancy.\n"
                        "• DARE-TIES (Recommended) — applies DARE dropout first, then TIES sign election; best balance of quality and conflict reduction.\n"
                        "• SVD — decomposes tensors via singular value decomposition and reconstructs at a lower rank; useful for rank reduction."
                    ),
                }),
                "merge_density": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": (
                        "Density / keep-rate for TIES, DARE Linear, and DARE-TIES algorithms. "
                        "Controls how much of each tensor is retained before merging:\n"
                        "• 1.0 = keep all parameters (no pruning)\n"
                        "• 0.5 = keep the top 50%% by magnitude (default, good balance)\n"
                        "• 0.1 = keep only the top 10%% (aggressive pruning, reduces interference)\n"
                        "Not used by Add or SVD."
                    ),
                }),
                "merge_rank": ("INT", {
                    "default": 64,
                    "min": 1,
                    "max": 512,
                    "step": 1,
                    "tooltip": (
                        "Target rank for the SVD (Singular Value Decomposition) algorithm only. "
                        "Lower rank = more compression and smoothing, higher rank = more detail preserved. "
                        "Typical LoRA ranks are 4–128. Set to match the original LoRA rank or lower for aggressive compression. "
                        "Not used by Add, TIES, DARE Linear, or DARE-TIES."
                    ),
                }),
                "merge_threshold": ("FLOAT", {
                    "default": 0.01,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.001,
                    "tooltip": (
                        "Singular value threshold for the SVD algorithm only. "
                        "Singular values below (threshold × largest singular value) are discarded. "
                        "• 0.0 = keep all singular values up to merge_rank\n"
                        "• 0.01 = discard values smaller than 1%% of the largest (default)\n"
                        "• 0.1 = more aggressive truncation\n"
                        "Not used by Add, TIES, DARE Linear, or DARE-TIES."
                    ),
                }),
            }
        }

        # Dynamic LoRA slot inputs (max 20 slots)
        for i in range(20):
            slot_num = i + 1
            inputs["optional"][f"lora_{i}_enabled"] = ("BOOLEAN", {
                "default": False,
                "tooltip": f"Enable LoRA slot {slot_num}. Only enabled slots are included in the merge.",
            })
            inputs["optional"][f"lora_{i}_name"] = (lora_list, {
                "default": "",
                "tooltip": f"LoRA file to use in slot {slot_num}. Select from your installed LoRAs.",
            })
            inputs["optional"][f"lora_{i}_strength"] = ("FLOAT", {
                "default": 1.0,
                "min": -2.0,
                "max": 2.0,
                "step": 0.01,
                "tooltip": (
                    f"Merge strength / weight for LoRA slot {slot_num}. "
                    "1.0 = full contribution, 0.5 = half weight, negative values invert the LoRA effect. "
                    "For Add algorithm this directly scales the tensor; "
                    "for TIES/DARE it scales before sign election and dropout."
                ),
            })
            inputs["optional"][f"lora_{i}_tower"] = ([
                "Auto-detect",
                "double_blocks",
                "single_blocks",
                "double_blocks + single_blocks",
                "Unknown"
            ], {
                "default": "Auto-detect",
                "tooltip": (
                    f"Transformer block tag for LoRA slot {slot_num}. "
                    "Used for metadata only — does not affect merge math:\n"
                    "• Auto-detect — inspects tensor key names to determine block type automatically (recommended).\n"
                    "• double_blocks — LoRA targets double_blocks / img_mlp layers.\n"
                    "• single_blocks — LoRA targets single_blocks layers.\n"
                    "• double_blocks + single_blocks — LoRA spans both block types.\n"
                    "• Unknown — no specific block type detected.\n"
                    "Works with all LoRA types (Wan, SD, Flux, Krea, etc.)."
                ),
            })

        return inputs

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("merge_path", "debug_output")
    FUNCTION = "process"
    CATEGORY = "Apex Artist/Models"
    DESCRIPTION = (
        "Merges multiple LoRA files into a single new .safetensors file on disk. "
        "Supports Add, TIES, DARE Linear, DARE-TIES (recommended), and SVD algorithms. "
        "Wan 2.2 tower-aware: auto-detects high-noise / low-noise tower keys. "
        "No model or clip connection needed — operates entirely on raw LoRA tensor files. "
        "Outputs the full path to the saved merged file and a debug log."
    )

    def __init__(self):
        self.lora_cache = {}
        self._debug_log: List[str] = []

    def _log(self, message: str):
        """Print to console and capture in debug log."""
        print(message)
        self._debug_log.append(message)

    def _get_debug_output(self) -> str:
        """Return the accumulated debug log as a single string."""
        return "\n".join(self._debug_log)

    def process(self, save_path, lora_count, merge_algorithm="dare_ties",
                merge_density=0.5, merge_rank=64, merge_threshold=0.01, **kwargs):
        """
        Main processing function — merges selected LoRAs into a new file.

        Args:
            save_path: Subfolder path within loras directory to save merged file
            lora_count: Number of LoRA slots (for dynamic UI)
            merge_algorithm: Algorithm for merge mode
            merge_density: Density parameter for TIES/DARE
            merge_rank: Rank for SVD
            merge_threshold: Threshold for SVD
            **kwargs: Dynamic LoRA parameters from UI

        Returns:
            Tuple of (merge_path_string, debug_output_string)
        """
        # Reset debug log for this run
        self._debug_log = []

        lora_configs = self._extract_lora_configs(kwargs, lora_count)
        enabled_loras = [cfg for cfg in lora_configs if cfg['enabled']]

        if not enabled_loras:
            self._log("[Apex LoRA Merge] No LoRAs enabled, nothing to merge")
            return ("", self._get_debug_output())

        merge_algorithm = self._normalize_merge_algorithm(merge_algorithm)
        result = self._merge_mode(enabled_loras, merge_algorithm,
                                  merge_density, merge_rank, merge_threshold, save_path)
        # result is (path,) or (path,), append debug output
        if isinstance(result, tuple) and len(result) >= 1:
            return (result[0], self._get_debug_output())
        return (str(result), self._get_debug_output())

    def _normalize_merge_algorithm(self, algorithm: str) -> str:
        """
        Normalize readable UI labels and legacy workflow values to internal algorithm keys.

        Internal keys: add, ties, dare_linear, dare_ties, svd
        """
        algorithm_map = {
            "Add / Weighted Sum": "add",
            "TIES - Trim, Elect Sign, Merge": "ties",
            "DARE Linear - Drop And REscale": "dare_linear",
            "DARE-TIES - DARE + TIES (Recommended)": "dare_ties",
            "SVD - Rank Reduction": "svd",
            "add": "add",
            "ties": "ties",
            "dare_linear": "dare_linear",
            "dare_ties": "dare_ties",
            "svd": "svd",
        }
        return algorithm_map.get(str(algorithm), "dare_ties")

    def _extract_lora_configs(self, kwargs: Dict, lora_count: int) -> List[Dict]:
        """Extract LoRA configurations from dynamic widget kwargs."""
        configs = []

        for i in range(lora_count):
            enabled = kwargs.get(f"lora_{i}_enabled", False)
            lora_name = kwargs.get(f"lora_{i}_name", "")
            strength = kwargs.get(f"lora_{i}_strength", 1.0)
            tower = self._normalize_tower(kwargs.get(f"lora_{i}_tower", "Auto-detect"))

            if lora_name:
                configs.append({
                    'enabled': enabled,
                    'name': lora_name,
                    'strength': strength,
                    'tower': tower,
                    'index': i
                })

        return configs

    def _normalize_tower(self, tower: str) -> str:
        """
        Normalize user-facing tower labels and legacy workflow values to internal codes.

        Internal codes: unknown, high, low, both
        """
        tower_map = {
            "Auto-detect": "unknown",
            "double_blocks": "high",
            "single_blocks": "low",
            "double_blocks + single_blocks": "both",
            "Unknown": "unknown",
            "unknown": "unknown",
            "high": "high",
            "low": "low",
            "both": "both",
        }
        return tower_map.get(str(tower), "unknown")

    def _merge_mode(self, lora_configs: List[Dict], algorithm: str,
                    density: float, rank: int, threshold: float, save_path: str = "") -> Tuple:
        """
        Combine LoRA tensors into a single file.

        Args:
            lora_configs: List of enabled LoRA configurations
            algorithm: Merge algorithm (add, ties, dare_linear, dare_ties, svd)
            density: Density parameter for TIES/DARE
            rank: Rank parameter for SVD
            threshold: Threshold parameter for SVD
            save_path: Subfolder path within loras directory to save merged file

        Returns:
            Tuple of (merged_file_path,)
        """
        self._log(f"[Apex LoRA Merge] Combining {len(lora_configs)} LoRAs with {algorithm} algorithm")

        try:
            lora_tensors = []
            for cfg in lora_configs:
                lora_path = folder_paths.get_full_path("loras", cfg['name'])
                if not lora_path:
                    self._log(f"[Apex LoRA Merge] Warning: LoRA not found: {cfg['name']}")
                    continue

                lora_data = comfy.utils.load_torch_file(lora_path, safe_load=True)

                tower = cfg['tower']
                if tower == "unknown":
                    tower = self._detect_tower(lora_data)
                    self._log(f"[Apex LoRA Merge] Auto-detected tower for '{cfg['name']}': {tower}")

                lora_tensors.append({
                    'data': lora_data,
                    'strength': cfg['strength'],
                    'name': cfg['name'],
                    'tower': tower
                })

            if not lora_tensors:
                self._log("[Apex LoRA Merge] No valid LoRAs to merge")
                return ("",)

            merged_state_dict = self._merge_tensors(lora_tensors, algorithm, density, rank, threshold)
            output_path = self._save_merged_lora(merged_state_dict, lora_configs, algorithm, save_path)

            self._log(f"[Apex LoRA Merge] Merge complete: {output_path}")
            return (output_path,)

        except Exception as e:
            self._log(f"[Apex LoRA Merge] Error in merge: {e}")
            import traceback
            traceback.print_exc()
            return (f"Error: {str(e)}",)

    def _detect_tower(self, lora_data: Dict[str, torch.Tensor]) -> str:
        """
        Auto-detect Wan 2.2 tower architecture from LoRA keys.

        Wan 2.2 architecture:
        - High-noise tower: double_blocks.*.img_mlp.* keys
        - Low-noise tower: single_blocks.* keys
        - Both: has both types of keys
        - Unknown: neither pattern detected (SD/SDXL/Flux)
        """
        keys = list(lora_data.keys())

        has_high = any("double_blocks" in k or "img_mlp" in k for k in keys)
        has_low = any("single_blocks" in k for k in keys)
        has_wan_patterns = any(
            "joint_blocks" in k or
            "transformer_blocks" in k and "txt" in k or
            "transformer_blocks" in k and "img" in k
            for k in keys
        )

        if has_high and has_low:
            return "both"
        elif has_high or has_wan_patterns:
            return "high"
        elif has_low:
            return "low"
        else:
            return "unknown"

    def _merge_tensors(self, lora_tensors: List[Dict], algorithm: str,
                       density: float, rank: int, threshold: float) -> Dict[str, torch.Tensor]:
        """
        Merge multiple LoRA tensors using specified algorithm.
        All math performed in fp32 for precision, then cast back to original dtype.
        """
        if algorithm == "add":
            return self._merge_add(lora_tensors)
        elif algorithm == "ties":
            return self._merge_ties(lora_tensors, density)
        elif algorithm == "dare_linear":
            return self._merge_dare_linear(lora_tensors, density)
        elif algorithm == "dare_ties":
            return self._merge_dare_ties(lora_tensors, density)
        elif algorithm == "svd":
            return self._merge_svd(lora_tensors, rank, threshold)
        else:
            self._log(f"[Apex LoRA Merge] Unknown algorithm '{algorithm}', using 'add'")
            return self._merge_add(lora_tensors)

    def _pad_tensors_to_common_shape(self, tensors: List[torch.Tensor],
                                      key: str) -> List[torch.Tensor]:
        """
        Pad all tensors to the maximum shape across all dimensions.
        This handles merging LoRAs with different ranks (e.g., rank 128 vs rank 32)
        by zero-padding smaller tensors to match the largest.

        Zero-padding is mathematically safe: the extra dimensions contribute
        nothing (zero weight = no effect), preserving all LoRA information.

        Args:
            tensors: List of tensors for a given key
            key: The tensor key name (for logging)

        Returns:
            List of tensors all padded to the same shape
        """
        if len(tensors) <= 1:
            return tensors

        # Find the maximum shape across all dimensions
        max_shape = list(tensors[0].shape)
        needs_padding = False
        for t in tensors[1:]:
            for dim, size in enumerate(t.shape):
                if dim < len(max_shape):
                    if size > max_shape[dim]:
                        max_shape[dim] = size
                        needs_padding = True
                else:
                    max_shape.append(size)
                    needs_padding = True

        # Extend max_shape for tensors with more dimensions
        for t in tensors:
            for dim in range(len(max_shape), len(t.shape)):
                max_shape.append(t.shape[dim])
                needs_padding = True

        max_shape = tuple(max_shape)

        # If all tensors already match, no padding needed
        all_match = all(t.shape == max_shape for t in tensors)
        if all_match:
            return tensors

        # Pad each tensor to max_shape
        padded_tensors = []
        for i, t in enumerate(tensors):
            if t.shape == max_shape:
                padded_tensors.append(t)
            else:
                # Calculate padding for each dimension
                # pad format: (left_0, right_0, left_1, right_1, ...)
                pad_dims = []
                for dim in range(len(t.shape)):
                    diff = max_shape[dim] - t.shape[dim]
                    pad_dims.extend([0, diff])  # pad only at the end
                # Handle extra dimensions in max_shape
                for dim in range(len(t.shape), len(max_shape)):
                    pad_dims.extend([0, max_shape[dim]])

                # Reverse for torch.nn.functional.pad (it expects reverse order)
                pad_dims = pad_dims[::-1]

                padded = torch.nn.functional.pad(t, pad_dims, mode='constant', value=0.0)
                padded_tensors.append(padded)

                self._log(f"[Apex LoRA Merge] Padded tensor {i} for key '{key}': "
                          f"{t.shape} -> {padded.shape}")

        return padded_tensors

    def _merge_add(self, lora_tensors: List[Dict]) -> Dict[str, torch.Tensor]:
        """Simple weighted addition merge."""
        self._log("[Apex LoRA Merge] Merging with ADD algorithm")

        merged = {}
        original_dtypes = {}

        all_keys = set()
        for lora in lora_tensors:
            all_keys.update(lora['data'].keys())

        for key in all_keys:
            tensors_for_key = []
            strengths_for_key = []

            for lora in lora_tensors:
                if key in lora['data']:
                    tensor = lora['data'][key]
                    strength = lora['strength']

                    if key not in original_dtypes:
                        original_dtypes[key] = tensor.dtype

                    tensor_fp32 = tensor.to(torch.float32)
                    tensors_for_key.append(tensor_fp32)
                    strengths_for_key.append(strength)

            if not tensors_for_key:
                continue

            # Pad to common shape before stacking
            tensors_for_key = self._pad_tensors_to_common_shape(tensors_for_key, key)

            result = torch.zeros_like(tensors_for_key[0])
            for tensor, strength in zip(tensors_for_key, strengths_for_key):
                result += tensor * strength
            merged[key] = result.to(original_dtypes[key])

        return merged

    def _merge_ties(self, lora_tensors: List[Dict], density: float) -> Dict[str, torch.Tensor]:
        """
        TIES merge algorithm (Trim, Elect Sign, Merge).
        Reference: "TIES-Merging: Resolving Interference When Merging Models"
        """
        self._log(f"[Apex LoRA Merge] Merging with TIES algorithm (density={density})")

        merged = {}
        original_dtypes = {}

        all_keys = set()
        for lora in lora_tensors:
            all_keys.update(lora['data'].keys())

        for key in all_keys:
            tensors_for_key = []
            strengths_for_key = []

            for lora in lora_tensors:
                if key in lora['data']:
                    tensor = lora['data'][key]
                    strength = lora['strength']

                    if key not in original_dtypes:
                        original_dtypes[key] = tensor.dtype

                    tensor_fp32 = tensor.to(torch.float32) * strength
                    tensors_for_key.append(tensor_fp32)
                    strengths_for_key.append(strength)

            if not tensors_for_key:
                continue

            # Pad to common shape before stacking
            tensors_for_key = self._pad_tensors_to_common_shape(tensors_for_key, key)

            stacked = torch.stack(tensors_for_key)
            abs_values = torch.abs(stacked)

            flat_abs = abs_values.flatten()
            k = max(1, int(len(flat_abs) * density))
            threshold_val = torch.topk(flat_abs, k).values[-1]
            mask = abs_values >= threshold_val

            sign_sum = torch.sum(torch.sign(stacked) * mask.float(), dim=0)
            elected_sign = torch.sign(sign_sum)

            masked_values = stacked * mask.float()
            sum_values = torch.sum(masked_values * elected_sign, dim=0)
            count = torch.sum(mask.float(), dim=0).clamp(min=1)

            result = (sum_values / count) * elected_sign
            merged[key] = result.to(original_dtypes[key])

        return merged

    def _merge_dare_linear(self, lora_tensors: List[Dict], density: float) -> Dict[str, torch.Tensor]:
        """
        DARE (Drop And REscale) merge with linear drop rate.
        Reference: "Language Models are Super Mario: Absorbing Abilities from Homologous Models"
        """
        self._log(f"[Apex LoRA Merge] Merging with DARE-Linear algorithm (density={density})")

        merged = {}
        original_dtypes = {}

        all_keys = set()
        for lora in lora_tensors:
            all_keys.update(lora['data'].keys())

        for key in all_keys:
            tensors_for_key = []

            for lora in lora_tensors:
                if key in lora['data']:
                    tensor = lora['data'][key]
                    strength = lora['strength']

                    if key not in original_dtypes:
                        original_dtypes[key] = tensor.dtype

                    tensor_fp32 = tensor.to(torch.float32) * strength

                    drop_mask = torch.rand_like(tensor_fp32) < density
                    tensor_dare = tensor_fp32 * drop_mask.float()
                    tensor_dare = tensor_dare / (density + 1e-10)

                    tensors_for_key.append(tensor_dare)

            if not tensors_for_key:
                continue

            # Pad to common shape before stacking
            tensors_for_key = self._pad_tensors_to_common_shape(tensors_for_key, key)

            result = torch.mean(torch.stack(tensors_for_key), dim=0)
            merged[key] = result.to(original_dtypes[key])

        return merged

    def _merge_dare_ties(self, lora_tensors: List[Dict], density: float) -> Dict[str, torch.Tensor]:
        """
        Combined DARE + TIES algorithm.
        Applies DARE dropout first, then TIES sign election and merging.
        """
        self._log(f"[Apex LoRA Merge] Merging with DARE-TIES algorithm (density={density})")

        merged = {}
        original_dtypes = {}

        all_keys = set()
        for lora in lora_tensors:
            all_keys.update(lora['data'].keys())

        for key in all_keys:
            tensors_for_key = []

            for lora in lora_tensors:
                if key in lora['data']:
                    tensor = lora['data'][key]
                    strength = lora['strength']

                    if key not in original_dtypes:
                        original_dtypes[key] = tensor.dtype

                    tensor_fp32 = tensor.to(torch.float32) * strength

                    drop_mask = torch.rand_like(tensor_fp32) < density
                    tensor_dare = tensor_fp32 * drop_mask.float() / (density + 1e-10)

                    tensors_for_key.append(tensor_dare)

            if not tensors_for_key:
                continue

            # Pad to common shape before stacking
            tensors_for_key = self._pad_tensors_to_common_shape(tensors_for_key, key)

            stacked = torch.stack(tensors_for_key)
            abs_values = torch.abs(stacked)

            flat_abs = abs_values.flatten()
            k = max(1, int(len(flat_abs) * density))
            threshold_val = torch.topk(flat_abs, k).values[-1]
            mask = abs_values >= threshold_val

            sign_sum = torch.sum(torch.sign(stacked) * mask.float(), dim=0)
            elected_sign = torch.sign(sign_sum)

            masked_values = stacked * mask.float()
            sum_values = torch.sum(masked_values * elected_sign, dim=0)
            count = torch.sum(mask.float(), dim=0).clamp(min=1)

            result = (sum_values / count) * elected_sign
            merged[key] = result.to(original_dtypes[key])

        return merged

    def _merge_svd(self, lora_tensors: List[Dict], rank: int, threshold: float) -> Dict[str, torch.Tensor]:
        """
        SVD-based merge with rank reduction.
        Decomposes each LoRA, combines in latent space, reconstructs.
        """
        self._log(f"[Apex LoRA Merge] Merging with SVD algorithm (rank={rank}, threshold={threshold})")

        merged = {}
        original_dtypes = {}

        all_keys = set()
        for lora in lora_tensors:
            all_keys.update(lora['data'].keys())

        for key in all_keys:
            tensors_for_key = []
            strengths_for_key = []

            for lora in lora_tensors:
                if key in lora['data']:
                    tensor = lora['data'][key]
                    strength = lora['strength']

                    if key not in original_dtypes:
                        original_dtypes[key] = tensor.dtype

                    tensor_fp32 = tensor.to(torch.float32) * strength
                    tensors_for_key.append(tensor_fp32)
                    strengths_for_key.append(strength)

            if not tensors_for_key:
                continue

            # Pad to common shape before stacking
            tensors_for_key = self._pad_tensors_to_common_shape(tensors_for_key, key)

            avg_tensor = torch.mean(torch.stack(tensors_for_key), dim=0)

            original_shape = avg_tensor.shape
            if len(original_shape) > 2:
                avg_tensor = avg_tensor.reshape(original_shape[0], -1)
            elif len(original_shape) == 1:
                avg_tensor = avg_tensor.unsqueeze(0)

            try:
                U, S, Vh = torch.linalg.svd(avg_tensor, full_matrices=False)

                effective_rank = min(rank, len(S))
                significant = S > (threshold * S[0])
                effective_rank = min(effective_rank, significant.sum().item())
                effective_rank = max(1, effective_rank)

                U_reduced = U[:, :effective_rank]
                S_reduced = S[:effective_rank]
                Vh_reduced = Vh[:effective_rank, :]

                reconstructed = U_reduced @ torch.diag(S_reduced) @ Vh_reduced
                reconstructed = reconstructed.reshape(original_shape)
                merged[key] = reconstructed.to(original_dtypes[key])

            except Exception as e:
                self._log(f"[Apex LoRA Merge] SVD failed for key '{key}': {e}, using average")
                merged[key] = avg_tensor.reshape(original_shape).to(original_dtypes[key])

        return merged

    def _save_merged_lora(self, state_dict: Dict[str, torch.Tensor],
                          lora_configs: List[Dict], algorithm: str,
                          save_path: str = "") -> str:
        """
        Save merged LoRA to disk.

        Args:
            state_dict: Merged LoRA state dict
            lora_configs: Original LoRA configurations (for naming)
            algorithm: Algorithm used (for naming)
            save_path: Subfolder path within loras directory to save merged file

        Returns:
            Full path to saved file
        """
        lora_root = folder_paths.get_folder_paths("loras")[0]

        if save_path:
            output_dir = os.path.join(lora_root, save_path)
        else:
            output_dir = lora_root
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        lora_names = "_".join([cfg['name'].split('.')[0][:20] for cfg in lora_configs[:3]])
        filename = f"merged_{algorithm}_{lora_names}_{timestamp}.safetensors"
        output_path = os.path.join(output_dir, filename)

        try:
            from safetensors.torch import save_file
            save_file(state_dict, output_path)
            self._log(f"[Apex LoRA Merge] Saved merged LoRA: {output_path}")
        except ImportError:
            torch.save(state_dict, output_path.replace('.safetensors', '.pt'))
            output_path = output_path.replace('.safetensors', '.pt')
            self._log(f"[Apex LoRA Merge] Saved merged LoRA (torch format): {output_path}")

        return output_path

# Node registration
NODE_CLASS_MAPPINGS = {
    "ApexLoRAMerge": ApexLoRAMerge
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexLoRAMerge": "Apex LoRA Merge"
}
