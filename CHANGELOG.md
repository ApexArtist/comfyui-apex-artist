# Changelog

## 2.2.0 — 2026-09-21 (prepared locally; unpublished)

### Added
- Apex Character Prompt: 12 categories, 221 bundled presets, deterministic weighted selection, 13 text outputs, and optional leading free-text input.
- Separate installation-shared user prompt library with atomic writes, revision conflict detection, import/export, and live dropdown refresh. Bundled factory presets remain read-only.
- Regression coverage for core image processing, prompt storage/API/UI, character prompts, and HDRI socket previews.

### Changed
- Prompt Save/Manage dialogs: prefilled drafts, inline validation, Save & Use, grouped and paginated search results, delete confirmation/undo, and sticky top-right Close controls.
- Gaussian blur uses separable convolution; masks follow the image device and dtype.
- Release metadata now lists all nine registered nodes and matches the declared OpenCV dependency.
- Consolidated project documentation and prepared consistent 2.2.0 version metadata.

### Fixed
- HDRI preview uses separate source panorama metadata rather than projected output images; fixes back-view yaw, preview lifetime, stale loads, exposure, lens, and aspect handling.
- LoRA API path checks compare resolved directory components, including thumbnail boundaries.
- LoRA loader explicitly imports comfy.sd; lens API reads defaults without instantiating prompt state.

### Upgrade notes
- Restart ComfyUI and hard-refresh the browser.
- Back up customized bundled preset JSON before updating. Prompt user presets are stored under ComfyUI's configured user directory; export user presets alongside workflows that reference them.
- Added character presets change the weighted Random pool; named selections are unaffected.
- The character preset API still edits its extension-local JSON; it does not yet use the prompt user-store design.

### Validation and remaining checks
- Passed: 7 core tests, 10 prompt store/API tests, 6 HDRI backend tests, 105 character checks, character JSON synchronization, prompt frontend harness, 11 HDRI frontend checks, and frontend syntax checks.
- Real-browser smoke tests and clean-install validation remain pending; automated checks do not establish full release readiness.
- Preserved legacy diagnostics `scripts/test_ground_height_visual.py` and `scripts/test_hdri_viewer_preview.mjs` target removed height controls/old preview contracts. They are not part of the passing current regression suite; use `scripts/test_hdri_socket.py` and `.mjs` instead.
- The existing GitHub workflow publishes to the registry when a push to main changes pyproject.toml. No push or publication is part of this local preparation.