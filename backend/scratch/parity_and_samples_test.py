import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import io
import numpy as np
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
import pydicom
import tensorflow as tf
from tensorflow.keras.applications.densenet import preprocess_input as tf_preprocess_input

from services.model_manager import model_manager
from inference.fracture import predict_fracture
from inference.spine import predict_spine
from inference.knee import predict_knee
from inference.chest import predict_chest
from inference.tumor import predict_tumor

print("Loading all models...")
model_manager.load_all()

samples_root = Path("backend/samples")

# -------------------------------------------------------------
# 1. FRACTURE NOTEBOOK LOGIC VS BACKEND
# -------------------------------------------------------------
def notebook_fracture(img_path):
    # Exactly from bone-fracture-notebook.ipynb Cell 10 and 11
    image_bytes = tf.io.read_file(str(img_path))
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, [224, 224])
    image = tf.cast(image, tf.float32)
    image = tf_preprocess_input(image)
    batch = tf.expand_dims(image, 0)
    out = model_manager.models["fracture"].predict(batch, verbose=0)
    p = float(out[0, 0])
    return p

print("\n" + "="*80)
print("FRACTURE SAMPLES:")
fracture_diffs = []
for p in sorted((samples_root / "fracture").glob("*.png")):
    with open(p, "rb") as f:
        img_bytes = f.read()
    
    nb_p = notebook_fracture(p)
    be_res = predict_fracture(img_bytes)
    be_p = be_res["probabilities"]["fractured"]
    diff = abs(nb_p - be_p)
    fracture_diffs.append(diff)
    
    gt = "fractured" if "not" not in p.name else "not fractured"
    print(f"File: {p.name:<20} | GT: {gt:<14} | Pred: {be_res['prediction']:<14} | P(fracture): {be_p:.4f} | NB P: {nb_p:.4f} | Diff: {diff:.6f}")

