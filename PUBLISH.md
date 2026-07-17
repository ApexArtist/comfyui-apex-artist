# Publishing Guide for ComfyUI Apex Artist

This document outlines the complete workflow for publishing new versions of the ComfyUI Apex Artist custom nodes package.

## Pre-Publish Checklist

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

### Documentation
- [ ] README.md is up to date with new features
- [ ] Code comments are clear and accurate
- [ ] API changes are documented
- [ ] Example workflows are included if relevant
- [ ] Memory bank files reflect current state

### Version Files
- [ ] All version numbers are consistent across files
- [ ] CHANGELOG or release notes prepared
- [ ] manifest.json is accurate
- [ ] pyproject.toml metadata is current
- [ ] package.json (if applicable) is updated

---

## Version Update Process

### 1. Determine Version Increment

Follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **PATCH** (0.0.x): Bug fixes, minor tweaks, no breaking changes
- **MINOR** (0.x.0): New features, backward compatible
- **MAJOR** (x.0.0): Breaking changes, major overhaul

### 2. Run Version Update Script

The `update_version.py` script updates version numbers across all project files:

```bash
# Basic usage - manually enter version
python update_version.py

# Auto-increment patch version (e.g., 1.2.3 → 1.2.4)
python update_version.py --patch

# Auto-increment minor version (e.g., 1.2.3 → 1.3.0)
python update_version.py --minor

# Auto-increment major version (e.g., 1.2.3 → 2.0.0)
python update_version.py --major

# Preview changes without applying them
python update_version.py --dry-run --patch

# Update version and create git commit + tag
python update_version.py --patch --commit --tag
```

### 3. Verify Version Consistency

After running the script, verify that version numbers are updated in:
- `__init__.py` (NODE_VERSION)
- `manifest.json` (version field)
- `pyproject.toml` (version field)
- `comfyui.yaml` (version field)
- Any other relevant files

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
# Run script again with --dry-run to check
python update_version.py --dry-run

# Or manually edit files to match
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
# 1. Update version (choose one)
python update_version.py --patch
python update_version.py --minor
python update_version.py --major

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

### One-Command Publishing (with script)

```bash
# Update version, commit, tag, and push in one go
python update_version.py --patch --commit --tag
git push origin main --tags
```

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

**Last Updated:** 2026-07-18
