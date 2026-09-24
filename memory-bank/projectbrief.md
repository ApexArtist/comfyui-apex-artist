# Project Brief

## What This Project Does
ComfyUI Apex Artist provides 9 custom nodes for ComfyUI: image processing (blur, sharpen, blend, depth-to-normal), panorama viewing (HDRI viewer), LoRA loading with browser UI, prompt presets with categories, and JSON lookup utilities.

## Core Requirements
- Integrate with native ComfyUI conventions (graph, tensors, folder_paths, previews)
- Maintain backward compatibility with existing workflows
- Support batched images and device-aware tensor processing
- Keep dependencies minimal; verification is manual (browser/ComfyUI plus `node --check`) — the automated test scripts were removed September 23, 2026 as dev-only material

## Current State
- Version 2.3.0 committed and tagged locally on September 24, 2026 (9 registered nodes); the push to main is blocked on GitHub credentials, so registry publication has not run
- Core image processing functional and tested
- HDRI socket preview repaired and regression-tested; live browser smoke test pending
- Character prompt node and API registered; isolated storage/random selection verified by the character validator (removed 2026-09-23)
- Not release-ready due to HDRI and metadata validation gaps
