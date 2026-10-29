"""
Experiment Script for Task C: Bone Tumor ROI vs Whole-Image Analysis
Evaluates the 5-fold ResNet-50 ensemble on benign, malignant, and normal samples.
"""
import sys
from pathlib import Path
from PIL import Image
import numpy as np
import torch

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.model_manager import model_manager
from preprocessing.tumor import crop_with_padding, eval_transform
from inference.tumor import predict_tumor

def run_experiment():
    print("=" * 80)
    print("TASK C: BONE TUMOR ROI VS WHOLE-IMAGE EXPERIMENT")
    print("=" * 80)

    model_manager.load_all()
    models = model_manager.models["tumor"]
    classes = ["Normal", "Benign", "Malignant"]

    samples = [
        {
            "name": "tumor_benign.jpeg",
            "path": backend_dir / "samples" / "tumor" / "tumor_benign.jpeg",
            "ground_truth": "Benign",
            # Lesion in distal radius/ulna or proximal tibia/fibula
            # Let's test manual crop coordinates around the lesion
            # Width=1560, Height=2484
            "roi_box": (350, 1400, 1150, 2150) # (x1, y1, x2, y2)
        },
        {
            "name": "tumor_malignant.jpeg",
            "path": backend_dir / "samples" / "tumor" / "tumor_malignant.jpeg",
            "ground_truth": "Malignant",
            # Width=3213, Height=2397
            # Osteosarcoma/malignant lesion in distal femur / proximal tibia
            "roi_box": (1100, 450, 2350, 1600) # (x1, y1, x2, y2)
        },
        {
            "name": "tumor_normal.jpeg",
            "path": backend_dir / "samples" / "tumor" / "tumor_normal.jpeg",
            "ground_truth": "Normal",
            # Normal has no lesion; whole image is training setup
            "roi_box": None
        }
    ]

    print("\n--- Running Inference Comparison ---")
    results = []

    for s in samples:
        with open(s["path"], "rb") as f:
            raw_bytes = f.read()

        img = Image.open(s["path"]).convert("RGB")
        w, h = img.size

        # 1. Whole Image Inference
        whole_pred = predict_tumor(raw_bytes, bbox=None)

        # 2. ROI Cropped Inference
        roi_pred = None
        if s["roi_box"] is not None:
            roi_pred = predict_tumor(raw_bytes, bbox=s["roi_box"])

        results.append({
            "name": s["name"],
            "gt": s["ground_truth"],
            "dimensions": f"{w}x{h}",
            "whole_pred": whole_pred["prediction"],
            "whole_probs": whole_pred["probabilities"],
            "roi_box": s["roi_box"],
            "roi_pred": roi_pred["prediction"] if roi_pred else "N/A (No ROI)",
            "roi_probs": roi_pred["probabilities"] if roi_pred else None
        })

    print("\n" + "="*110)
    print(f"{'File':<22} | {'GT':<10} | {'Mode':<12} | {'Prediction':<10} | {'Normal %':<10} | {'Benign %':<10} | {'Malignant %':<10}")
    print("="*110)

    for r in results:
        wp = r["whole_probs"]
        print(f"{r['name']:<22} | {r['gt']:<10} | {'Whole Image':<12} | {r['whole_pred']:<10} | {wp['Normal']*100:<10.2f} | {wp['Benign']*100:<10.2f} | {wp['Malignant']*100:<10.2f}")
        if r["roi_probs"]:
            rp = r["roi_probs"]
            print(f"{r['name']:<22} | {r['gt']:<10} | {'ROI Crop':<12} | {r['roi_pred']:<10} | {rp['Normal']*100:<10.2f} | {rp['Benign']*100:<10.2f} | {rp['Malignant']*100:<10.2f}")
        print("-" * 110)

if __name__ == "__main__":
    run_experiment()
