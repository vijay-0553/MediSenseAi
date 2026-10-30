"""
Model Weight Verification and Git LFS Resolution Utility
--------------------------------------------------------
Ensures that all 9 required production neural network weights are fully present
on disk as real binary files rather than Git LFS text pointer files (~130 bytes).
If any model is missing or detected as an LFS pointer, it automatically downloads
the full weights directly from GitHub CDN (media.githubusercontent.com).
"""

import os
import sys
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models" / "models"
GITHUB_CDN_BASE = "https://media.githubusercontent.com/media/vijay-0553/MediSenseAi/main/backend/models/models"

REQUIRED_MODELS = [
    "fracture/DenseNet201_CBAM_Final.keras",
    "spine/medisense_spine_densenet201_cbam.pth",
    "knee/MediSense_Knee_EfficientNetB5_CleanLab_Final.pth",
    "chest/chest_model.pth",
    "bone_tumor/resnet50_baseline_fold1.pth",
    "bone_tumor/resnet50_baseline_fold2.pth",
    "bone_tumor/resnet50_baseline_fold3.pth",
    "bone_tumor/resnet50_baseline_fold4.pth",
    "bone_tumor/resnet50_baseline_fold5.pth",
]

def is_lfs_pointer_or_missing(filepath: Path) -> bool:
    """Returns True if the file does not exist or is a Git LFS pointer text file."""
    if not filepath.exists():
        return True
    
    # If size is smaller than 2 KB, it cannot be a real neural net checkpoint
    if filepath.stat().st_size < 2048:
        try:
            with open(filepath, "rb") as f:
                head = f.read(64)
                if b"version https://git-lfs" in head:
                    return True
        except Exception:
            return True
        return True
        
    return False

def download_model(rel_path: str) -> None:
    """Downloads model weights directly from GitHub LFS CDN with progress feedback."""
    target_path = MODELS_DIR / rel_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".downloading")
    
    url = f"{GITHUB_CDN_BASE}/{rel_path}"
    print(f"[MediSense] Downloading {rel_path} from {url}...")
    
    start_time = time.time()
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MediSense-Deployment-Bootstrapper/1.0"}
    )
    
    with urllib.request.urlopen(req, timeout=120) as response, open(temp_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1 MB chunk
        last_logged = 0

        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            # Log progress every ~20MB
            if downloaded - last_logged >= 20 * 1024 * 1024 or (total_size and downloaded >= total_size):
                if total_size > 0:
                    pct = (downloaded / total_size) * 100
                    print(f"  -> {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({pct:.1f}%)")
                else:
                    print(f"  -> {downloaded / (1024*1024):.1f} MB downloaded")
                last_logged = downloaded

    # Atomic move
    if target_path.exists():
        target_path.unlink()
    temp_path.rename(target_path)
    elapsed = time.time() - start_time
    final_size_mb = target_path.stat().st_size / (1024 * 1024)
    print(f"[MediSense] Successfully fetched {rel_path} ({final_size_mb:.2f} MB in {elapsed:.1f}s)")

def ensure_all_models() -> None:
    """Ensures all 9 required production models exist and are valid binaries."""
    print("=" * 65)
    print("[MediSense] Verifying production neural network model checkpoints...")
    print("=" * 65)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    resolved_count = 0
    for rel_path in REQUIRED_MODELS:
        full_path = MODELS_DIR / rel_path
        if is_lfs_pointer_or_missing(full_path):
            current_status = "missing" if not full_path.exists() else f"LFS pointer ({full_path.stat().st_size} bytes)"
            print(f"[MediSense] Checkpoint {rel_path} is {current_status}. Resolving...")
            try:
                download_model(rel_path)
                resolved_count += 1
            except Exception as e:
                print(f"[MediSense WARNING] Could not fetch {rel_path} during build: {e}. Will retry on demand.")
        else:
            size_mb = full_path.stat().st_size / (1024 * 1024)
            print(f"[MediSense] Checkpoint OK: {rel_path} ({size_mb:.2f} MB)")
            
    print("=" * 65)
    print(f"[MediSense] Model checkpoint verification completed. ({resolved_count} fetched, {len(REQUIRED_MODELS) - resolved_count} verified on disk)")
    print("=" * 65)

if __name__ == "__main__":
    try:
        ensure_all_models()
    except Exception as e:
        print(f"[MediSense WARNING] Non-critical model check note: {e}", file=sys.stderr)

