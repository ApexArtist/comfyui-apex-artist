# Active Context

## Current Focus
Release September 24, 2026: the repository owner authorized committing the entire project, updating all version files, and pushing to main; minor version 2.3.0 was selected for the new Apex Color category and the preset colour fixes. Synchronized five version files and nine-node metadata; added CHANGELOG.md and corrected stale publishing instructions. Core/prompt/HDRI/character regressions and preset synchronization all passed at preparation time (the suite has since been removed — see Repository Cleanup). Browser and clean-install checks remain pending. Legacy diagnostics were excluded from the passing suite and later removed with it (see Repository Cleanup). No release tag or publication during the September 21 preparation; on September 24, 2026 the release was committed as `1c3eaa4`, tagged `v2.3.0`, and pushed to main (an initial push returned 403 from a credential without write access; after that was fixed the push succeeded), and GitHub Actions run #29 "Publish to Comfy registry" completed with `success` and created registry version 2.3.0 (present with status `NodeVersionStatusPending` at first check; 2.1.3 remains latest until activation).

HDRI socket preview repaired September 21, 2026. Backend emits separate `hdri_source` + `hdri_source_scale` UI metadata; source is a bounded first-frame panorama, outputs remain front/back IMAGE batches. Unique temporary preview files prevent overwrites. Back yaw rotates 180 degrees. Frontend uses only source metadata (never projected node.imgs), with per-node tokens/timers, removal cleanup, fisheye/exposure/output-aspect support. Removed sampled IS_CHANGED in favor of native dependency caching. New `scripts/test_hdri_socket.mjs` (11 checks) and `scripts/test_hdri_socket.py` (6 tests) pass. Existing uncommitted height-control harness preserved; it targets absent controls and obsolete UI payload. Browser smoke test pending; restart ComfyUI and refresh browser before use.

Implemented Apex Prompt factory/user preset separation (September 20, 2026); added a free-text input box to the character prompt node (September 21, 2026). Fixed Apex Prompt Save/Manage usability (frontend-only, backend unchanged) on September 21, 2026. Preserving unrelated uncommitted HDRI and character-preset work.

## Repository Cleanup (September 23, 2026)
- Removed derived junk only: `__pycache__/`, `scripts/__pycache__/` (20 bytecode files) and `scripts/_hdri_under_test.mjs` — the latter is a generated copy of `web/apex_hdri_viewer.js` that `test_hdri_viewer_preview.mjs` leaves behind (`.gitignore` line 42 covers it). 363,407 bytes freed; `git status` after removal listed only the intended edits, confirming no tracked content was touched.
- Superseded the same day: the user then asked to delete everything not required for ComfyUI to run the pack, so the three previously preserved diagnostics went out together with the whole test suite — 9 dev-only files removed (`test_project_core.py`, `test_hdri_socket.py/.mjs`, `test_prompt_presets.py/.mjs`, `test_hdri_viewer_preview.mjs`, `test_ground_height_visual.py`, `check_model_options.py`, `validate_character_prompt.py`), 84,342 bytes. Kept `scripts/generate_character_presets.py` because `apex_character_prompt.py` names it as the regeneration path for the shipped `character_presets.json`. No temp/backup/cache files remained to delete (the first pass had already cleared them); README, PUBLISH, CHANGELOG, `.gitignore` and this memory bank no longer instruct running the deleted scripts. Everything removed is git-tracked and recoverable via `git show HEAD:<path>`.
- Preserved because deleting them breaks the package, not cleans it: `lens/` and `lens_previews/` (the lens API serves `lens_previews/<preset name>.jpg` by exact filename and 404s when missing, and nothing regenerates them). The live regression suite was preserved in that first pass, then removed later the same day as dev-only material (previous bullet).
- Full suite re-verified after the first cleanup (see techContext.md for the run): all green, ~10 s total. That was the last full run — the suite was deleted later on September 23, 2026 as material ComfyUI does not need.
- Release metadata note: `pyproject.toml` advertises `Icon` and `Banner` at `main/icon.png` / `main/banner.png`, but neither file exists in the repository.


