import time
from typing import Any, Dict, List
import torch
from preprocessing.chest import preprocess_chest_image
from services.model_manager import model_manager

def predict_chest(image_bytes: bytes, threshold: float = 0.50) -> Dict[str, Any]:
    """
    Run multilabel inference for ChestX-ray14 module.
    Outputs:
    - all_probabilities: {pathology: prob} sorted high to low
    - findings: list of flagged pathologies exceeding threshold
    - derived_no_finding: bool (True only when no pathology exceeds threshold)
    - interpretation_note: neutral clinical summary
    """
    if "chest" not in model_manager.models:
        raise RuntimeError("Chest model is not loaded: " + str(model_manager.model_status.get("chest", {}).get("error", "Unknown error")))

    model = model_manager.models["chest"]
    meta = model_manager.metadata.get("chest", {})
    pathologies: List[str] = meta.get("pathologies", [
        "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration", "Mass",
        "Nodule", "Pneumonia", "Pneumothorax", "Consolidation", "Edema",
        "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia"
    ])
    device = model_manager.device

    start_time = time.perf_counter()

    tensor = preprocess_chest_image(image_bytes).to(device)

    with model_manager.locks["chest"]:
        with torch.inference_mode():
            logits = model(tensor)
            probs = torch.sigmoid(logits)[0].cpu().numpy()

    inference_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Sort all 14 pathologies high to low
    sorted_items = sorted(
        zip(pathologies, [float(p) for p in probs]),
        key=lambda item: item[1],
        reverse=True
    )

    all_probabilities = {name: round(p, 4) for name, p in sorted_items}

    flagged_findings = [
        {"pathology": name, "probability": round(p, 4), "threshold": threshold}
        for name, p in sorted_items
        if p >= threshold
    ]

    is_no_finding = len(flagged_findings) == 0
    top_pathology, top_prob = sorted_items[0]

    if is_no_finding:
        interpretation_note = f"0 labels above the {int(threshold*100)}% threshold. 'No Finding' is derived based on all 14 monitored thoracic conditions remaining below the decision threshold."
        status_text = "No Finding (Derived)"
    else:
        interpretation_note = f"{len(flagged_findings)} label(s) above the {int(threshold*100)}% threshold: {', '.join([f['pathology'] for f in flagged_findings])}."
        status_text = f"{len(flagged_findings)} label(s) above {int(threshold*100)}% threshold"

    notices = [
        "Labels use an uncalibrated 0.5 threshold; multiple labels may be flagged. Probabilities are independent and do not sum to 100%."
    ]

    return {
        "module": "chest",
        "module_name": "Chest (ChestX-ray14)",
        "model_architecture": "DenseNet-121",
        "decision_threshold": threshold,
        "derived_no_finding": is_no_finding,
        "derived_status": status_text,
        "primary_finding": "No Finding (Derived)" if is_no_finding else top_pathology,
        "flagged_findings": flagged_findings,
        "findings_count": len(flagged_findings),
        "all_probabilities": all_probabilities,
        "notices": notices,
        "interpretation_note": interpretation_note,
        "inference_time_ms": inference_time_ms,
    }
