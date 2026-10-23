# Active context

Updated 2026-10-23. The owner authorized committing, tagging and pushing version 2.4.0. The code is installed locally. Verify publication through GitHub Actions and registry activation rather than inferring it from local metadata.

## Current work

- Include existing Audio/Timeline Python and frontend modules in the release; these were previously untracked. Exactly eleven node classes remain registered. The separate Timeline Render node was removed earlier.
- Reliability fixes cover depth/fractional-radius/half-precision processing, dissolve opacity, sharpen brightness, explicit failures, safe character-preset saves, LoRA roots/previews, HDRI caching and saved-timeline export.
- Documentation is consolidated around current behavior. Historical details stay in CHANGELOG/git rather than duplicated incident diaries.
- Preserve the owner's LTX 2.5 Music Video v3 workflow, wiring, prompts, settings and media. Never start, restart, stop or interrupt ComfyUI; the owner manages its CMD window. Wait for its queue before operations that affect production media.

## Validation and limits

CPU, isolated API/browser and native timeline-loop checks passed. The loop checks used CPU placeholder frames, not AI sampling. Twenty character seeds retained identical outputs. The portable regression suite contains eight tests. Live restart/clean-install checks and GPU model behavior remain unverified for release.

Detailed local evidence is outside the repository at `E:\Codex\apex-fixes-2026-10-23`; it is not required by the package. Release-preparation evidence is at `E:\Codex\apex-release-2026-10-23`.

## Open follow-ups

- Release publication is authorized. Pushing changed pyproject.toml to main publishes to the registry; a successful Action still requires checking activation separately.
- Some artistic/noir presets deliberately retain monochrome wording. Changing inline color anchors versus the Apex Color slot remains a separate product decision; do not rewrite presets during cleanup.
- Character shape vocabulary and CGI-style language can affect generated appearance. These are prompt-library choices, not evidence of a storage failure.
