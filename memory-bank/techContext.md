# Technical Context

## Technologies Used
- **Python**: 3.8+ with torch 2.13.0+cu130, numpy, Pillow, aiohttp, aiofiles, opencv-python>=4.8.0
- **ComfyUI**: Minimum version 0.1.0 declared in metadata (not tested on all versions)
- **Frontend**: JavaScript (browser native), Node.js for test harness
- **Platform**: Windows 10/11, PowerShell, VS Code

## Development Setup
- **Workspace**: `F:\AI\ComfyUI Sandbox\ComfyUI\custom_nodes\comfyui-apex-artist`
- **Python**: `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe`
- **CUDA**: Available via torch+cu130
- **Dependencies**: requirements.txt (opencv-python>=4.8.0) needs reconciliation with pyproject.toml/comfyui.yaml before release

## Project Structure
```
comfyui-apex-artist/
├── apex_*.py              # Node implementations
├── apex_*_api.py          # API route handlers
├── apex_utils.py          # Shared utilities
├── __init__.py            # ComfyUI registration
├── web/                   # Frontend modules (4 files, 1 unregistered)
├── lens/                  # Source images for presets
├── lens_previews/         # Generated preview assets
├── scripts/               # Tests, validators, generators
├── memory-bank/           # Context documentation (6 core files)
├── presets/               # JSON data stores
├── pyproject.toml         # Python package metadata
├── comfyui.yaml           # ComfyUI registry metadata
└── README.md, PUBLISH.md  # Documentation
```

## Technical Constraints
- Must support batched IMAGE tensors with variable batch sizes
- Must handle device migration (CPU/CUDA) transparently
- Must validate file paths against ComfyUI security model
- Frontend limited to browser-native APIs (no build step)
- HDRI/LoRA operations currently block async handlers (needs fixing)

## Tool Usage Patterns
### Running Tests

Character node (September 20, 2026): `scripts/validate_character_prompt.py` covers the 12-category library, dropdowns, 13 outputs, deterministic/weighted random selection, bracket variants, the five `/apex/character_presets` CRUD routes, damaged/missing store fallback, and real `__init__.py` registration (heavyweight node imports stubbed). All checks pass.

Prompt presets (September 20, 2026): `scripts/test_prompt_presets.py` uses unittest/aiohttp temporary storage and synthetic package imports; `scripts/test_prompt_presets.mjs` runs a dependency-free DOM/API harness against the actual frontend module loaded in memory. Neither touches real user presets. 10 Python tests and the frontend harness pass; browser integration still needs manual verification.
```powershell
# Core unit tests (29.973s, 7 methods)
& 'F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe' scripts\test_project_core.py

# Character preset validator
& 'F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe' scripts\validate_character_prompt.py

# HDRI socket regressions (11 frontend checks + 6 backend tests)
node scripts\test_hdri_socket.mjs
& 'F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe' scripts\test_hdri_socket.py

# JavaScript syntax check
node --check web\<filename>.js
```

### Important Notes on Testing
- Core tests use synthetic ComfyUI package; don't require full runtime
- Legacy uncommitted test_hdri_viewer_preview.mjs targets obsolete payloads/absent height controls; preserved separately. New socket harness imports via data URL without creating temporary source files.
- Syntax tests pass ≠ ComfyUI/browser integration working
- PowerShell may truncate output; use `Start-Process -Wait` with redirected stdout/stderr for full logs
- No end-to-end benchmark or live integration test suite exists

### Version Management
- Version 2.2.0 in `__init__.py`, `pyproject.toml`, `comfyui.yaml`, `manifest.json`, and `custom_nodes.json`; prepared locally, unpublished
- A push to main changing pyproject.toml triggers the existing registry publish workflow; do not push without authorization
- No automated version update script; manual sync required
- Restart ComfyUI for Python changes; hard-refresh browser for JavaScript

## Development Dependencies
- **Runtime**: All in requirements.txt
- **Testing**: unittest (Python stdlib), Node.js for JS tests
- **No build tools**: Frontend uses browser-native JavaScript
