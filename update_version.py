#!F:\AI\ComfyUI Sandbox\ComfyUI\.venv\Scripts\python.exe
"""
Version Update Script for ComfyUI Apex Artist Nodes
Updates version across all required files for consistent publishing
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Tuple

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def colored(text: str, color: str) -> str:
    """Return colored text for terminal output"""
    return f"{color}{text}{Colors.RESET}"

def get_current_version() -> Optional[str]:
    """Read current version from pyproject.toml"""
    try:
        content = Path("pyproject.toml").read_text(encoding='utf-8')
        match = re.search(r'version = "([^"]*)"', content)
        return match.group(1) if match else None
    except Exception as e:
        print(colored(f"⚠️  Could not read current version: {e}", Colors.YELLOW))
        return None

def parse_version(version: str) -> Tuple[int, int, int]:
    """Parse semantic version string into tuple"""
    parts = version.split('.')
    return (int(parts[0]), int(parts[1]), int(parts[2]))

def increment_version(current: str, bump_type: str) -> str:
    """Increment version based on bump type (major, minor, patch)"""
    major, minor, patch = parse_version(current)
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    
    return current

def check_git_status() -> Tuple[bool, str]:
    """Check if git working tree is clean"""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        is_clean = len(result.stdout.strip()) == 0
        return is_clean, result.stdout
    except Exception:
        return True, ""  # Assume clean if git not available

def get_file_version(filepath: Path, pattern: str) -> Optional[str]:
    """Extract version from file using pattern"""
    try:
        content = filepath.read_text(encoding='utf-8')
        match = re.search(pattern, content)
        if match:
            # Extract version from the match
            version_match = re.search(r'(\d+\.\d+\.\d+)', match.group(0))
            return version_match.group(1) if version_match else None
    except Exception:
        pass
    return None

def update_version(new_version: str, dry_run: bool = False, auto_commit: bool = False, 
                   create_tag: bool = False, commit_message: Optional[str] = None):
    """Update version in all required files"""
    
    # Define all files that need version updates
    files_to_update = {
        "pyproject.toml": {
            "pattern": r'version = "[^"]*"',
            "replacement": f'version = "{new_version}"'
        },
        "custom_nodes.json": {
            "pattern": r'"version": "[^"]*"',
            "replacement": f'"version": "{new_version}"'
        },
        "comfyui.yaml": {
            "pattern": r'version: "[^"]*"',
            "replacement": f'version: "{new_version}"'
        },
        "manifest.json": {
            # More specific pattern to avoid matching "manifest_version"
            "pattern": r'(?<!"manifest_)"version": "[^"]*"',
            "replacement": f'"version": "{new_version}"'
        }
    }
    
    # Get current version
    current_version = get_current_version()
    
    # Display header
    print(colored("\n" + "="*60, Colors.CYAN))
    print(colored("🚀 ComfyUI Apex Artist - Version Update", Colors.BOLD))
    print(colored("="*60 + "\n", Colors.CYAN))
    
    if current_version:
        print(colored(f"📦 Current version: {current_version}", Colors.BLUE))
        print(colored(f"📦 New version:     {new_version}", Colors.GREEN))
        
        # Validate version progression
        try:
            current_tuple = parse_version(current_version)
            new_tuple = parse_version(new_version)
            
            if new_tuple <= current_tuple:
                print(colored(f"\n⚠️  Warning: New version {new_version} is not greater than current version {current_version}", Colors.YELLOW))
                if not dry_run:
                    response = input(colored("Continue anyway? (y/N): ", Colors.YELLOW))
                    if response.lower() != 'y':
                        print(colored("❌ Aborted", Colors.RED))
                        return
        except Exception as e:
            print(colored(f"⚠️  Could not validate version order: {e}", Colors.YELLOW))
    else:
        print(colored(f"📦 New version: {new_version}", Colors.GREEN))
    
    # Check git status
    is_clean, git_status = check_git_status()
    if not is_clean and not dry_run:
        print(colored(f"\n⚠️  Warning: You have uncommitted changes:", Colors.YELLOW))
        print(colored(git_status, Colors.YELLOW))
        response = input(colored("Continue anyway? (y/N): ", Colors.YELLOW))
        if response.lower() != 'y':
            print(colored("❌ Aborted", Colors.RED))
            return
    
    if dry_run:
        print(colored(f"\n🔍 DRY RUN MODE - No files will be modified\n", Colors.YELLOW))
    else:
        print()
    
    # Track results
    updated_files = []
    failed_files = []
    version_mismatches = []
    
    # Update each file
    for filename, config in files_to_update.items():
        filepath = Path(filename)
        
        if not filepath.exists():
            print(colored(f"⚠️  {filename}: Not found", Colors.YELLOW))
            failed_files.append(filename)
            continue
        
        # Read file content
        content = filepath.read_text(encoding='utf-8')
        
        # Get current version in this file
        old_version = get_file_version(filepath, config["pattern"])
        
        # Check if pattern matches
        if not re.search(config["pattern"], content):
            print(colored(f"❌ {filename}: Pattern did not match", Colors.RED))
            failed_files.append(filename)
            continue
        
        # Update version
        updated_content = re.sub(config["pattern"], config["replacement"], content)
        
        if dry_run:
            # Show what would change
            print(colored(f"📄 {filename}:", Colors.CYAN))
            if old_version:
                print(colored(f"   {old_version} → {new_version}", Colors.BLUE))
            else:
                print(colored(f"   Would update to {new_version}", Colors.BLUE))
        else:
            # Write back
            filepath.write_text(updated_content, encoding='utf-8')
            print(colored(f"✅ {filename}:", Colors.GREEN))
            if old_version:
                print(colored(f"   {old_version} → {new_version}", Colors.BLUE))
            else:
                print(colored(f"   Updated to {new_version}", Colors.BLUE))
            updated_files.append(filename)
        
        # Track version mismatches
        if old_version and old_version != current_version and current_version:
            version_mismatches.append((filename, old_version))
    
    # Verification section
    if not dry_run and updated_files:
        print(colored("\n" + "="*60, Colors.CYAN))
        print(colored("🔍 Verification", Colors.BOLD))
        print(colored("="*60, Colors.CYAN))
        
        # Verify all files have the same version
        all_consistent = True
        for filename in updated_files:
            filepath = Path(filename)
            config = files_to_update[filename]
            final_version = get_file_version(filepath, config["pattern"])
            
            if final_version == new_version:
                print(colored(f"✅ {filename}: {final_version}", Colors.GREEN))
            else:
                print(colored(f"❌ {filename}: {final_version} (expected {new_version})", Colors.RED))
                all_consistent = False
        
        if all_consistent:
            print(colored("\n✅ All files updated consistently!", Colors.GREEN))
        else:
            print(colored("\n⚠️  Some files have version mismatches!", Colors.YELLOW))
    
    # Summary
    print(colored("\n" + "="*60, Colors.CYAN))
    print(colored("📊 Summary", Colors.BOLD))
    print(colored("="*60, Colors.CYAN))
    
    if dry_run:
        print(colored(f"Would update {len(files_to_update)} files", Colors.BLUE))
    else:
        print(colored(f"✅ Updated: {len(updated_files)} files", Colors.GREEN))
        if failed_files:
            print(colored(f"❌ Failed: {len(failed_files)} files", Colors.RED))
            for f in failed_files:
                print(colored(f"   - {f}", Colors.RED))
        
        if version_mismatches:
            print(colored(f"\n⚠️  Version mismatches before update:", Colors.YELLOW))
            for filename, old_ver in version_mismatches:
                print(colored(f"   - {filename}: {old_ver} (expected {current_version})", Colors.YELLOW))
    
    # Git operations
    if not dry_run and updated_files and (auto_commit or create_tag):
        print(colored("\n" + "="*60, Colors.CYAN))
        print(colored("🔧 Git Operations", Colors.BOLD))
        print(colored("="*60, Colors.CYAN))
        
        if auto_commit:
            try:
                # Stage files
                subprocess.run(['git', 'add'] + updated_files, check=True)
                print(colored(f"✅ Staged {len(updated_files)} files", Colors.GREEN))
                
                # Commit
                msg = commit_message or f"🚀 Version {new_version}"
                subprocess.run(['git', 'commit', '-m', msg], check=True)
                print(colored(f"✅ Committed: {msg}", Colors.GREEN))
            except subprocess.CalledProcessError as e:
                print(colored(f"❌ Git commit failed: {e}", Colors.RED))
        
        if create_tag:
            try:
                tag_name = f"v{new_version}"
                subprocess.run(['git', 'tag', '-a', tag_name, '-m', f"Release {new_version}"], check=True)
                print(colored(f"✅ Created tag: {tag_name}", Colors.GREEN))
            except subprocess.CalledProcessError as e:
                print(colored(f"❌ Git tag failed: {e}", Colors.RED))
    
    # Next steps
    if not dry_run and updated_files:
        print(colored("\n" + "="*60, Colors.CYAN))
        print(colored("📝 Next Steps", Colors.BOLD))
        print(colored("="*60, Colors.CYAN))
        
        if not auto_commit:
            print(colored("1. git add .", Colors.BLUE))
            print(colored(f'2. git commit -m "🚀 Version {new_version} - [Your release notes]"', Colors.BLUE))
        
        if not create_tag:
            print(colored(f"3. git tag -a v{new_version} -m 'Release {new_version}'", Colors.BLUE))
        
        print(colored(f"{'4' if not auto_commit else '1'}. git push origin main", Colors.BLUE))
        print(colored(f"{'5' if not auto_commit else '2'}. git push origin v{new_version}", Colors.BLUE))
        print(colored("\n💡 This will trigger GitHub Actions to publish to ComfyUI Registry.", Colors.CYAN))
    
    print()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Update version across all ComfyUI Apex Artist project files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 2.0.3                    # Set explicit version
  %(prog)s --patch                  # Increment patch (2.0.2 → 2.0.3)
  %(prog)s --minor                  # Increment minor (2.0.2 → 2.1.0)
  %(prog)s --major                  # Increment major (2.0.2 → 3.0.0)
  %(prog)s --patch --dry-run        # Preview patch increment
  %(prog)s 2.1.0 --commit "New feature"  # Update and commit
  %(prog)s --minor --tag            # Increment minor and create git tag
        """
    )
    
    # Version specification (mutually exclusive)
    version_group = parser.add_mutually_exclusive_group(required=True)
    version_group.add_argument('version', nargs='?', help='Explicit version number (e.g., 2.0.3)')
    version_group.add_argument('--patch', action='store_true', help='Increment patch version')
    version_group.add_argument('--minor', action='store_true', help='Increment minor version')
    version_group.add_argument('--major', action='store_true', help='Increment major version')
    
    # Options
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--commit', metavar='MESSAGE', help='Auto-commit with specified message')
    parser.add_argument('--tag', action='store_true', help='Create git tag for the version')
    
    args = parser.parse_args()
    
    # Determine version
    if args.patch or args.minor or args.major:
        current_version = get_current_version()
        if not current_version:
            print(colored("❌ Error: Could not read current version from pyproject.toml", Colors.RED))
            sys.exit(1)
        
        bump_type = 'patch' if args.patch else ('minor' if args.minor else 'major')
        new_version = increment_version(current_version, bump_type)
    else:
        new_version = args.version
    
    # Validate semantic version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print(colored("❌ Error: Version must be in format X.Y.Z (e.g., 2.0.3)", Colors.RED))
        sys.exit(1)
    
    # Update version
    update_version(
        new_version,
        dry_run=args.dry_run,
        auto_commit=bool(args.commit),
        create_tag=args.tag,
        commit_message=args.commit
    )

if __name__ == "__main__":
    main()
