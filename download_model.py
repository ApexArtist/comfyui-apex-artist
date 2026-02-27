"""
Download Qwen2.5-0.5B-Instruct model to the local models directory.
Run this once to pre-download the model (~500MB) so it's included in the repo.
"""

import os
import sys

def download_model():
    """Download the LLM model to the local models directory."""
    
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_cache = os.path.join(current_dir, "models")
    
    print("="*70)
    print("Apex Auto Prompt - Model Downloader")
    print("="*70)
    print(f"\nModel: Qwen/Qwen2.5-0.5B-Instruct")
    print(f"Size: ~500MB")
    print(f"Destination: {models_cache}")
    print("\n" + "="*70 + "\n")
    
    # Create models directory if missing
    os.makedirs(models_cache, exist_ok=True)

    # If models directory already contains files, skip download
    def models_dir_nonempty(path):
        try:
            for root, dirs, files in os.walk(path):
                # ignore empty directories
                if files:
                    return True
            return False
        except Exception:
            return False

    if models_dir_nonempty(models_cache):
        print("✅ Models directory already contains files. Skipping download.")
        print(f"Existing models path: {models_cache}")
        return 0
    
    # Set HuggingFace cache to local directory
    os.environ["HF_HOME"] = models_cache
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    
    # Prefer huggingface_hub.snapshot_download for artifact-only download
    has_hf_hub = False
    try:
        from huggingface_hub import snapshot_download
        has_hf_hub = True
    except Exception:
        has_hf_hub = False

    try:
        print("Checking for transformers library...")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        print("✅ transformers found\n")
    except Exception:
        print("❌ transformers not found!")
        print("\nPlease install requirements first:")
        print("  pip install -r requirements.txt")
        print("\nOr install manually:")
        print("  pip install transformers>=4.36.0 accelerate>=0.25.0 huggingface-hub")
        return 1
    
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    
    try:
        # If huggingface_hub is available, use snapshot_download to only fetch artifacts
        if has_hf_hub:
            print("Downloading model snapshot via huggingface_hub.snapshot_download (artifacts only)...")
            # snapshot_download will place files into the HF cache under models_cache
            snapshot_path = snapshot_download(repo_id=model_name, cache_dir=models_cache, allow_regex=None)
            print("✅ Snapshot download complete\n")
            print("="*70)
            print("✅ SUCCESS! Model artifacts downloaded")
            print("="*70)
            print(f"Model artifacts available inside HuggingFace cache at: {models_cache}")
            print("\nImportant: It's recommended NOT to commit large model files into git. Use Git LFS or leave models out of the repository.")
            return 0
        else:
            # Fallback: use transformers to download tokenizer + model (this will instantiate)
            print(f"Downloading tokenizer from HuggingFace (fallback)...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                trust_remote_code=True,
                cache_dir=models_cache
            )
            print("✅ Tokenizer downloaded\n")
            
            print(f"Downloading model (~500MB, this may take a few minutes)...")
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                trust_remote_code=True,
                cache_dir=models_cache,
                low_cpu_mem_usage=True
            )
            print("✅ Model downloaded\n")
            print("="*70)
            print("✅ SUCCESS! Model artifacts downloaded (via transformers)")
            print("="*70)
            print(f"Model artifacts available at: {models_cache}")
            print("\nImportant: It's recommended NOT to commit large model files into git. Use Git LFS or leave models out of the repository.")
            return 0

    except Exception as e:
        import traceback
        print(f"\n❌ ERROR: Failed to download model")
        print("Traceback:")
        traceback.print_exc()
        print(f"\nTroubleshooting:")
        print(f"  1. Check internet connection")
        print(f"  2. Ensure you have ~500MB free disk space")
        print(f"  3. Try running again (downloads can resume)")
        print(f"  4. If the model requires authentication, set HUGGINGFACE_HUB_TOKEN env var")
        return 1

if __name__ == "__main__":
    sys.exit(download_model())
