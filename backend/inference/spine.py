import time
from typing import Any, Dict
import torch
from preprocessing.spine import preprocess_spine_image
from services.model_manager import model_manager

def predict_spine(image_bytes: bytes, filename: str = "") -> Dict[str, Any]:
    """
    Run inference for Spine module.
    Threshold: 0.7574 (from checkpoint)
    Outputs:
    - prediction: 'Normal' or 'Abnormal'
    - probability_abnormal: raw sigmoid output P(Abnormal)
    - decision_threshold: 0.7574
    - probabilities: {'Normal': 1 - p, 'Abnormal': p}
    - interpretation_note: neutral clinical explanation
    """
    if "spine" not in model_manager.models:
        model_manager.ensure_loaded("spine")
    if "spine" not in model_manager.models:
        raise RuntimeError("Spine model is not loaded: " + str(model_manager.model_status.get("spine", {}).get("error", "Unknown error")))

    model = model_manager.models["spine"]
    meta = model_manager.metadata.get("spine", {})
    threshold = float(meta.get("threshold", 0.7574001550674438))
    device = model_manager.device

    start_time = time.perf_counter()

    tensor = preprocess_spine_image(image_bytes, filename=filename).to(device)

    with model_manager.locks["spine"]:
        with torch.inference_mode():
            logits = model(tensor)
            p_abnormal = float(torch.sigmoid(logits).item())

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    is_abnormal = p_abnormal >= threshold
    prediction = "Abnormal" if is_abnormal else "Normal"

    pct = p_abnormal * 100.0
    thresh_pct = threshold * 100.0
    if is_abnormal:
        interpretation_note = f"AI prediction: Abnormal. Abnormal probability ({pct:.1f}%) exceeds the model's decision threshold ({thresh_pct:.1f}%)."
    else:
        interpretation_note = f"AI prediction: Normal. Abnormal probability ({pct:.1f}%) is below the model's decision threshold ({thresh_pct:.1f}%)."

    notices = []
    # If confidence is below 50% on any module with low_confidence
    # Spine is binary classification with calibrated threshold 0.7574

    return {
        "module": "spine",
        "module_name": "Spine",
        "model_architecture": "MediSense DenseNet-201 + CBAM",
        "prediction": prediction,
        "probability_abnormal": round(p_abnormal, 4),
        "decision_threshold": round(threshold, 4),
        "probabilities": {
            "Normal": round(1.0 - p_abnormal, 4),
            "Abnormal": round(p_abnormal, 4),
        },
        "notices": notices,
        "interpretation_note": interpretation_note,
        "inference_time_ms": inference_time_ms,
    }
