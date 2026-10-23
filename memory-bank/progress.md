# Progress

## Included in 2.4.0

- Eleven nodes: the original nine plus Audio and Timeline Editor.
- Embedded multitrack editing, linked external media, persistent undo/redo, missing-source repair, video/audio fades, gain, thumbnails, scrubbing and standard VIDEO/IMAGE/AUDIO/FPS outputs.
- Audio file/input selection, sample-based trim, gain, preview and metadata.
- Image-filter correctness and dtype fixes; actionable processing/LoRA errors.
- Validated atomic character saves with revision conflicts; multiple LoRA roots and race-safe previews; reusable HDRI preview frames; worker-based heavy API operations.
- Saved export prunes unused input loaders. Explicit video-cache cleanup preserves source media and refuses a busy queue.

## Verified locally

Seventy-one targeted CPU checks, eight portable regressions, isolated API/browser tests, all eleven node schemas, twenty-seed character compatibility, a real five-second CPU export at 24 FPS, and native loops for 6, 25.25 and 60 seconds passed. Loop tests used placeholder frames and exact audio crops. Syntax checks are not live integration tests.

The owner's v3 workflow and media were unchanged by the reliability fixes. No GPU render was run. The owner authorized committing, tagging and pushing 2.4.0 on 2026-10-23; verify current publication status through GitHub and the registry.

## Remaining

Owner smoke testing after manual restart/browser refresh; clean-install and GPU-specific verification; registry activation and installation checks. Previous release details are in CHANGELOG.md, not current registry status claims.