## Face Presets Leaned Toward a Compact Doll-Oval Look (September 23, 2026)
- Anchor: **Universal Beauty** (weight 1.3) rewritten from "soft oval-to-tapered shape / noticeably slim lower face" to a compact, softly oval structure — balanced facial proportions with a slightly widened mid-face, gently rounded cheeks with soft full cheek volume, a short lower face with a reduced vertical distance from the eyes to the chin, a measured forehead height that keeps the face compact, and a small softly rounded chin. Almond eyes, arched brows, petite nose, full lips, porcelain blush and serene expression retained; "anatomically realistic and natural" added; description and tags updated (`compact oval face`).
- 15 other face presets received light, identity-preserving nudges (American Beauty, K-Idol Soft, Editorial High Fashion, Girl Next Door, Hollywood Classic, Ethereal Elf, Nordic Cool, Mediterranean Warm, East Asian Delicate, Afrocentric Radiance, South Asian Grace, Latina Spark, Gothic Porcelain, Freckled Fresh, Athlete Sun-Kissed): softened `slim / tapered / angular / strong / prominent / sharp / defined jaw` wording, plus fuller rounded cheeks and compact proportions where they fit.
- Deliberately unchanged: **Square Eyes** (user text stored verbatim) and **Mature Elegance** (mature identity already reads soft, no conflicting geometry wording). The **Ethnicity** category was reviewed and left alone — those entries describe heritage structure, not beauty geometry.
- The request's "avoid a long forehead, long mid-face, long jaw, pointed chin, vertically elongated proportions" list was converted into positive geometry: the validator rejects negative markers (`" no "`, `" not "`, `"avoid"`, `"without "`, `"excluding"`) and the library is positive-fragment only because the pipeline has no negative prompt. The literal phrase "doll-like" was likewise kept out of the prompt text for the reason recorded in the September 21 3D-render learnings; it can be added on request.
- Counts unchanged (face 18, total 221; nothing added or removed). `character_presets.json` regenerated with `scripts/generate_character_presets.py` (`--check` in sync); the character validator passes (105 PASS / 0 FAIL) and the 10 prompt-preset tests pass. Pool size is unchanged, but a reworded preset returns different text for a given seed, so `Random` face output can differ from pre-change runs; named selection is unaffected.
- Out of scope for the character node: the 85mm / f1.4 / charcoal-studio / overcast-light / PBR-ray-trace half of the request belongs to the Apex Prompt library. Silk Headscarf (headwear), Flannel Overshirt (top, "worn open over a tee") and Knit Mittens (hand accessory, folded cuffs) already matched the outfit lines.


## Prompt Save/Manage Usability Fix (September 21, 2026)
- Follow-up: moved the shared prompt dialog Close button into a sticky top-right header so Manage/Save remain dismissible while scrolling. Frontend harness checks header placement, sticky CSS, and Close removal for both dialogs; harness and JS syntax check pass. Actual browser scrolling still needs a smoke test after a hard refresh.
- `web/apex_prompt.js` only; no changes to store/API/node Python or preset JSON.
- Save dialog now prefills category/name/text from the node's current selection ("Factory X" -> "X Copy"), validates inline (name/whitespace/reserved/empty prompt/weight) without a server round-trip, shows Name/Prompt counters, adds `Save & Use` (saves then applies `User: X` via existing `usePreset`), focuses Name/Prompt, and renames refresh to `Refresh library (keep my draft)`.
- Manager now groups `Factory/User · Category (n)` headers, shows `Showing X of Y` + empty-state, debounces search (150ms) with match highlight, pages at 100 rows with `Show more`, uses inline delete confirm + `Undo delete`, previews import new/conflict counts, uses dated export filenames, and toasts on Save/Use/Delete/Import/Export.
- Node buttons show `Working…`/disabled state while loading; stacked editor-over-manager dialogs get bumped z-index.
- Tests: `node scripts/test_prompt_presets.mjs` extended (prefill, validation-no-fetch, Save & Use applies node value, group headers, count, search filter, empty state) — passed at the time; `node --check` passed; 10 Python store/API tests passed (`scripts/test_prompt_presets.py`). Both scripts were deleted September 23, 2026 as dev-only material (recoverable from git); `node --check web/*.js` remains the available automated check.

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
6. **Preset black-and-white output (audited and fixed September 24, 2026)**: the runtime `Photorealistic` style preset (`prompt_presets.json:1476-1479`) contained no colour word at all — the Python default at `apex_prompt.py:475` had "true-to-life colors" and the shipped JSON had lost it — and 22.6% of the Style weight / 42.5% of the Lighting weight carried no colour vocabulary. Fix applied: 29 zero-colour Style/Lighting presets gained a colour/palette anchor (mirrored in the 6 matching built-in defaults), `Film Noir Classic` and `Film Noir Shadow` were reworded from outright monochrome demands to colour-preserving noir, and colour coverage is now Style 0/36 and Lighting 0/50. Monochrome-wording risk in a Random draw fell from 8.51% to 3.54%; still open are the two mono presets outside the chosen scope (`Noir Detective Office`, `Lightning Storm Flash`), the character node's 42.02% "silhouette" shape-word share, and the missing colour/negative output in both nodes. Full measurements, seed examples and verification steps are recorded under Known Issues in progress.md.
7. **Apex Color slot (added September 24, 2026)**: Apex Prompt gained a fifth preset category as a dedicated colour-grade slot — 68 bundled standard and industry presets, a `color_preset` dropdown appended last, a sixth `color_text` output appended after `camera_lens_text`, and the colour text placed after the style text in the combined prompt. Verified against the real store and node (legacy 4-category user libraries still load, user saves into the new category succeed, six outputs returned) with both Python files compiling. Restart ComfyUI and hard-refresh the browser to see the dropdown. Still open: the deferred decision on reverting the 27 inline colour anchors from the earlier fix, the character node's 42.02% "silhouette" share, and a live browser smoke test of the new dropdown.

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
