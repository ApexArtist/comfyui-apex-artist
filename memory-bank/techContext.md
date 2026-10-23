# Technical context

## Runtime

- Python 3.10+; ComfyUI 0.42.1+ is the tested declared minimum.
- Core provides torch, numpy, Pillow, aiohttp and PyAV. Extra requirements: opencv-python>=4.8.0 and aiofiles>=23.2.1.
- Native VIDEO APIs and V3 autogrowing inputs are required by Timeline. FFmpeg must be on PATH.
- Frontend uses browser JavaScript without a build step. Node.js is used for development syntax checks only.

## Layout

- `apex_*.py`: nodes, stores and APIs; `__init__.py`: eleven-node registration.
- `web/`: frontend modules and Timeline helpers.
- `prompt_presets.json`, `character_presets.json`: bundled factory libraries.
- `lens/`, `lens_previews/`: shipped assets; preserve them.
- `scripts/generate_character_presets.py`: factory-library generator/checker.
- `tests/test_regressions.py`: portable CPU regression suite.
- `memory-bank/`: concise project context; release history lives in CHANGELOG.md.

## Development checks

Use the same Python environment as ComfyUI:

```sh
python -m unittest discover -s tests
python scripts/generate_character_presets.py --check
```

Parse Python without creating bytecode, validate JSON/TOML and run `node --check` for every web module. Keep fixture media, test logs, caches and backups outside the package. Tests use synthetic package loading to avoid starting ComfyUI.

A manual ComfyUI restart loads Python changes; Ctrl+Shift+R loads frontend changes. The owner manages this process. Version fields in five files must match. The publish workflow runs when a push to main changes pyproject.toml; see PUBLISH.md.
