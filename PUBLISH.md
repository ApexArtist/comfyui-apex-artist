# Publishing Apex Artist

## Release 2.5.0

**2.5.0 — 2026-10-23.** The owner authorized committing, tagging and pushing this release. See CHANGELOG.md for changes and validation limits. Confirm publication through the GitHub Action and registry; a pushed tag alone does not establish activation.

A push to `main` that changes `pyproject.toml` triggers `.github/workflows/publish_action.yml` and publishes to the ComfyUI registry. Treat the release push as publication and obtain owner approval for each release.

## Before committing

- Review `git status`, `git diff` and untracked runtime files. Include all Audio/Timeline Python and frontend modules, the portable regression test and release documentation.
- Exclude Python/test caches, generated previews, temporary media, local credentials and build output. Preserve bundled `lens/` and `lens_previews/` assets. Never delete project media as repository cleanup.
- Run `python -m unittest discover -s tests` and `python scripts/generate_character_presets.py --check` with the ComfyUI environment. Parse Python, JSON and TOML files and run `node --check` for each frontend module.
- Confirm all twelve registered nodes are described in metadata. Align the package version in `__init__.py`, `pyproject.toml`, `comfyui.yaml`, `manifest.json` and `custom_nodes.json`; do not change `manifest_version`.
- Review README, CHANGELOG, dependencies and minimum versions. Document any API changes and checks that remain unperformed.
- Restart ComfyUI from the owner's CMD window and hard-refresh the browser. Smoke-test Audio trim/preview, Timeline capture/playback/export, preset saving, LoRA selection and HDRI preview. A clean installation and GPU-specific checks remain separate from CPU tests.
- Run `node --test tests/test_timeline_export.mjs` for saved-timeline output selection.
- Run `git diff --check`. Review the explicit staged file list with `git diff --cached --stat`; avoid staging unrelated changes.

## Commit and publish

After approval, commit the reviewed changes with a short, direct message, for example:

```sh
git commit -m "Add timeline cut windows and fix multi-output export"
git tag -a v2.5.0 -m "Release 2.5.0"
git push origin main
git push origin v2.5.0
```

Inspect the current branch and remote state before pushing. Push only the intended release tag. Do not force-push, replace an existing release tag or rebase unrelated work to bypass a rejection; inspect the cause first.

## Verify publication

Check the pushed commit/tag and the registry publishing Action. A successful Action does not establish registry activation: verify the version becomes available, then test installation through ComfyUI Manager. Do not overwrite an existing published version; use a new version for subsequent changes.

Record verified publication results without treating an unconfirmed registry state as active. Keep release history in CHANGELOG rather than repeating run logs across documentation.
