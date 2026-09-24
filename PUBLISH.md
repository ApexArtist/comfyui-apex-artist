# Publishing Guide for ComfyUI Apex Artist

This document outlines the complete workflow for publishing new versions of the ComfyUI Apex Artist custom nodes package.

## Pre-Publish Checklist

### Current release: 2.3.0 (September 24, 2026)
- Version metadata and release notes prepared; see `CHANGELOG.md`.
- Push to `main` and registry publication authorized by the repository owner on 2026-09-24.
- **Push completed 2026-09-24:** an initial attempt returned `403 Permission denied` because the stored Git Credential Manager credential (`apexartistx`) lacked write access to `ApexArtist/comfyui-apex-artist`. After write access was granted, commit `1c3eaa4` and tag `v2.3.0` pushed successfully, and Actions run #29 (https://github.com/ApexArtist/comfyui-apex-artist/actions/runs/35989797563) finished with `success`.
- Automated pre-publish verification passed (version consistency, character preset store sync, prompt store and node behaviour, frontend syntax). Live browser and clean-install checks remain pending.
- **Important:** the existing GitHub workflow publishes on a push to `main` that changes `pyproject.toml`; the release push is a publishing action, not just a backup.

Before publishing a new version, ensure all of the following are complete:

### Code Quality
- [ ] All new features are fully implemented and tested
- [ ] Code follows project conventions and patterns
- [ ] No debug code, console logs, or temporary hacks remain
- [ ] All TODO comments are addressed or documented
- [ ] Error handling is comprehensive and user-friendly

### Testing
- [ ] Manual testing of all modified nodes in ComfyUI
- [ ] Test workflows with various configurations
- [ ] Verify backward compatibility with existing workflows
- [ ] Check for memory leaks or performance issues
- [ ] Test on clean ComfyUI installation if possible
- [ ] Verify preset store is in sync: `python scripts\generate_character_presets.py --check`
- [ ] Confirm `git status` shows no temp or derived files before staging
- [ ] Syntax check frontend: `node --check web\<filename>.js` for each file

### Documentation
- [ ] README.md is up to date with new features
- [ ] Code comments are clear and accurate
- [ ] API changes are documented
- [ ] Example workflows are included if relevant
- [ ] Memory bank files reflect current state

### Version Files
- [ ] All version numbers are consistent across files
- [ ] Release notes prepared
- [ ] comfyui.yaml metadata is accurate
- [ ] pyproject.toml metadata is current
- [ ] __init__.py NODE_VERSION matches

---

## Version Update Process

### 1. Determine Version Increment

Follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **PATCH** (0.0.x): Bug fixes, minor tweaks, no breaking changes
- **MINOR** (0.x.0): New features, backward compatible
- **MAJOR** (x.0.0): Breaking changes, major overhaul

### 2. Update Version Numbers Manually

This project does not currently include an automated version-update script. Update version numbers manually in these files:

- `__init__.py` — `NODE_VERSION = "x.y.z"`
- `comfyui.yaml` — `version: "x.y.z"`
- `pyproject.toml` — `version = "x.y.z"`
- `manifest.json` and `custom_nodes.json` — package `version` fields (not `manifest_version`)

### 3. Verify Version Consistency

After updating, verify that version numbers match across:
- `__init__.py` (NODE_VERSION)
- `pyproject.toml` (version field)
- `comfyui.yaml` (version field)
- `manifest.json` and `custom_nodes.json` (package version fields)

---

## Git Workflow

### 1. Stage Changes

Review and stage all modified files:

```bash
# Review changes
git status
git diff

# Stage version-related files
git add __init__.py manifest.json pyproject.toml comfyui.yaml

# Stage all other changes
git add .
```

### 2. Commit Changes

Use a clear, descriptive commit message:

```bash
# Version bump commit
git commit -m "chore: bump version to v1.2.3"

# Or feature/fix commit
git commit -m "feat: add new lens simulation node"
git commit -m "fix: resolve LoRA stack memory leak"
```

**Commit Message Conventions:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `chore:` Maintenance tasks (version bumps, dependency updates)
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Testing changes

### 3. Create Git Tag

Tag the release with the version number:

```bash
# Create annotated tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# Verify tag
git tag -l
git show v1.2.3
```

### 4. Push to Remote

Push both commits and tags:

```bash
# Push commits
git push origin main

# Push tags
git push origin --tags

# Or push both at once
git push origin main --tags
```

---

## Post-Push Verification

### 1. Verify GitHub

- [ ] Check that commits appear on GitHub
- [ ] Verify that tags are visible in the Releases section
- [ ] Confirm GitHub Actions workflows complete successfully (if configured)

### 2. ComfyUI Registry

If publishing to ComfyUI Registry:

- [ ] Verify package appears with correct version
- [ ] Test installation via ComfyUI Manager
- [ ] Check that metadata displays correctly
- [ ] Verify download count starts tracking

### 3. User Testing

- [ ] Install the package in a clean ComfyUI instance
- [ ] Verify all nodes load correctly
- [ ] Test basic functionality of key nodes
- [ ] Check for any import errors or missing dependencies

---

## Troubleshooting

### Version Mismatch Errors

**Problem:** Version numbers differ across files after update.

**Solution:**
```bash
# Inspect the five version files listed above and manually align them.
# There is no update_version.py script in this repository.
```

### Git Push Rejected

**Problem:** `git push` fails with "Updates were rejected".

**Solution:**
```bash
# Pull latest changes first
git pull origin main --rebase

# Resolve any conflicts
# Then push again
git push origin main --tags
```

### Tag Already Exists

**Problem:** Tag already exists locally or remotely.

**Solution:**
```bash
# Delete local tag
git tag -d v1.2.3

# Delete remote tag
git push origin :refs/tags/v1.2.3

# Create tag again with correct commit
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin v1.2.3
```

### ComfyUI Registry Not Updating

**Problem:** New version doesn't appear in ComfyUI Manager.

**Solution:**
- Check that `comfyui.yaml` or `manifest.json` has correct version
- Ensure the repository is properly registered with ComfyUI Registry
- Wait 5-10 minutes for registry to refresh
- Clear ComfyUI Manager cache if needed

### Missing Dependencies

**Problem:** Users report import errors after installation.

**Solution:**
- Verify `requirements.txt` includes all dependencies
- Test installation in clean Python environment:
  ```bash
  pip install -r requirements.txt
  ```
- Update documentation with manual installation steps if needed

---

## Quick Reference

### Complete Publishing Command Sequence

```bash
# 1. Manually update the five version files and CHANGELOG.md

# 2. Review changes
git status
git diff

# 3. Stage and commit
git add .
git commit -m "chore: bump version to v1.2.3"

# 4. Create tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# 5. Push everything
git push origin main --tags
```

### Local preparation only

Stop after the commit when a push has not been authorized. Leave the release tag
and publication until the remaining checks pass and publication is requested.

---

## Release Notes Template

When creating release notes or CHANGELOG entries:

```markdown
## [1.2.3] - 2024-01-15

### Added
- New feature descriptions

### Changed
- Modified behaviors or improvements

### Fixed
- Bug fixes and corrections

### Deprecated
- Features marked for future removal

### Removed
- Removed features

### Security
- Security fixes
```

---

## Additional Resources

- [Semantic Versioning Specification](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [ComfyUI Custom Nodes Documentation](https://docs.comfy.org/custom-nodes)
- [Git Tagging Documentation](https://git-scm.com/book/en/v2/Git-Basics-Tagging)

---

**Last Updated:** 2026-09-24
