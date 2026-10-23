# Product context

Make image processing, prompt management, LoRA browsing and video/audio editing convenient inside ComfyUI. Favor native widgets, standard media outputs and a flexible graph over workflow-specific helper nodes.

- Keep node sizes under user control and previews responsive.
- Preserve seeded prompt choices and make custom libraries editable and exportable.
- Keep the Timeline editor embedded in its node, with familiar clip editing, gain, fades, scrubbing and keyboard playback controls.
- Let downstream Save Video/combine nodes own final saving settings.
- Preserve linked originals and show missing clips clearly instead of discarding edits.

Libraries are installation-shared; private per-profile stores and whole-node preset saves are not implemented. HDRI previews approximate the source and cannot reveal new geometry. Photographic presets should use photographic language, while artistic styles retain their own vocabulary. GPU timing and full live release readiness require separate verification.
