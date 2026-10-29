import time
from typing import Any, Dict
from preprocessing.fracture import preprocess_fracture_image
from services.model_manager import model_manager

def predict_fracture(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run inference for Bone Fracture module.
    Outputs:
    - prediction: 'fractured' or 'not fractured'
    - confidence: float
    - probabilities: {'not fractured': prob, 'fractured': prob}
    - low_confidence: bool (true when top probability < 0.50)
    """
    if "fracture" not in model_manager.models:
        raise RuntimeError("Fracture model is not loaded: " + str(model_manager.model_status.get("fracture", {}).get("error", "Unknown error")))

    model = model_manager.models["fracture"]
    start_time = time.perf_counter()

    batch = preprocess_fracture_image(image_bytes)
    with model_manager.locks["fracture"]:
        raw_output = model.predict(batch, verbose=0)
    p_fracture = float(raw_output[0, 0])

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    is_fractured = p_fracture >= 0.5
    prediction = "fractured" if is_fractured else "not fractured"
    top_prob = p_fracture if is_fractured else (1.0 - p_fracture)
    low_conf = bool(top_prob < 0.50)

    interpretation_note = (
        f"AI prediction: {prediction}. Model fracture probability ({p_fracture:.1%}) "
        f"{'exceeds' if is_fractured else 'is below'} the 50.0% decision threshold."
    )

    notices = []
    if low_conf:
        notices.append("Model confidence is below 50%. Interpret with caution.")

    return {
        "module": "fracture",
        "module_name": "Bone Fracture (Upper Limb)",
        "model_architecture": "DenseNet201 + CBAM",
        "prediction": prediction,
        "confidence": round(top_prob, 4),
        "low_confidence": low_conf,
        "decision_threshold": 0.5,
        "probabilities": {
            "not fractured": round(1.0 - p_fracture, 4),
            "fractured": round(p_fracture, 4),
        },
        "raw_fracture_probability": round(p_fracture, 6),
        "notices": notices,
        "interpretation_note": interpretation_note,
        "inference_time_ms": inference_time_ms,
    }
