# Tech Context: comfyui-apex-artist

## Technologies
- **Python**: >=3.8 (tested with 3.10, 3.12)
- **PyTorch**: Core tensor/image processing (provided by ComfyUI)
- **ComfyUI API**: >=0.1.0
- **JavaScript**: Frontend extensions
- **scikit-image**: >=0.19.0

## Development Setup
- **OS**: Windows 10
- **IDE**: Visual Studio Code
- **Python venv**: `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe`
- **ComfyUI root**: `F:\AI\ComfyUI Sandbox\ComfyUI`
- **Custom nodes**: `F:\AI\ComfyUI Sandbox\ComfyUI\custom_nodes`

## Dependencies

### ComfyUI-Provided
- torch, numpy, scipy, Pillow
- folder_paths, node_helpers

### Extra Requirements
- scikit-image >=0.19.0

## Input/Output Types
| Type | Format | Description |
|------|--------|-------------|
| `IMAGE` | `torch.Tensor` (B,H,W,3) float32 [0,1] | RGB image batch |
| `MASK` | `torch.Tensor` (B,H,W) float32 | Alpha mask |
| `INT` | Python int | Integer parameter |
| `FLOAT` | Python float | Float parameter |
| `STRING` | Python str | Text output |

## Common Widget Formats
```python
# Combo box
(["option1", "option2"], {"default": "option1"})

# Slider
("FLOAT", {"default": 1.0, "min": 0.0, "max": 10.0, "step": 0.1})

# Integer
("INT", {"default": 0, "min": 0, "max": 9999})
```

## Version Management & Publishing

### Tool Usage
- **Version update**: `python update_version.py [--patch|--minor|--major] [--dry-run] [--commit] [--tag]`
- **Testing**: Run ComfyUI and test nodes manually
- **Python verification**: Use `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe` for import checks
- **JS syntax check**: `node --check web\filename.js`
- **Publishing workflow**: See `PUBLISH.md` for complete guide

### update_version.py Features
- **Auto-increment**: `--patch`, `--minor`, `--major` flags for semantic versioning
- **Preview mode**: `--dry-run` to see changes before applying
- **Git integration**: `--commit` and `--tag` for automated git workflow
- **Current version detection**: Reads existing version from files
- **Multi-file update**: Updates `__init__.py`, `manifest.json`, `pyproject.toml`, `comfyui.yaml`
- **Colored output**: Visual feedback with emoji indicators (✓, ✗, ⚡)

### Publishing Workflow (Quick Reference)
```bash
# One-line version update and commit
python update_version.py --patch --commit --tag

# Push to remote
git push origin main --tags

# Or see PUBLISH.md for complete workflow
```

## File Structure
```
comfyui-apex-artist/
├── __init__.py              # Node registration
├── apex_*.py                # Node implementations
├── apex_*_api.py            # API endpoints
├── requirements.txt         # Python dependencies
├── manifest.json            # ComfyUI Registry metadata
├── pyproject.toml          # Python project metadata
├── comfyui.yaml            # ComfyUI configuration
├── custom_nodes.json       # Custom nodes metadata
├── PUBLISH.md              # Publishing workflow guide
├── update_version.py       # Version management tool
├── web/                    # Frontend extensions
│   ├── apex_prompt.js
│   ├── apex_lora_loader.js
│   ├── apex_lora_stack.js
│   └── apex_prompt_lens.js
├── lens/                   # Lens preset source images
├── lens_previews/          # Processed lens thumbnails
└── memory-bank/            # Project documentation
    ├── projectbrief.md
    ├── productContext.md
    ├── activeContext.md
    ├── systemPatterns.md
    ├── techContext.md
    ├── progress.md
    └── features.md
```
