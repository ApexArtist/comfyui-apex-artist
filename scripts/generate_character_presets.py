#!/usr/bin/env python3
"""
Generate character_presets.json from the built-in library in apex_character_prompt.py.

The built-in library inside apex_character_prompt.py is the source of truth; this script
snapshots it to the on-disk store that the manager UI and API edit.

Usage (always use the ComfyUI virtual environment Python):
    & "F:\\AI\\ComfyUI Sandbox\\ComfyUI\\.venv\\Scripts\\python.exe" scripts\\generate_character_presets.py
    & "F:\\AI\\ComfyUI Sandbox\\ComfyUI\\.venv\\Scripts\\python.exe" scripts\\generate_character_presets.py --check
"""

import argparse
import importlib.util
import json
import os
import sys
import types

NODE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "apex_character_prompt_pkg"


def load_node_module(module_name, file_name):
    """Load a node module as part of a synthetic package so relative imports resolve."""
    path = os.path.join(NODE_DIR, file_name)
    spec = importlib.util.spec_from_file_location(f"{PACKAGE_NAME}.{module_name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Snapshot the built-in character presets to JSON")
    parser.add_argument("--check", action="store_true",
                        help="Verify character_presets.json matches the built-in library")
    args = parser.parse_args()

    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [NODE_DIR]
    sys.modules[PACKAGE_NAME] = package

    load_node_module("apex_prompt", "apex_prompt.py")
    node_module = load_node_module("apex_character_prompt", "apex_character_prompt.py")

    presets = node_module.ApexCharacterPrompt.get_default_presets()
    target = os.path.join(NODE_DIR, node_module.ApexCharacterPrompt.PRESET_FILE_NAME)

    total = 0
    for category, data in presets.items():
        print(f"  {category}: {len(data)}")
        total += len(data)
    print(f"[Apex Character Presets] Total presets: {total}")

    if args.check:
        if not os.path.exists(target):
            print(f"✗ Missing {target}")
            return 1
        with open(target, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing == presets:
            print("✓ character_presets.json matches the built-in library")
            return 0
        print("✗ character_presets.json differs from the built-in library")
        return 1

    payload = json.dumps(presets, indent=2, ensure_ascii=False) + "\n"
    with open(target, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"✓ Wrote {target} ({len(payload)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
