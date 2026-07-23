#!/usr/bin/env python3
"""
Apex Load Model Node - Advanced diffusion model loader with weight dtype selection
Provides fp16, bf16, fp8, and fp32 weight loading options with cublas optimization
Based on Kijai's DiffusionModelLoaderKJ implementation
"""
import torch
import folder_paths
import comfy.sd
import comfy.utils
import logging
from comfy.cli_args import args


def _load_diffusion_model_apex(unet_path, model_options=None, extra_state_dict=None):
    """
    Load diffusion model from path with optional extra state dict merging.
    
    Args:
        unet_path: Full path to the diffusion model file
        model_options: Dict of model loading options (dtype, etc.)
        extra_state_dict: Optional path to additional state dict to merge
        
    Returns:
        Loaded model with cached_patcher_init
    """
    model_options = {} if model_options is None else dict(model_options)

    sd, metadata = comfy.utils.load_torch_file(unet_path, return_metadata=True)
    
    # Merge extra state dict if provided
    if extra_state_dict is not None:
        extra_sd = comfy.utils.load_torch_file(extra_state_dict)
        sd.update(extra_sd)
        del extra_sd

        # Handle prefix replacement for merged state dicts
        diffusion_model_prefix = comfy.sd.model_detection.unet_prefix_from_state_dict(sd)
        sd = comfy.utils.state_dict_prefix_replace(sd, {diffusion_model_prefix: ""}, filter_keys=False)

    # Load the diffusion model
    model = comfy.sd.load_diffusion_model_state_dict(
        sd,
        model_options=model_options,
        metadata=metadata,
    )

    # Store init parameters for proper model management
    model.cached_patcher_init = (_load_diffusion_model_apex, (unet_path, model_options, extra_state_dict))
    
    return model


