# Project Brief

## What This Project Does
ComfyUI Apex Artist provides 9 custom nodes for ComfyUI: image processing (blur, sharpen, blend, depth-to-normal), panorama viewing (HDRI viewer), LoRA loading with browser UI, prompt presets with categories, and JSON lookup utilities.

## Core Requirements
- Integrate with native ComfyUI conventions (graph, tensors, folder_paths, previews)
- Maintain backward compatibility with existing workflows
- Support batched images and device-aware tensor processing
- Keep dependencies minimal; verify changes with runnable tests

## Current State
- Version 2.2.0 prepared locally, 9 registered nodes; not yet published
- Core image processing functional and tested
- HDRI socket preview repaired and regression-tested; live browser smoke test pending
- Character prompt node and API registered; isolated storage/random selection verified by character validator
- Not release-ready due to HDRI and metadata validation gaps
