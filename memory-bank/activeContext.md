# Active Context

## Current Focus
Release preparation September 21, 2026: user requested committing the entire current project, updating version, and no push. Selected minor version 2.2.0 for new character/preset features. Synchronized five version files and nine-node metadata; added CHANGELOG.md and corrected stale publishing instructions. Current core/prompt/HDRI/character regressions and preset synchronization pass. Browser and clean-install checks remain pending. Preserve legacy diagnostics, explicitly excluded from the current passing suite. No release tag or publication during this preparation; a later main push changing pyproject.toml triggers registry publication.

HDRI socket preview repaired September 21, 2026. Backend emits separate `hdri_source` + `hdri_source_scale` UI metadata; source is a bounded first-frame panorama, outputs remain front/back IMAGE batches. Unique temporary preview files prevent overwrites. Back yaw rotates 180 degrees. Frontend uses only source metadata (never projected node.imgs), with per-node tokens/timers, removal cleanup, fisheye/exposure/output-aspect support. Removed sampled IS_CHANGED in favor of native dependency caching. New `scripts/test_hdri_socket.mjs` (11 checks) and `scripts/test_hdri_socket.py` (6 tests) pass. Existing uncommitted height-control harness preserved; it targets absent controls and obsolete UI payload. Browser smoke test pending; restart ComfyUI and refresh browser before use.

Implemented Apex Prompt factory/user preset separation (September 20, 2026); added a free-text input box to the character prompt node (September 21, 2026). Fixed Apex Prompt Save/Manage usability (frontend-only, backend unchanged) on September 21, 2026. Preserving unrelated uncommitted HDRI and character-preset work.

## Prompt Save/Manage Usability Fix (September 21, 2026)
- Follow-up: moved the shared prompt dialog Close button into a sticky top-right header so Manage/Save remain dismissible while scrolling. Frontend harness checks header placement, sticky CSS, and Close removal for both dialogs; harness and JS syntax check pass. Actual browser scrolling still needs a smoke test after a hard refresh.
- `web/apex_prompt.js` only; no changes to store/API/node Python or preset JSON.
- Save dialog now prefills category/name/text from the node's current selection ("Factory X" -> "X Copy"), validates inline (name/whitespace/reserved/empty prompt/weight) without a server round-trip, shows Name/Prompt counters, adds `Save & Use` (saves then applies `User: X` via existing `usePreset`), focuses Name/Prompt, and renames refresh to `Refresh library (keep my draft)`.
- Manager now groups `Factory/User · Category (n)` headers, shows `Showing X of Y` + empty-state, debounces search (150ms) with match highlight, pages at 100 rows with `Show more`, uses inline delete confirm + `Undo delete`, previews import new/conflict counts, uses dated export filenames, and toasts on Save/Use/Delete/Import/Export.
- Node buttons show `Working…`/disabled state while loading; stacked editor-over-manager dialogs get bumped z-index.
- Tests: `node scripts/test_prompt_presets.mjs` extended (prefill, validation-no-fetch, Save & Use applies node value, group headers, count, search filter, empty state) — passes; `node --check` passes; 10 Python store/API tests pass (`scripts/test_prompt_presets.py`).

## Character Prompt Input Box (September 21, 2026)
- `ApexCharacterPrompt` now exposes `input_text` (empty multiline STRING) and `combine_prompts(input_text="")` merges that text **ahead** of the 12 preset categories, so the user's own words are the first tokens the text encoder sees. It supports its own `[option a, option b]` brackets, seeded with the plain seed (offset 0 vs the presets' 1-12), and stays seed-deterministic. Slots 1-12 never receive it.
- The widget is appended **last** in `INPUT_TYPES["required"]` deliberately: ComfyUI maps saved `widgets_values` positionally, so inserting it earlier would silently shift the seed/control/preset values of existing workflows (`Character Sheet v2/v3.json`).
- Validator grew 96 → 105 checks (widget order and spec, leading position, no leakage into the category outputs, empty-box byte-identical regression, bracket determinism, input-only prompt). All 105 character checks and the 10 prompt-preset regressions pass.
- The running ComfyUI at 127.0.0.1:8188 still reports the old 13-input schema because Python modules load at boot; a restart is required before the box appears in the UI (live UI verification pending).

## Learnings: "everything comes out 3D renders" (September 21, 2026)
Diagnosed against the user's `Character Sheet v3.json` (Apex Character Prompt + Apex Prompt → StringConcatenate → Qwen-Image-Edit 2511 / Krea 2 subgraph, `ConditioningZeroOut` negatives):
- The **`Photorealistic` style preset is not photographic language**: "Photorealistic, hyperrealistic, ultra-detailed, realistic textures, **physically based rendering, ray-traced lighting**, photorealistic rendering, film-quality realism, 8K resolution, ultra sharp focus, masterpiece, best quality." PBR / ray-tracing wording is 3D-CGI vocabulary in the training data and pulls toward Blender/Octane-style renders.
- The same vocabulary appears elsewhere in the library: Environment `Subway Fashion Portrait` ("HDR, global illumination, volumetric lighting, ray tracing"), Lighting `HDR Balanced` / `Ring Light Beauty` ("realistic skin rendering", "smooth skin rendering"), Style `Fashion Studio Portrait` ("global illumination, photorealistic rendering").
- The character library supplies the doll-like half of the look (porcelain / flawless / airbrushed complexion, idealized geometry) and the pipeline has **no negative prompt**, so nothing counteracts "3d render, cgi, doll".
- `Random` style is a coin flip away from non-photographic: 73.7% of the weighted Style pool is illustration/CG/artistic, 5.5% explicitly 3D/CG.
- Workflow wiring note: the character prompt feeds `StringConcatenate.delimiter` (not `string_b`). Output is still correct because `delimiter.join((a, b))` with an empty `string_b`, but it is accidental and fragile.

