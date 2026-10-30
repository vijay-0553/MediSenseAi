import time
from typing import Any, Dict, List
import numpy as np
import torch
from preprocessing.knee import preprocess_knee_image
from services.model_manager import model_manager

KL_DESCRIPTIONS = {
    "KL-0": "Grade 0: Normal - no radiographic features of osteoarthritis.",
    "KL-1": "Grade 1: Doubtful joint space narrowing and possible osteophytic lipping.",
    "KL-2": "Grade 2: Definite osteophytes and possible joint space narrowing.",
    "KL-3": "Grade 3: Moderate multiple osteophytes, definite narrowing, and some sclerosis.",
    "KL-4": "Grade 4: Severe osteophytes, marked joint space narrowing, and severe sclerosis.",
}

def predict_knee(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run inference for Knee Osteoarthritis module.
    Outputs:
    - prediction: KL-0, KL-1, KL-2, KL-3, or KL-4
    - confidence: float
    - low_confidence: bool (true when top probability < 0.50)
    - top2: list of top 2 grades with probabilities
    - probabilities: {class_name: prob}
    """
    if "knee" not in model_manager.models:
        model_manager.ensure_loaded("knee")
    if "knee" not in model_manager.models:
        raise RuntimeError("Knee model is not loaded: " + str(model_manager.model_status.get("knee", {}).get("error", "Unknown error")))

    model = model_manager.models["knee"]
    meta = model_manager.metadata.get("knee", {})
    classes = meta.get("class_names", ["KL-0", "KL-1", "KL-2", "KL-3", "KL-4"])
    device = model_manager.device

    start_time = time.perf_counter()

    tensor = preprocess_knee_image(image_bytes).to(device)

    with model_manager.locks["knee"]:
        with torch.inference_mode():
            logits = model(tensor)
            probs = torch.softmax(logits, dim=1)[0].cpu().numpy()

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    pred_idx = int(np.argmax(probs))
    prediction = classes[pred_idx]
    confidence = float(probs[pred_idx])
    low_conf = bool(confidence < 0.50)

    # Compute top 2 grades
    sorted_indices = np.argsort(probs)[::-1]
    top2 = [
        {"grade": classes[idx], "probability": round(float(probs[idx]), 4)}
        for idx in sorted_indices[:2]
    ]

    interpretation_note = (
        f"AI prediction: {prediction} with model confidence of {confidence:.1%}. "
        f"Secondary differential grade: {top2[1]['grade']} ({top2[1]['probability']:.1%})."
    )

    notices = []
    if low_conf:
        notices.append("Low confidence; top-2 grades shown")
        notices.append("Model confidence is below 50%. Interpret with caution.")

    return {
        "module": "knee",
        "module_name": "Knee Osteoarthritis",
        "model_architecture": "EfficientNet-B5 (CleanLab)",
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "low_confidence": low_conf,
        "top2": top2,
        "reference_description": f"standard KL grade description (reference, not a model output): {KL_DESCRIPTIONS.get(prediction, '')}",
        "probabilities": {
            classes[i]: round(float(probs[i]), 4)
            for i in range(len(classes))
        },
        "notices": notices,
        "interpretation_note": interpretation_note,
        "inference_time_ms": inference_time_ms,
    }
