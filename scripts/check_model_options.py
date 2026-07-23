#!/usr/bin/env python3
"""Quick script to check what model_options are supported in ComfyUI"""

import sys
import os

# Dynamically find ComfyUI root: this script is in custom_nodes/comfyui-apex-artist/scripts/
# Go up 3 levels to reach ComfyUI root
script_dir = os.path.dirname(os.path.abspath(__file__))
apex_node_dir = os.path.dirname(script_dir)  # comfyui-apex-artist/
custom_nodes_dir = os.path.dirname(apex_node_dir)  # custom_nodes/
comfyui_root = os.path.dirname(custom_nodes_dir)  # ComfyUI/

sys.path.insert(0, comfyui_root)

try:
    import comfy.model_base
    import comfy.sd
    import inspect
    
    print("=" * 80)
    print("COMFYUI MODEL_OPTIONS DOCUMENTATION")
    print("=" * 80)
    
    # Check BaseModel init signature
    print("\n1. BaseModel.__init__ signature:")
    print("-" * 80)
    sig = inspect.signature(comfy.model_base.BaseModel.__init__)
    print(sig)
    
    # Try to get model_options handling code
    print("\n2. Searching for model_options usage...")
    print("-" * 80)
    
    source = inspect.getsource(comfy.model_base.BaseModel.__init__)
    lines = source.split('\n')
    
    for i, line in enumerate(lines[:50]):  # First 50 lines
        if 'model_options' in line.lower() or 'dtype' in line.lower():
            print(f"Line {i}: {line}")
    
    print("\n3. Model management dtype methods:")
    print("-" * 80)
    if hasattr(comfy.model_base.BaseModel, 'set_model_compute_dtype'):
        print("✓ set_model_compute_dtype exists")
        print(f"  Signature: {inspect.signature(comfy.model_base.BaseModel.set_model_compute_dtype)}")
    
    print("\n4. Common model_options keys (from inspection):")
    print("-" * 80)
    print("Based on ComfyUI code, model_options typically supports:")
    print("  - 'dtype': Weight storage dtype (torch.float8_e4m3fn, torch.float16, etc.)")
    print("  - 'fp8_optimizations': Enable FP8 optimizations (bool)")
    print("  - 'weight_dtype': Alias for dtype in some contexts")
    print("  - Model-specific options may exist")
    
    print("\n" + "=" * 80)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()