# Changelog

## Unreleased

- Let Apex Audio Lyrics download missing official Whisper Turbo files on first transcription. Add a download toggle, reuse complete local models without network access, repair partial processor assets and preserve previous widget positions.

## 2.6.1 - 2026-11-03

- Repair Apex Optional Images sockets after loading, cloning and connection changes. Keep one empty socket, restore numeric order past ten inputs and preserve connected image sources through native node APIs.
- Add portable socket-repair regressions and verify growth to 17 images, reload, middle disconnection and source replacement in the actual frontend.

### Validation

- Passed 21 Python regressions, eight frontend regressions, preset synchronization and metadata/syntax checks. The real frontend grew to 17 images and preserved source order after reload, middle removal and replacement. No new GPU render was needed for this frontend-only fix.

## 2.6.0 - 2026-11-03

- Assemble timeline cuts on a constant frame grid with disk-backed FFmpeg segments, avoiding native list-remux timestamp gaps after trimmed B/C cuts. Mixed audio stays aligned; muted timelines stay silent.

- Supply an explicit LTX 2.5 compatibility patch for separately installed PromptRelay, including Gemma 4 token alignment and scoped guide/mask cleanup.

- Register Apex Audio Lyrics and Apex Optional Images for music-video workflows. Whisper controls use local files and keep prior widget positions.
- Add independent timeline project Save/Open, grid/playhead snapping and the widget-width correction. Preserve the existing cut-window and multi-output export fixes.
- Add portable registration, optional-input, lyric override, path, cut-window and snapshot regressions.

### Validation

- Passed 21 Python regressions, four frontend export tests and preset synchronization. All fourteen node registrations match metadata.
- Sandbox music-video tests completed a 60-second first-frame baseline with all 16 clips and a separate 20-second restored PromptRelay test with singer, instrument and candid branches. The corrected baseline export passed 25 visible-interval and 75 boundary comparisons; the restored native export passed six interval and 17 boundary comparisons, with uniform 24 fps timestamps and aligned audio.
- Native frontend loading and Whisper parameter serialization passed. Timeline sliders and the width callback passed an isolated mounted-editor check; full canvas interaction, clean installation, unrelated-node smoke tests and Manager installation were not repeated for this release.
- Generated camera framing and band identities remain imperfect: the restored test widens too far and briefly duplicates a guitarist. No listening or exact lyric/lip-sync verification was performed. Whisper output remains an editable draft.

## 2.5.0 - 2026-10-23

### Added

- Apex V1 Cut Window reads actual saved V1 joins and returns frame-aligned start, duration, cut position and join count. Use the same start for B-roll audio cropping and placement; edited joins are read on each execution.

### Fixed

- Timeline Export now queues all connected save/combine outputs instead of selecting only the first. Saved-timeline exports still bypass generation loops and preserve each output's encoding settings.

### Validation

- The 80-second music-video run completed with four 20-second main clips and three 5-second B-roll windows covering the joins at 20, 40 and 60 seconds. Both native Save Video nodes saved 80-second outputs; measured audio placement offset was 0 ms. The owner confirmed playback and sync. These runs used workflow routing through End Loop; that connection change is not a custom-node code change.
- Passed: 13 Python regressions, including 5 cut-window tests; 4 frontend export tests; character preset synchronization; Python/JSON/TOML/YAML parsing; frontend syntax; all five version fields and twelve-node metadata consistency. Clean-install and unrelated-node browser smoke tests are not repeated for this release.

## 2.4.0 — 2026-10-23

### Added

- Apex Audio: file or standard AUDIO input, waveform selection, sample-based trimming, 0–200% gain, selection preview and metadata outputs.
- Apex Timeline Editor: embedded video/audio tracks, native VIDEO inputs, append/start/offset placement, thumbnails, linked external clips, trims, split, persistent undo/redo, gain, fades, snapping, scrubbing and missing-source relinking. Standard VIDEO/IMAGE/AUDIO/FPS outputs connect to downstream save/combine nodes; no separate Timeline Render node is registered.

### Fixed

- Depth Blur covers the full depth range; fractional motion/sharpen radii keep image dimensions; half-precision filters use safe computation; RGBA depth produces RGB normals. Dissolve follows opacity and zero-strength Multi Scale Sharpen preserves brightness.
- Blur, blend and LoRA failures report errors instead of silently passing inputs through.
- Character presets use validated atomic user-folder saves with revision conflicts. The manager preserves failed-save drafts and rejects accidental name collisions; missing selections fail explicitly. Character API writes now require the read response's ETag in If-Match.
- LoRA browsing supports all configured roots, prevents stale previews and refreshes changed thumbnails. HDRI views reuse unchanged frames; heavy preview/scan work runs off the event loop.
- Saved timeline exports prune unused input loaders. Clear video cache removes regenerable MP4s only with an idle queue and preserves source media.

### Requirements and upgrade

- Python 3.10+ and ComfyUI 0.42.1+ are the declared tested minimums. Explicit extra requirements are opencv-python>=4.8.0 and aiofiles>=23.2.1. Timeline uses FFmpeg on PATH.
- Restart ComfyUI and hard-refresh the browser. Back up custom libraries before updating. Character edits now live under the configured user directory at apex_artist/character_presets.json; existing bundled edits seed the first user save. Timeline projects persist under the configured output directory at Apex/timelines.

### Validation

