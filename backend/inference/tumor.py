import logging
import time
from typing import Any, Dict, List, Optional
import numpy as np
import torch
from preprocessing.tumor import preprocess_tumor_image
from services.model_manager import model_manager

logger = logging.getLogger("medisense.tumor")

def predict_tumor(image_bytes: bytes, bbox=None) -> Dict[str, Any]:
    """
    Run inference for Bone Tumor module using 5-fold ResNet-50 ensemble.
    Outputs:
    - prediction: 'Normal', 'Benign', or 'Malignant'
    - confidence: float
    - low_confidence: bool (true when top probability < 0.50)
    - probabilities: {class_name: prob}
    - analysis_mode: 'roi_cropped' or 'whole_image_no_roi'
    - roi_box: Optional bounding box
    """
    if "tumor" not in model_manager.models:
        raise RuntimeError("Tumor model ensemble is not loaded: " + str(model_manager.model_status.get("tumor", {}).get("error", "Unknown error")))

    fold_models: List[torch.nn.Module] = model_manager.models["tumor"]
    meta = model_manager.metadata.get("tumor", {})
    classes = meta.get("classes", ["Normal", "Benign", "Malignant"])
    device = model_manager.device

    start_time = time.perf_counter()

    tensor = preprocess_tumor_image(image_bytes, bbox=bbox).to(device)

    all_fold_probs = []
    with model_manager.locks["tumor"]:
        with torch.inference_mode():
            for fold_idx, model in enumerate(fold_models, start=1):
                logits = model(tensor)
                probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
                all_fold_probs.append(probs)
                logger.info(
                    f"[Tumor Ensemble] Fold {fold_idx}: "
                    f"Normal={probs[0]:.4f}, Benign={probs[1]:.4f}, Malignant={probs[2]:.4f}"
                )

    # Average across all 5 folds
    mean_probs = np.mean(all_fold_probs, axis=0)

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    pred_idx = int(np.argmax(mean_probs))
    prediction = classes[pred_idx]
    confidence = float(mean_probs[pred_idx])
    low_conf = bool(confidence < 0.50)

    is_roi = bbox is not None
    analysis_mode = "roi_cropped" if is_roi else "whole_image_no_roi"

    if is_roi:
        interpretation_note = (
            f"AI prediction: {prediction} (confidence: {confidence:.1%}) using targeted ROI lesion crop. "
            f"Evaluated with 5-fold ResNet-50 ensemble."
        )
        notices = [
            "ROI-guided analysis applied using selected lesion coordinates with 10% surrounding context.",
        ]
    else:
        interpretation_note = (
            f"AI prediction: {prediction} (confidence: {confidence:.1%}) in whole-image evaluation mode. "
            f"Model was trained on ROI-cropped tumor regions; whole-image analysis is outside the training setup."
        )
        notices = [
            "Whole-image analysis is outside the model's training setup. Results may be unreliable and are not a screening result.",
            "Model was trained on ROI-cropped tumor regions. Whole-image analysis is outside the training setup and results may be less reliable."
        ]

    if low_conf:
        notices.append("Model confidence is below 50%. Interpret with caution.")

    return {
        "module": "tumor",
        "module_name": "Bone Tumor (BTXRD)",
        "prediction": prediction,
        "confidence": confidence,
        "low_confidence": low_conf,
        "analysis_mode": analysis_mode,
        "roi_box": bbox,
        "probabilities": {
            classes[i]: float(mean_probs[i]) for i in range(len(classes))
        },
        "notices": notices,
        "interpretation_note": interpretation_note,
        "inference_time_ms": inference_time_ms,
        "model_architecture": "ResNet-50 Baseline (5-Fold Ensemble)",
    }