# -------------------------------------------------------------
# 2. SPINE NOTEBOOK LOGIC VS BACKEND
# -------------------------------------------------------------
def notebook_spine(dcm_path):
    # Exactly from spine-notebook.ipynb Cell 12, 13, 14
    ds = pydicom.dcmread(str(dcm_path), force=True)
    image = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0))
    intercept = float(getattr(ds, "RescaleIntercept", 0.0))
    image = image * slope + intercept
    if getattr(ds, "PhotometricInterpretation", "") == "MONOCHROME1":
        image = image.max() - image
    image -= image.min()
    max_val = image.max()
    if max_val > 0:
        image /= max_val
    uint8_img = (image * 255.0).clip(0, 255).astype(np.uint8)
    
    tensor = torch.from_numpy(uint8_img).float()[None, None]
    tensor = F.interpolate(tensor, size=(224, 224), mode="bilinear", align_corners=False)
    resized_uint8 = tensor[0, 0].clamp(0, 255).byte().numpy()
    
    eval_tfm = transforms.Compose([
        transforms.ToPILImage(),
        transforms.ToTensor(),
        transforms.Lambda(lambda x: x.repeat(3, 1, 1)),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    inp = eval_tfm(resized_uint8).unsqueeze(0).to(model_manager.device)
    with torch.inference_mode():
        logits = model_manager.models["spine"](inp)
        p = float(torch.sigmoid(logits).item())
    return p

print("\n" + "="*80)
print("SPINE SAMPLES:")
spine_diffs = []
for p in sorted((samples_root / "spine").glob("*.dicom")):
    with open(p, "rb") as f:
        img_bytes = f.read()
    
    nb_p = notebook_spine(p)
    be_res = predict_spine(img_bytes, filename=p.name)
    be_p = be_res["probability_abnormal"]
    diff = abs(nb_p - be_p)
    spine_diffs.append(diff)
    
    gt = "Abnormal" if "abnormal" in p.name else "Normal"
    print(f"File: {p.name:<20} | GT: {gt:<10} | Pred: {be_res['prediction']:<10} | P(abnormal): {be_p:.4f} | NB P: {nb_p:.4f} | Diff: {diff:.6f}")

# -------------------------------------------------------------
# 3. KNEE NOTEBOOK LOGIC VS BACKEND
# -------------------------------------------------------------
def notebook_knee(img_path):
    eval_tfm = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img = Image.open(str(img_path)).convert("RGB")
    inp = eval_tfm(img).unsqueeze(0).to(model_manager.device)
    with torch.inference_mode():
        logits = model_manager.models["knee"](inp)
        probs = torch.softmax(logits, dim=1)[0].cpu().numpy()
    return probs

print("\n" + "="*80)
print("KNEE SAMPLES:")
knee_diffs = []
for p in sorted((samples_root / "knee").glob("*.png")):
    with open(p, "rb") as f:
        img_bytes = f.read()
    
    nb_probs = notebook_knee(p)
    be_res = predict_knee(img_bytes)
    be_probs = np.array([be_res["probabilities"][k] for k in ["KL-0", "KL-1", "KL-2", "KL-3", "KL-4"]])
    diff = float(np.max(np.abs(nb_probs - be_probs)))
    knee_diffs.append(diff)
    
    gt = p.stem.replace("knee_", "")
    print(f"File: {p.name:<15} | GT: {gt:<6} | Pred: {be_res['prediction']:<6} | Conf: {be_res['confidence']:.4f} | Max Diff: {diff:.6f} | Probs: {be_res['probabilities']}")

# -------------------------------------------------------------
# 4. CHEST NOTEBOOK LOGIC VS BACKEND
# -------------------------------------------------------------
def notebook_chest(img_path):
    eval_tfm = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img = Image.open(str(img_path)).convert("RGB")
    inp = eval_tfm(img).unsqueeze(0).to(model_manager.device)
    with torch.inference_mode():
        logits = model_manager.models["chest"](inp)
        probs = torch.sigmoid(logits)[0].cpu().numpy()
    return probs

print("\n" + "="*80)
print("CHEST SAMPLES:")
chest_diffs = []
for p in sorted((samples_root / "chest").glob("*.png")):
    with open(p, "rb") as f:
        img_bytes = f.read()
    
    nb_probs = notebook_chest(p)
    be_res = predict_chest(img_bytes)
    pathologies = list(be_res["all_probabilities"].keys())
    be_probs = np.array([be_res["all_probabilities"][k] for k in pathologies])
    # match notebook pathology order
    meta_pathologies = model_manager.metadata["chest"]["pathologies"]
    nb_ordered = [nb_probs[meta_pathologies.index(k)] for k in pathologies]
    diff = float(np.max(np.abs(np.array(nb_ordered) - be_probs)))
    chest_diffs.append(diff)
    
    gt = "Cardiomegaly" if "cardiomegaly" in p.name else "No Finding"
    print(f"File: {p.name:<25} | GT: {gt:<15} | Pred: {be_res['primary_finding']:<15} | Flagged: {[f['pathology'] for f in be_res['flagged_findings']]} | Max Diff: {diff:.6f}")

# -------------------------------------------------------------
# 5. TUMOR NOTEBOOK LOGIC VS BACKEND
# -------------------------------------------------------------
def notebook_tumor(img_path):
    eval_tfm = transforms.Compose([
        transforms.Resize((384, 384)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img = Image.open(str(img_path)).convert("RGB")
    inp = eval_tfm(img).unsqueeze(0).to(model_manager.device)
    all_p = []
    with torch.inference_mode():
        for m in model_manager.models["tumor"]:
            logits = m(inp)
            p = torch.softmax(logits, dim=1)[0].cpu().numpy()
            all_p.append(p)
    return np.mean(all_p, axis=0)

print("\n" + "="*80)
print("TUMOR SAMPLES:")
tumor_diffs = []
for p in sorted((samples_root / "tumor").glob("*")):
    if not p.is_file(): continue
    with open(p, "rb") as f:
        img_bytes = f.read()
    
    nb_probs = notebook_tumor(p)
    be_res = predict_tumor(img_bytes)
    be_probs = np.array([be_res["probabilities"][k] for k in ["Normal", "Benign", "Malignant"]])
    diff = float(np.max(np.abs(nb_probs - be_probs)))
    tumor_diffs.append(diff)
    
    gt = p.stem.replace("tumor_", "").capitalize()
    print(f"File: {p.name:<22} | GT: {gt:<12} | Pred: {be_res['prediction']:<12} | Conf: {be_res['confidence']:.4f} | Max Diff: {diff:.6f} | Probs: {be_res['probabilities']}")

print("\n" + "="*80)
print("MAX ABSOLUTE PROBABILITY DIFFERENCE SUMMARY:")
print(f"  Fracture max diff: {max(fracture_diffs):.6f}")
print(f"  Spine max diff:    {max(spine_diffs):.6f}")
print(f"  Knee max diff:     {max(knee_diffs):.6f}")
print(f"  Chest max diff:    {max(chest_diffs):.6f}")
print(f"  Tumor max diff:    {max(tumor_diffs):.6f}")