class ApexLoadModel:
    """
    Advanced diffusion model loader with weight dtype selection and optimization options.
    
    Loads diffusion models (UNet/DiT) with comprehensive weight precision options
    including fp16, bf16, fp8 variants, and fp32. Supports CuBLAS optimization
    and custom path loading.
    
    Features:
    - Multiple weight dtype options (fp16, bf16, fp8, fp32)
    - Separate compute dtype control
    - FP8 optimization flag support
    - CuBLAS linear optimization toggle
    - Custom path support for browsing any model location
    - Extra state dict merging (e.g., for VACE modules)
    
    Note: For full checkpoint loading (with CLIP/VAE), use ComfyUI's native
    CheckpointLoaderSimple node instead.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_name": (folder_paths.get_filename_list("diffusion_models"), {
                    "tooltip": "The diffusion model (UNet/DiT) file to load from the diffusion_models folder"
                }),
                "weight_dtype": ([
                    "default",
                    "fp8_e4m3fn",
                    "fp8_e4m3fn_fast",
                    "fp8_e5m2",
                    "fp16",
                    "bf16",
                    "fp32"
                ], {
                    "default": "default",
                    "tooltip": (
                        "Weight storage precision format:\n\n"
                        "• default — Use ComfyUI's default behavior\n"
                        "• fp8_e4m3fn — FP8 E4M3 format (8-bit, VRAM efficient)\n"
                        "• fp8_e4m3fn_fast — FP8 E4M3 with optimization flags (faster inference)\n"
                        "• fp8_e5m2 — FP8 E5M2 format (alternate 8-bit format)\n"
                        "• fp16 — Half precision (16-bit, balanced speed/quality)\n"
                        "• bf16 — Brain float 16 (better for training, newer GPUs)\n"
                        "• fp32 — Full precision (32-bit, highest quality, slow)\n\n"
                        "Lower precision = less VRAM, faster inference, but may reduce quality.\n"
                        "Recommended: fp16 for most uses, fp8_e4m3fn for VRAM-constrained systems."
                    )
                }),
                "compute_dtype": ([
                    "default",
                    "fp16",
                    "bf16",
                    "fp32"
                ], {
                    "default": "default",
                    "tooltip": (
                        "Computation precision (can differ from weight storage):\n\n"
                        "• default — Use model's native compute dtype\n"
                        "• fp16 — Compute in half precision\n"
                        "• bf16 — Compute in brain float 16\n"
                        "• fp32 — Compute in full precision\n\n"
                        "You can load weights in fp8 but compute in fp16 for better quality."
                    )
                }),
                "patch_cublaslinear": ("BOOLEAN", {
                    "default": False,
                    "tooltip": (
                        "Enable CuBLAS linear optimization (cublas_ops).\n"
                        "Can improve performance on some systems but may cause issues on others.\n"
                        "Requires compatible CUDA setup."
                    )
                }),
            },
            "optional": {
                "custom_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": (
                        "Custom model path (browse from anywhere on your system).\n"
                        "Priority: If provided, this overrides the model_name dropdown.\n"
                        "Supports: .safetensors, .ckpt, .pt, .pth, .bin"
                    )
                }),
                "extra_state_dict": ("STRING", {
                    "forceInput": True,
                    "tooltip": (
                        "Path to additional state dict to merge with the main model.\n"
                        "Useful for adding modules like VACE to WanVideoModel.\n"
                        "Use DiffusionModelSelector or provide full path."
                    )
                })
            }
        }
    
    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_model"
    CATEGORY = "Apex Artist/Models"
    DESCRIPTION = (
        "Load diffusion models (UNet/DiT) with advanced weight dtype selection and optimizations. "
        "Supports fp16, bf16, fp8, fp32 with CuBLAS optimization. "
        "For full checkpoints with CLIP/VAE, use ComfyUI's native loader instead."
    )

    def load_model(self, model_name, weight_dtype="default", compute_dtype="default", 
                   patch_cublaslinear=False, custom_path="", extra_state_dict=None):
        """
        Load diffusion model with specified weight and compute dtypes
        
        Args:
            model_name: Model filename from diffusion_models folder
            weight_dtype: Weight storage precision format
            compute_dtype: Computation precision format
            patch_cublaslinear: Enable CuBLAS linear optimization
            custom_path: Optional custom path to model file (takes priority over model_name)
            extra_state_dict: Optional path to additional state dict to merge
            
        Returns:
            Tuple of (MODEL,)
        """
        # Map dtype strings to torch dtypes
        DTYPE_MAP = {
            "fp8_e4m3fn": torch.float8_e4m3fn,
            "fp8_e5m2": torch.float8_e5m2,
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
            "fp32": torch.float32
        }
        
        # Build model options with weight dtype
        model_options = {}
        
        if weight_dtype != "default":
            if dtype := DTYPE_MAP.get(weight_dtype):
                model_options["dtype"] = dtype
                logging.info(f"[Apex Load Model] Setting weight dtype to {dtype}")
            
            # Handle fp8_e4m3fn_fast variant (enables optimization flags)
            if weight_dtype == "fp8_e4m3fn_fast":
                model_options["dtype"] = torch.float8_e4m3fn
                model_options["fp8_optimizations"] = True
                logging.info(f"[Apex Load Model] Enabled FP8 optimizations")
        
        # Handle CuBLAS linear patching
        if patch_cublaslinear:
            args.fast.add("cublas_ops")
            logging.info("[Apex Load Model] Enabled cublas_ops optimization")
        else:
            args.fast.discard("cublas_ops")
        
        # Determine which path to use (custom_path has priority)
        if custom_path and custom_path.strip():
            # Use custom path - validate file exists and has valid extension
            unet_path = custom_path.strip()
            
            # Validate file existence
            import os
            if not os.path.isfile(unet_path):
                raise FileNotFoundError(f"Custom model file not found: {unet_path}")
            
            # Validate file extension
            valid_extensions = ('.safetensors', '.ckpt', '.pt', '.pth', '.bin')
            if not unet_path.lower().endswith(valid_extensions):
                raise ValueError(
                    f"Invalid model file extension. Supported: {', '.join(valid_extensions)}\n"
                    f"Got: {unet_path}"
                )
            
            logging.info(f"[Apex Load Model] Using custom path: {unet_path}")
        else:
            # Use native dropdown selection
            unet_path = folder_paths.get_full_path_or_raise("diffusion_models", model_name)
            logging.info(f"[Apex Load Model] Loading model: {model_name}")
        
        # Load diffusion model
        try:
            model = _load_diffusion_model_apex(
                unet_path,
                model_options=model_options,
                extra_state_dict=extra_state_dict
            )
            
            # Set compute dtype if specified (separate from weight storage)
            if compute_dtype != "default":
                if compute_torch_dtype := DTYPE_MAP.get(compute_dtype):
                    model.set_model_compute_dtype(compute_torch_dtype)
                    model.force_cast_weights = False
                    logging.info(f"[Apex Load Model] Setting compute dtype to {compute_torch_dtype}")
            
            return (model,)
            
        except Exception as e:
            logging.error(f"[Apex Load Model] Error loading model '{model_name}': {e}")
            raise
