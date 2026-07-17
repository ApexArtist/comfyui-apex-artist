#!/usr/bin/env python3
"""
Apex Model Quantizer Node - Convert model weights to quantized formats
Wraps the convert_to_quant library for in-UI model quantization
Supports FP8, INT8, NVFP4, MXFP8 with optional learned rounding optimization
"""
import os
import sys
import tempfile
import json
import re
from pathlib import Path

import torch
import folder_paths

# Try to import convert_to_quant
try:
    from convert_to_quant import quantize
    from convert_to_quant.constants import MODEL_FILTERS
    CONVERT_TO_QUANT_AVAILABLE = True
except ImportError:
    CONVERT_TO_QUANT_AVAILABLE = False
    MODEL_FILTERS = {}


class ApexModelQuantizer:
    """
    Quantize safetensors model weights to reduced-precision formats
    (FP8, INT8, NVFP4, MXFP8) with optional learned rounding optimization.
    
    This node wraps the convert_to_quant library, providing a ComfyUI-native
    interface for model quantization. It processes model files on disk and
    outputs the path to the quantized model.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        quant_formats = ["fp8", "int8", "nvfp4", "mxfp8"]
        scaling_modes = ["tensor", "row", "block"]
        optimizers = ["prodigy", "adamw", "radam", "original"]
        lr_schedules = ["plateau", "exponential", "adaptive"]
        
        # Build model filter options from the library's MODEL_FILTERS registry
        model_filter_options = {}
        for filter_name, filter_cfg in MODEL_FILTERS.items():
            display_name = filter_cfg.get("help", filter_name).split(" ")[0] if filter_cfg.get("help") else filter_name
            model_filter_options[filter_name] = ("BOOLEAN", {"default": False})
        
        inputs = {
            "required": {
                "model_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Path to .safetensors model file"
                }),
                "quant_format": (quant_formats, {
                    "default": "fp8",
                    "tooltip": "Quantization format: FP8 (widest support), INT8, NVFP4 (Blackwell), MXFP8 (Blackwell)"
                }),
                "simple_mode": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Simple quantization (fast) vs Learned Rounding optimization (slow, higher quality)"
                }),
                "output_dir": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Output directory (leave empty for ComfyUI models/quantized)"
                }),
            },
            "optional": {
                "scaling_mode": (scaling_modes, {
                    "default": "tensor",
                    "tooltip": "FP8 scaling mode: tensor (1 global scale), row (per-row), block (2D tiles)"
                }),
                "block_size": ("INT", {
                    "default": 128,
                    "min": 16,
                    "max": 1024,
                    "step": 16,
                    "tooltip": "Block/group size for block-wise quantization (INT8/block scaling)"
                }),
                "num_iter": ("INT", {
                    "default": 4000,
                    "min": 100,
                    "max": 50000,
                    "step": 100,
                    "tooltip": "Number of optimization iterations per tensor (learned rounding)"
                }),
                "optimizer": (optimizers, {
                    "default": "prodigy",
                    "tooltip": "Optimization algorithm for learned rounding"
                }),
                "learning_rate": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0001,
                    "max": 10.0,
                    "step": 0.1,
                    "tooltip": "Initial learning rate for optimizer"
                }),
                "lr_schedule": (lr_schedules, {
                    "default": "plateau",
                    "tooltip": "Learning rate schedule"
                }),
                "top_p": ("FLOAT", {
                    "default": 0.2,
                    "min": 0.01,
                    "max": 1.0,
                    "step": 0.01,
                    "tooltip": "Proportion of principal components (SVD) to use"
                }),
                "calib_samples": ("INT", {
                    "default": 3072,
                    "min": 64,
                    "max": 65536,
                    "step": 64,
                    "tooltip": "Number of random samples for bias correction"
                }),
                "use_heur": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Skip layers with poor quantization characteristics"
                }),
                "full_precision_mm": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Use full precision for matrix multiplication in quantized layers"
                }),
                "input_scale": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Include input_scale tensor for quantized layers"
                }),
                "low_memory": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Use streaming tensor loading to reduce RAM usage"
                }),
                "device": (["auto", "cpu", "cuda"], {
                    "default": "auto",
                    "tooltip": "Device for quantization (auto = use CUDA if available)"
                }),
                "exclude_layers": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Regex pattern for layers to exclude from quantization"
                }),
                "custom_layers": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Regex pattern for layers to quantize with custom type"
                }),
                "custom_type": (["", "fp8", "int8", "mxfp8", "nvfp4"], {
                    "default": "",
                    "tooltip": "Quantization type for custom layer matches"
                }),
                "fallback": (["", "fp8", "int8", "mxfp8", "nvfp4"], {
                    "default": "",
                    "tooltip": "Fallback quantization type for excluded layers"
                }),
                "convrot": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Enable group-wise Hadamard rotation for INT8 row-wise quantization"
                }),
                "convrot_group_size": ("INT", {
                    "default": 256,
                    "min": 4,
                    "max": 1024,
                    "step": 4,
                    "tooltip": "Group size for ConvRot (must be power of 4)"
                }),
                "save_quant_metadata": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Save quantization metadata in safetensors header"
                }),
                "manual_seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 2147483647,
                    "step": 1,
                    "tooltip": "Manual seed for reproducibility (-1 = random)"
                }),
            }
        }
        
        # Add model filter flags dynamically
        if model_filter_options:
            inputs["optional"].update(model_filter_options)
        
        return inputs
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("quantized_path", "quantization_info")
    FUNCTION = "quantize_model"
    CATEGORY = "Apex Artist/Model"
    
    def quantize_model(self, model_path, quant_format="fp8", simple_mode=True, output_dir="",
                       scaling_mode="tensor", block_size=128, num_iter=4000,
                       optimizer="prodigy", learning_rate=1.0, lr_schedule="plateau",
                       top_p=0.2, calib_samples=3072, use_heur=False,
                       full_precision_mm=False, input_scale=False, low_memory=False,
                       device="auto", exclude_layers="", custom_layers="",
                       custom_type="", fallback="", convrot=False,
                       convrot_group_size=256, save_quant_metadata=False,
                       manual_seed=-1, **kwargs):
        
        if not CONVERT_TO_QUANT_AVAILABLE:
            raise RuntimeError(
                "convert_to_quant library is not installed. "
                "Please install it with: pip install convert-to-quant"
            )
        
        # Validate model path
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        if not model_path.endswith(".safetensors"):
            raise ValueError(f"Input must be a .safetensors file, got: {model_path}")
        
        # Determine output directory
        if not output_dir:
            output_dir = os.path.join(folder_paths.models_dir, "quantized")
        os.makedirs(output_dir, exist_ok=True)
        
        # Build output filename
        base_name = os.path.splitext(os.path.basename(model_path))[0]
        prefix = "simple_" if simple_mode else "learned_"
        
        # Add model filter flags to filename
        filter_suffix = ""
        for filter_name in MODEL_FILTERS:
            if kwargs.get(filter_name, False):
                filter_suffix += f"_{filter_name}"
        
        output_filename = f"{base_name}_{prefix}{quant_format}{filter_suffix}.safetensors"
        output_path = os.path.join(output_dir, output_filename)
        
        # Resolve device
        if device == "auto":
            device_arg = None  # Let library auto-detect
        else:
            device_arg = device
        
        # Build kwargs for quantize function
        quant_kwargs = {
            "simple": simple_mode,
            "scaling_mode": scaling_mode,
            "num_iter": num_iter,
            "optimizer": optimizer,
            "lr": learning_rate,
            "lr_schedule": lr_schedule,
            "top_p": top_p,
            "calib_samples": calib_samples,
            "heur": use_heur,
            "full_precision_matrix_mult": full_precision_mm,
            "input_scale": input_scale,
            "low_memory": low_memory,
            "device": device_arg,
            "save_quant_metadata": save_quant_metadata,
            "manual_seed": manual_seed if manual_seed >= 0 else -1,
        }
        
        # Add format-specific flags
        if quant_format == "int8":
            quant_kwargs["int8"] = True
            if scaling_mode != "tensor":
                quant_kwargs["block_size"] = block_size
        elif quant_format == "nvfp4":
            quant_kwargs["nvfp4"] = True
        elif quant_format == "mxfp8":
            quant_kwargs["mxfp8"] = True
        else:  # fp8
            if scaling_mode in ("block", "block2d", "block3d"):
                quant_kwargs["block_size"] = block_size
        
        # Add optional parameters
        if exclude_layers:
            quant_kwargs["exclude_layers"] = exclude_layers
        if custom_layers:
            quant_kwargs["custom_layers"] = custom_layers
        if custom_type:
            quant_kwargs["custom_type"] = custom_type
        if fallback:
            quant_kwargs["fallback"] = fallback
        if convrot:
            quant_kwargs["convrot"] = True
            quant_kwargs["convrot_group_size"] = convrot_group_size
        
        # Add model filter flags
        for filter_name in MODEL_FILTERS:
            if kwargs.get(filter_name, False):
                quant_kwargs[filter_name] = True
        
        # Run quantization
        print(f"[ApexModelQuantizer] Quantizing: {model_path}")
        print(f"[ApexModelQuantizer] Format: {quant_format.upper()}, Simple: {simple_mode}")
        print(f"[ApexModelQuantizer] Output: {output_path}")
        
        try:
            quantize(input=model_path, output=output_path, **quant_kwargs)
        except Exception as e:
            raise RuntimeError(f"Quantization failed: {str(e)}")
        
        # Build info string
        info_parts = [
            f"Format: {quant_format.upper()}",
            f"Mode: {'Simple' if simple_mode else 'Learned Rounding'}",
            f"Scaling: {scaling_mode}",
        ]
        if quant_format == "int8" and scaling_mode != "tensor":
            info_parts.append(f"Block Size: {block_size}")
        if not simple_mode:
            info_parts.append(f"Iterations: {num_iter}")
            info_parts.append(f"Optimizer: {optimizer}")
            info_parts.append(f"Top-P: {top_p}")
        
        # Add active filters
        active_filters = [f for f in MODEL_FILTERS if kwargs.get(f, False)]
        if active_filters:
            info_parts.append(f"Filters: {', '.join(active_filters)}")
        
        info = " | ".join(info_parts)
        
        return (output_path, info)


class ApexQuantizedModelLoader:
    """
    Load a previously quantized model into the ComfyUI graph.
    This node outputs a model that can be used with standard ComfyUI
    checkpoint loading workflows.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "placeholder": "Path to quantized .safetensors model file"
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("model_path",)
    FUNCTION = "load_quantized"
    CATEGORY = "Apex Artist/Model"
    
    def load_quantized(self, model_path):
        if not model_path or not os.path.exists(model_path):
            raise FileNotFoundError(f"Quantized model file not found: {model_path}")
        
        if not model_path.endswith(".safetensors"):
            raise ValueError(f"File must be a .safetensors file, got: {model_path}")
        
        return (model_path,)


# Node mappings
NODE_CLASS_MAPPINGS = {
    "ApexModelQuantizer": ApexModelQuantizer,
    "ApexQuantizedModelLoader": ApexQuantizedModelLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ApexModelQuantizer": "Apex Model Quantizer",
    "ApexQuantizedModelLoader": "Apex Quantized Model Loader",
}