# ComfyUI Apex Artist

Image processing, prompt presets, audio selection and a video timeline editor inside ComfyUI.

## Nodes

| Node | Purpose |
| --- | --- |
| Apex Blur | Nine blur methods, including Gaussian, motion, lens and depth blur |
| Apex Sharpen | Eight sharpening methods |
| Apex Layer Blend | Layer compositing with 25+ blend modes |
| Apex Depth to Normal | Convert depth maps to RGB normal maps |
| Apex HDRI Viewer | Aim a camera into a panorama and output front/back views |
| Apex LoRA Loader | Browse configured LoRA folders with thumbnail previews |
| Apex Prompt | Environment, Lighting, Style, Color and Camera Lens presets |
| Apex Character Prompt | Twelve character categories with separate and combined text outputs |
| Apex JSON Lookup | Read text values from JSON data |
| Apex Audio | Load or connect audio, trim, adjust gain, preview and read metadata |
| Apex Timeline Editor | Edit persistent video/audio tracks and output standard ComfyUI media |

## Installation

Requires **Python 3.10+**, **ComfyUI 0.42.1+**, and the dependencies in `requirements.txt`. Timeline rendering also needs FFmpeg available on PATH. PyTorch, PyAV, Pillow and the native audio/video APIs come from ComfyUI.

Clone this repository into ComfyUI's `custom_nodes` folder:

```sh
git clone https://github.com/ApexArtist/comfyui-apex-artist.git
```

Using the Python environment that runs ComfyUI, install `requirements.txt`. Restart ComfyUI and hard-refresh the browser. Find the nodes under **Apex Artist** in the Add Node menu.

## Prompt presets

**Apex Prompt** combines input text → environment → lighting → style → color → camera lens. It returns the combined prompt and five category texts. Each selector accepts Disabled, Random or a named preset. Random choices are deterministic for the seed.

**Save Preset…** saves text for one category. **Manage Presets…** supports search, copying factory presets, editing user presets and import/export. Factory entries stay read-only; user entries appear as `User: Name`. Saving user entries does not change the seeded factory Random pool. Share a library export with workflows that reference its names.

**Apex Character Prompt** has twelve selectors: gender, age, ethnicity, face, eye color, skin tone, hair, headwear, top, bottom, shoes and hand accessory. Its thirteen outputs contain the combined prompt and individual category texts. Optional input text leads the combined output. **Manage Character Presets…** edits the character library, with import/export and Use controls. Missing named presets raise an error instead of disappearing silently.

Both libraries save atomically beneath ComfyUI's configured user directory:

```text
apex_artist/prompt_presets.json
apex_artist/character_presets.json
```

These libraries are shared by clients of the same server. Revision checks reject stale saves and keep the editor draft. Character API reads return an ETag; writes require it in `If-Match`. One writing ComfyUI process is supported. Export custom libraries before reinstalling or moving installations. Existing bundled character edits seed the library until its first user save; later edits use the user copy.

## Audio

Load/upload a file or connect standard `AUDIO`; a connection takes priority. Drag the waveform handles or enter start and duration in seconds. Duration 0 selects the remaining source. Gain ranges from 0–200%, with 100% unchanged. Preview plays the selection. Outputs are `AUDIO`, selected duration, sample rate, channels and sample count.

Source files remain unchanged. No resampling or normalization is applied. Disable Preview to skip waveform generation and connected-input preview encoding; connected previews become available after execution.

## Timeline editor

The editor is embedded in the node. Resize it for more space. It outputs **VIDEO, IMAGE, AUDIO and FPS**, followed by project metadata. Connect VIDEO to native **Save Video**, or IMAGE/AUDIO/FPS to a video-combine node. IMAGE materializes frames only when connected; video-only exports keep frames on disk. Final saving uses the downstream node's encoding settings.

### Capture and placement

