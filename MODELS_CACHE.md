# Model Cache Information

## 📁 Local Model Storage

The **🌟 Apex Stable Normal** node automatically downloads and caches models in the local `models/` directory within this node's folder:

```
comfyui-apex-artist/
├── models/                          # Local model cache
│   ├── torch_hub/                   # PyTorch Hub models
│   │   └── hub/
│   │       └── Stable-X_StableNormal_main/  # ~50MB
│   └── huggingface/                 # HuggingFace models  
│       └── hub/
│           └── models--Stable-X--stable-normal-v0-1/  # ~1-2GB
```

## 📊 Model Sizes

- **StableNormal Regular**: ~2.3GB
- **StableNormal Turbo**: ~1.7GB
- **Repository Code**: ~50MB

## 🔧 Benefits of Local Caching

1. **Self-contained**: All models stored within the node directory
2. **Portable**: Easy to backup/restore with the node
3. **Organized**: No system-wide cache pollution
4. **Manageable**: Clear view of disk usage per node

## 💾 Managing Cache

### View Cache Information
Enable "show_cache_info" in the node to see:
- Cache location
- Total disk usage
- Which models are downloaded

### Clear Cache (if needed)
Delete the `models/` directory to clear all cached models:
```powershell
Remove-Item "models" -Recurse -Force
```

## 🚀 First Run
On first use, the node will:
1. Create the `models/` directory structure
2. Download the StableNormal repository (~50MB)
3. Download model weights when needed (~1-2GB)
4. Cache everything locally for future use

The download only happens once - subsequent uses are instant!