## Character Presets Added (September 21, 2026)
- Added three presets from a user-supplied cinematic EDM thumbnail character: **Long Silver Blonde Wispy Bangs** (`Apex Character Hair`, weight 1.1), **White Wireless Headphones** (`Apex Character Headwear`, weight 1.0), **Oversized Pale Blue Hoodie** (`Apex Character Top`, weight 1.1). Each was appended at the end of its category (matching the Square Eyes precedent) and carries its category's dominant random weight.
- Trait check against the existing library — deliberately **not** added because equivalents already existed: gender **Female**; age **Early Twenties 22-25** (and **Young Adult 18-21**); eye color **Gray-Blue** ("gray-blue eyes, soft silvery-blue irises... gentle cool mist tone"), which is effectively identical to the described luminous blue-gray eyes; skin tone **Warm Rosy** plus **Fair Cool** (fair complexion with a natural pink flush/bloom); face expression and glossy lips, already covered by **Girl Next Door** (subtle glossy pink lips), **Nordic Cool** (calm cool expression), and **Ethereal Elf** (serene). Ethnicity was not specified by the source text, so none was guessed; "one hand resting near her chin" is a pose, not a hand accessory.
- Library total 218 → 221 (hair 28→29, headwear 16→17, top 30→31). `character_presets.json` regenerated with `scripts/generate_character_presets.py` and confirmed in sync (`--check`); the validator's asserted total was updated to 221. Validator passes (96 PASS / 0 FAIL) and all 10 prompt-preset regressions pass.
- Note: adding presets changes the weighted Random pool for hair, headwear, and top, so existing seeds using `Random` in those categories may now select a different preset. Named selection is unaffected.

## Character Preset Added (September 20, 2026)
- Added the **Square Eyes** face preset (`Apex Character Face`) with the user's prompt text stored verbatim (1078 chars; verified character-for-character), tags `square eyes/horizontal eyes/oval face/soft/balanced`, and weight 1.2 matching the dominant face-preset weight.
- Face category is now 18 presets; library total 218. `character_presets.json` regenerated via `scripts/generate_character_presets.py` and confirmed in sync (`--check`).
- The validator's library total was updated to 218 (it asserts an exact count by design).
- Note: adding a face preset changes the weighted Random pool, so existing seeds using `face_preset = Random` may now select a different face. Named selection is unaffected.

## Prompt Preset Update (September 20, 2026)
- Added `apex_prompt_store.py`: bundled JSON remains unchanged; Python-only names supplemented at read time. User data resides under the configured ComfyUI user directory in `apex_artist/prompt_presets.json`.
- Library scope is installation-shared, explicitly labeled; not private per-profile. One ComfyUI process is supported (process-local lock).
- Save/Manage buttons, category text editor, factory-copy/user CRUD, filtering, import/export, revision conflicts, atomic replacement and error retention implemented.
- Backend INPUT_TYPES/execution/API share the store; execution reloads, IS_CHANGED hashes the revision; websocket notifications refresh open node dropdowns.
- Legacy factory write routes return 403; legacy reads remain compatible. Random preserves the original JSON pool/order/weights.
- Validated: 10 Python preset tests (including aiohttp routes), Node.js frontend harness, 7 existing core tests. Full browser/ComfyUI integration still requires a restart and manual smoke test.

## Recent Changes (Sept 19, 2026)
- **Shared utilities optimization**: Converted Gaussian blur to separable convolution (tested against dense reference), added float64 kernel support, preserved existing sigma/padding behavior
- **Device/dtype safety**: Masks now match image device/dtype before blending operations
- **Security hardening**: LoRA path validation uses resolved component checks, not string prefixes; validates final thumbnail paths
- **Import fixes**: LoRA loader explicitly imports comfy.sd; lens preset API reads static defaults without instantiating nodes
- **Testing**: 7 core unittest methods passed (29.973s) covering blur/sharpen/blend modes, Gaussian accuracy at 4 radii/2 sigmas, device handling, path boundaries
- **Documentation**: Consolidated 13 redundant root-level reports into Memory Bank

## Active Issues
1. **HDRI viewer**: Socket flow repaired and regression-tested; real browser smoke test pending
2. **Preset follow-up**: Manual live-browser smoke test pending; separate character preset API was not changed
3. **Blocking I/O**: HDRI decode/render and LoRA thumbnail scans block async handlers
4. **Character node fixed (September 20)**: Registered class/display name and API in __init__.py. Removed inheritance of prompt-store state; character loading, random selection and IS_CHANGED are independent. Character validator now covers package exports and passes; all 10 prompt regressions pass.
5. **Registry metadata**: May not match actual registration; needs review before publish

## Next Steps
1. Smoke-test HDRI socket preview after restart/browser refresh
2. Smoke-test Save/Manage after restart; apply equivalent persistence fixes to character presets as a separate follow-up
3. Move expensive API operations off event loop with memory bounds
4. Reconcile registry metadata with source before release

## Important Patterns & Preferences
- Source code and reproducible tests are authoritative over historical completion reports
- Don't claim performance improvements without benchmarks
- Preserve user-controlled node sizes; use native ComfyUI UI mechanisms
- Keep findings in Memory Bank topics, not dated completion documents
- Don't discard uncommitted code or source assets during cleanup
