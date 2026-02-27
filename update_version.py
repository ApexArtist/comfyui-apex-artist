#!/usr/bin/env python3
"""
Version Update Script for ComfyUI Apex Artist Nodes
Updates version across all required files for consistent publishing
"""

import re
import sys
from pathlib import Path

def update_version(new_version):
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
            "pattern": r'"version": "[^"]*"',
            "replacement": f'"version": "{new_version}"'
        }
    }
    
    print(f"🚀 Updating to version {new_version}")
    
    for filename, config in files_to_update.items():
        filepath = Path(filename)
        
        if not filepath.exists():
            print(f"⚠️  Warning: {filename} not found")
            continue
            
        # Read file content
        content = filepath.read_text(encoding='utf-8')
        
        # Update version
        updated_content = re.sub(config["pattern"], config["replacement"], content)
        
        # Write back
        filepath.write_text(updated_content, encoding='utf-8')
        
        print(f"✅ Updated {filename}")
    
    print(f"""
🎯 Version {new_version} updated in all files!

Next steps:
1. git add .
2. git commit -m "🚀 Version {new_version} - [Your release notes]"
3. git push origin main

This will trigger GitHub Actions to publish to ComfyUI Registry.
""")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_version.py <new_version>")
        print("Example: python update_version.py 1.6.5")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    # Validate semantic version format
    if not re.match(r'^\d+\.\d+\.\d+$', new_version):
        print("❌ Error: Version must be in format X.Y.Z (e.g., 1.6.5)")
        sys.exit(1)
    
    update_version(new_version)