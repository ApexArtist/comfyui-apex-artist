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
├── scripts/               # Preset generator only (test scripts removed 2026-09-23)
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
### Tests — removed September 23, 2026

September 23, 2026: the development test suite (core, prompt-store, HDRI socket, character validator, plus the obsolete diagnostics) was removed from `scripts/` — it is dev-only and not required for ComfyUI to load this pack. All deleted scripts remain recoverable from git (`git show HEAD:scripts/<name>`). The only script kept is `scripts/generate_character_presets.py`, which `apex_character_prompt.py` names as the regeneration path for the shipped `character_presets.json`.

Last full-suite run before removal (September 23, 2026): 7 core tests (3.5 s), 6 HDRI backend tests (1.6 s), 10 prompt-store tests (1.3 s), 105 character checks, 11 HDRI frontend checks, the prompt frontend harness, and `character_presets.json` synchronization all passed — roughly 10 seconds total. This records the last passing state, not a runnable suite: verification is now manual (browser/ComfyUI) plus the `node --check` syntax check below.
```powershell
# Automated Python tests were removed September 23, 2026 (see note above); only the preset generator remains:
& 'F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe' scripts\generate_character_presets.py --check

# Recovery example — deleted scripts are still in git HEAD:
#   git show HEAD:scripts\test_project_core.py

# Recovery examples for the HDRI/prompt tests:
#   git show HEAD:scripts\test_hdri_socket.mjs
#   git show HEAD:scripts\test_hdri_socket.py

# JavaScript syntax check
node --check web\<filename>.js
```

### Important Notes on Testing
- Core tests use synthetic ComfyUI package; don't require full runtime
- The legacy HDRI diagnostics (`test_hdri_viewer_preview.mjs`, `test_ground_height_visual.py`) and the entire test suite were removed September 23, 2026 as dev-only material; the socket contract now lives in systemPatterns.md and deleted scripts are recoverable from git.
- Syntax tests pass ≠ ComfyUI/browser integration working
- PowerShell may truncate output; use `Start-Process -Wait` with redirected stdout/stderr for full logs. A native command whose stderr is merged inside a pipeline (`... 2>&1 | Select-Object -Last 5`) can report exit code 1 even when every test passed; redirect to a file first (`> "$env:TEMP\out.txt" 2>&1`) and only then read `$LASTEXITCODE`. This produced two false failures on September 23, 2026.
- No end-to-end benchmark or live integration test suite exists

### Version Management
- Version **2.3.0** in `__init__.py`, `pyproject.toml`, `comfyui.yaml`, `manifest.json`, and `custom_nodes.json`; committed and tagged `v2.3.0` locally on September 24, 2026 with the repository owner's authorization. **The push to `main` is still pending**: the stored Git Credential Manager token belongs to the GitHub account `apexartistx`, which lacks write access to `ApexArtist/comfyui-apex-artist` and returns `403 Permission denied`
- A push to main changing pyproject.toml triggers the existing registry publish workflow; do not push without authorization (the 2.3.0 release push is authorized; it publishes to the registry once a credential with write access completes the push)
- No automated version update script; manual sync required
- Restart ComfyUI for Python changes; hard-refresh browser for JavaScript

## Development Dependencies
- **Runtime**: All in requirements.txt
- **Testing**: unittest (Python stdlib), Node.js for JS tests
- **No build tools**: Frontend uses browser-native JavaScript