- Passed: 71 targeted CPU checks, eight portable regressions, isolated API/browser checks, all eleven node schemas, twenty-seed character-output compatibility, a five-second CPU export at 24 FPS and native loops for 6, 25.25 and 60 seconds with exact audio crops and placement.
- Loop checks used CPU placeholder frames, not AI sampling. No GPU render was run. Owner live smoke testing and a clean installation remain unverified; these results do not establish complete release readiness.
- Documentation and release metadata were consolidated. The owner authorized the 2.4.0 commit, release tag and publication on 2026-10-23.

## 2.3.0 — 2026-09-24

First published release of the 2.x line. It covers everything prepared since v2.1.3, including the 2.2.0 work that was prepared locally on 2026-09-21 and never published.

### Added
- Apex Prompt: new **Apex Color** category with 68 bundled standard and industry colour-grade presets (natural, vibrant, pastel, tonal and graphic treatments, film-stock emulations, cinema DI looks, vintage media, plus an explicit Monochrome Noir opt-in) and a sixth `color_text` output. The `color_preset` dropdown is appended last so saved workflows keep their widget values, and the combined prompt now orders input → environment → lighting → style → color → camera lens.
- Apex Character Prompt: 12 categories, 221 bundled presets, deterministic weighted selection, 13 text outputs, and optional leading free-text input.
- Separate installation-shared user prompt library with atomic writes, revision conflict detection, import/export, and live dropdown refresh. Bundled factory presets remain read-only.
- Regression coverage for core image processing, prompt storage/API/UI, character prompts, and HDRI socket previews (added for 2.2.0, removed from the repository on 2026-09-23 as dev-only material; recoverable from git history).

### Changed
- Prompt Save/Manage dialogs: prefilled drafts, inline validation, Save & Use, grouped and paginated search results, delete confirmation/undo, and sticky top-right Close controls.
- Gaussian blur uses separable convolution; masks follow the image device and dtype.
- Release metadata now lists all nine registered nodes and matches the declared OpenCV dependency.
- Consolidated project documentation; version metadata unified at 2.3.0 for this release.

### Fixed
- Prompt presets no longer push images toward black and white: 29 zero-colour entries — all 8 Apex Style and all 21 Apex Lighting presets that carried no colour vocabulary — now state a colour/palette anchor, and the two within that set that explicitly demanded monochrome (`Film Noir Classic`, `Film Noir Shadow`) keep their noir mood in full colour. `Photorealistic`, which had lost its "true-to-life colors" clause when the JSON library was expanded, is restored. The six matching built-in defaults in `apex_prompt.py` were mirrored so a regenerated JSON keeps the anchors. Monochrome wording in a full Random draw drops from 8.51% to 3.54%; `Noir Detective Office` and `Lightning Storm Flash` intentionally keep their wording for now.
- HDRI preview uses separate source panorama metadata rather than projected output images; fixes back-view yaw, preview lifetime, stale loads, exposure, lens, and aspect handling.
- LoRA API path checks compare resolved directory components, including thumbnail boundaries.
- LoRA loader explicitly imports comfy.sd; lens API reads defaults without instantiating prompt state.

### Upgrade notes
- Restart ComfyUI and hard-refresh the browser.
- Back up customized bundled preset JSON before updating. Prompt user presets are stored under ComfyUI's configured user directory; export user presets alongside workflows that reference them.
- Added character presets change the weighted Random pool; named selections are unaffected.
- Apex Prompt gained a sixth output and a colour dropdown: restart ComfyUI and hard-refresh the browser. Existing workflows keep their selections, links and widget values; the colour grade defaults to `Disabled`.
- The character preset API still edits its extension-local JSON; it does not yet use the prompt user-store design.

### Validation and remaining checks
- Passed: 7 core tests, 10 prompt store/API tests, 6 HDRI backend tests, 105 character checks, character JSON synchronization, prompt frontend harness, 11 HDRI frontend checks, and frontend syntax checks.
- 2026-09-24 release verification (automated, run against the real store and node with a stubbed `folder_paths`): version consistency across all five version files; character preset store in sync (221 presets); `prompt_presets.json` re-parses with Environment 70 / Lighting 50 / Style 36 / Camera Lens 43 / Color 68; legacy four-category user libraries still load and user saves into the new category succeed; the Apex Prompt dropdowns list every preset and `combine_prompts` returns six values with the colour text placed after the look; `node --check` passes for all four frontend files; every `apex_*.py` and `__init__.py` parses; `manifest.json` and `custom_nodes.json` parse. Real-browser smoke tests and clean-install validation remain pending; automated checks do not establish full release readiness.
- The legacy diagnostics (`scripts/test_ground_height_visual.py`, `scripts/test_hdri_viewer_preview.mjs`, `scripts/check_model_options.py`) and the whole development test suite were removed from `scripts/` on 2026-09-23 — nothing there is required for ComfyUI to run the pack, and every deleted file remains recoverable from git history. `scripts/generate_character_presets.py` is kept because `apex_character_prompt.py` names it as the regeneration path for `character_presets.json`. The checks listed above all passed before removal.
- The existing GitHub workflow publishes to the registry when a push to main changes pyproject.toml; the 2.3.0 release push therefore published this version rather than acting as a backup. GitHub Actions run #29 (https://github.com/ApexArtist/comfyui-apex-artist/actions/runs/35989797563) completed with `success` on 2026-09-24 and created registry version 2.3.0 (createdAt 10:53:22Z; `NodeVersionStatusPending` at first verification, activation follows).
