# System patterns

## Registration and boundaries

`__init__.py` exposes NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS and WEB_DIRECTORY. Keep V3 nodes in the existing mapping alongside legacy nodes; do not add an exclusive root comfy_entrypoint. APIs register with PromptServer; frontend files enhance existing nodes. Preserve hooks, saved widget order and stable socket indices.

## Image processing

IMAGE is batch × height × width × channels; MASK is batch × height × width. Shared utilities provide separable Gaussian blur, masks and color conversions. Masks/kernels follow image device and compute dtype. Half-precision filters compute in float32 and restore input dtype. Invalid processing raises a clear node error; avoid silently returning original inputs. Use local RNGs rather than resetting global seeds.

## Presets

`apex_prompt_store.py` owns validation, revision checks, process-local locking and atomic same-directory replacement. Both libraries live under the configured user root in `apex_artist/`; the bundled JSON stays untouched by UI saves. Multiple server processes writing one library are unsupported.

Apex Prompt adds `User: ` names without altering the factory Random pool. Its combined order is input → environment → lighting → style → color → camera lens. Outputs retain their original positions, with color_text last. Character has twelve categories and thirteen outputs; input_text is appended in the widget schema but leads the combined text. Character user storage contains a complete library and keeps ordinary names. Missing selected presets fail explicitly. Its API uses ETag/If-Match; frontend save conflicts retain the draft.

## LoRA and HDRI

LoRA APIs validate resolved paths within configured roots. Duplicate relative filenames follow core first-root precedence. Thumbnail generation uses 256×256 JPEGs, regenerates when source previews change and runs outside the event loop. Request tokens prevent stale folder/preview results. Native node.imgs displays previews without forcing node size.

HDRI backend reprojection uses grid_sample, forward −Z/up +Y and R=Ry@Rx@Rz. Equirectangular longitude is atan2(x,−z), latitude asin(y). `ui.hdri_source` is the bounded source panorama; hdri_source_scale restores its HDR range. `ui.images` contains projected outputs and must never be treated as the panorama. Per-node load tokens and render keys prevent stale loads/repeated frames; removal clears owned state. HTTP decode/render runs in a worker.

## Timeline and audio

Project JSON, captured assets and render_cache live beneath `<output>/Apex/timelines`. Legacy user-folder projects are copied on first open without deleting originals. Per-project locks, revisions and atomic replacement protect edits. Assets and placements are separate; placements hold track, start, source-in, duration, gain and fades.

VIDEO socket suffixes map to stable V lanes. Disconnecting never deletes edits. Autogrow supports up to sixteen tracks; V1 remains. `placement_start=-1` appends per receiving track; placement_offset adds seconds to each computed start. Capture deduplicates identical media on the same track in New Results Only mode. External media is linked by original path; captured/generated assets are persisted.

Higher video lanes cover lower lanes; audio lanes mix independently. Linked video/audio placements share timing until unlinked. Zero fades mean full opacity/gain. SNAP rejects overlap; disabling it permits automatic join fades. Missing clips retain edits and block export until repaired.

Native file-backed VIDEO avoids materializing full frame batches unless IMAGE is requested. Render normalizes mixed sizes/rates; downstream nodes own final saving. Export uses Read Saved and prunes unused generation/placement/audio-loader links. Audio/waveform caches have count limits. Clear video cache removes regenerable MP4s only with an idle queue, retaining originals.

## Frontend lifecycle

Keep UI state on the owning node, clean up listeners/timers/media on removal and guard asynchronous results. Avoid unrelated canvas resize/scroll changes during edits. Preview retains active layers plus the next clip. Only editor-focused keyboard events control playback; numeric fields keep native behavior. Source and tests take precedence over historical completion notes.
