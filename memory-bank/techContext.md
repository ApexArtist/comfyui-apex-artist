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

## Tool Usage
- **Versioning**: `python update_version.py X.Y.Z`
- **Testing**: Run ComfyUI and test nodes manually
- **Python verification**: Use `F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe` for import checks
- **JS syntax check**: `node --check web\filename.js`
- **Publishing**: `update_version.py` → commit → push → GitHub Actions