- Each VIDEO input maps to the same numbered video lane: Video 1 → V1, Video 2 → V2. Repeated captures append to that lane.
- `placement_start = -1` appends at each receiving track's end. A non-negative value sets an explicit start. `placement_offset` adds seconds to that computed start for each incoming clip; 0 adds no gap.
- **New Results Only** rejects identical media already captured on the same track. The target defaults to 180 seconds; overflow is retained in the review bin.
- Native loop/math nodes can drive ordinary inputs. Connect a loop's `is_last` to `prepare_outputs` to assemble only its final iteration. Loops retain the editor's persistent project identity.
- **+ Track** exposes its VIDEO socket. Connecting the last socket grows a matching lane/socket, up to sixteen tracks. Disconnecting keeps edits intact. V1 is permanent; other lanes have a small minus button with deletion confirmation and undo support.

### Editing and playback

Drag clips between tracks, trim edges, set numeric positions/source trims, split, duplicate or delete. Undo/redo persists. Higher video tracks cover lower tracks. Gaps show black; enabled audio lanes mix independently of the visible video layer.

Video audio receives linked audio placements. The optional master AUDIO input becomes an editable clip on A1. Disable `capture_clip_audio` when the master should supply the soundtrack. Timing edits affect linked video/audio until unlinked. Audio lanes support mute and gain: drag the thin waveform line from 0–200%, double-click to reset to 100%, or focus it and use Up/Down/Home. Waveform height follows gain.

Project FPS defaults to 24. Scrub the ruler/playhead; Space toggles playback, Left/Right steps frames and Home/End jumps to boundaries while the editor has focus. Text and numeric fields retain their normal keys. **Fit** sits beside zoom. Clip actions are before **Export**. Wheel input scrolls editing panels and reaches canvas zoom over the preview/background.

Video/audio edge handles control fades. Zero duration means full opacity/gain. SNAP stops edits at clip boundaries; disabling SNAP allows overlap and automatic join fades. Preview preloads the next visible clip for hard cuts. Mixed sizes and frame rates are normalized during rendering, leaving linked originals unchanged.

### Storage and export

Projects and captured assets persist under:

```text
<ComfyUI output>/Apex/timelines/<project>/
```

Legacy projects under `user/apex_artist/timelines` are copied on first open; originals remain. **Link clips** and external drag/drop reference original absolute paths without copying. If the browser hides a dropped path, use the local source picker. Audio files can be linked directly to audio lanes.

Missing sources remain red with their edits intact. Right-click to locate one or search a folder, optionally including subfolders. Ambiguous matches stay unresolved. Missing media blocks export until repaired.

**Export** queues the connected save path using saved placements, fades, mute and gain. It does not regenerate source clips or reload the original audio loader. **Clear video cache** removes regenerable MP4 cache files only while the ComfyUI queue is idle. Source media stays intact. Audio/waveform caches have count limits; video caches are cleared explicitly.

## LoRA and HDRI previews

The LoRA browser lists all configured roots and generates 256×256 JPEG thumbnails. Changed source previews regenerate thumbnails; asynchronous results stay matched to the selected model. Duplicate relative names follow ComfyUI's earlier-root precedence. Keep original preview images if you need their full quality.

The HDRI viewer uses source panorama metadata for its interactive preview. Connect IMAGE and execute once for a socket preview; the bounded 8-bit preview approximates the source while final outputs retain tensor dynamic range. Drag to aim, Shift-drag to roll and scroll to change FOV. Unchanged views reuse the rendered frame. OpenCV provides HDR/EXR decoding; panoramas cannot reveal unseen geometry or true parallax.

## Development and release

Version **2.4.0** adds Apex Audio, Timeline Editor and node reliability fixes. See [CHANGELOG.md](CHANGELOG.md) for changes and validation limits, [PUBLISH.md](PUBLISH.md) for release steps, and [system patterns](memory-bank/systemPatterns.md) for architecture.

Run the portable CPU regressions with the ComfyUI Python environment:

```sh
python -m unittest discover -s tests
python scripts/generate_character_presets.py --check
```

Check each `web/*.js` with `node --check`. These checks do not replace a live ComfyUI smoke test or clean-install test. No GPU performance benchmark is claimed.

MIT licensed; see [license.md](license.md). Issues and contributions are welcome on [GitHub](https://github.com/ApexArtist/comfyui-apex-artist/issues).
