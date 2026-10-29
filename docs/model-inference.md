# MediSense AI - Deep Learning Pipelines & Model Inference Reference

This document provides exact technical specifications for the 5 pre-trained specialist models, their preprocessing pipelines, class orders, evaluation parameters, and clinically documented limitations derived directly from the verified production checkpoints and source notebooks.

---

## Model Architectures & Pipeline Specifications

### 1. Bone Fracture (Upper Limb)
- **Checkpoint**: `backend/models/models/fracture/DenseNet201_CBAM_Final.keras`
- **Framework**: Keras 3 / TensorFlow (`tensorflow-cpu`)
- **Architecture**: DenseNet-201 backbone with Convolutional Block Attention Module (CBAM)
- **Input Dimensions**: $224 \times 224 \times 3$
- **Preprocessing** (from `bone-fracture-notebook.ipynb` Cells 10-11):
  1. Image decoded via `tf.io.decode_image(image_bytes, channels=3, expand_animations=False)`
  2. Bilinear resize to $224 \times 224$ via `tf.image.resize(img, (224, 224))`
  3. Preprocessing via `tensorflow.keras.applications.densenet.preprocess_input` (scales pixel range $[-1, +1]$)
- **Output Activation**: Single Sigmoid neuron
- **Class Mapping**:
  - `0`: `"not fractured"` (alphabetical directory order)
  - `1`: `"fractured"`
  - Output float directly represents $P(\text{fracture})$
- **Decision Threshold**: `0.50`

---

### 2. Bone Tumor (BTXRD)
- **Checkpoints**: `backend/models/models/bone_tumor/resnet50_baseline_fold{1..5}.pth` (5 checkpoints)
- **Framework**: PyTorch (`torch`, CPU mode)
- **Architecture**: ResNet-50 baseline 5-fold cross-validation ensemble (soft voting mean)
- **Input Dimensions**: $384 \times 384 \times 3$
- **Preprocessing** (from `btxrtd-without-cbam.ipynb` Cells 6-8):
  1. PIL RGB decode
  2. Optional ROI crop with 10% surrounding padding (`crop_with_padding(img, bbox, padding=0.10)`); if no box provided, uses the whole image
  3. Bilinear resize to $384 \times 384$
  4. Convert to Tensor, normalize with ImageNet Mean $[0.485, 0.456, 0.406]$ and Std $[0.229, 0.224, 0.225]$
- **Output Activation**: Softmax over 3 logits, averaged across all 5 folds
- **Class Mapping**:
  - Index `0`: `"Normal"`
  - Index `1`: `"Benign"`
  - Index `2`: `"Malignant"`
- **Analysis Modes**:
  - `roi_cropped`: Targeted analysis on user-specified lesion region.
  - `whole_image_no_roi`: Whole image without lesion crop.

---

### 3. Spine
- **Checkpoints**: `backend/models/models/spine/medisense_spine_densenet201_cbam.pth`
- **Framework**: PyTorch (`torch`, CPU mode)
- **Architecture**: `MediSenseDenseNet201` with CBAM attention module
- **Input Formats**: DICOM (`.dcm`, `.dicom`), PNG, JPEG
- **Input Dimensions**: $224 \times 224 \times 3$
- **Preprocessing** (from `spine-notebook.ipynb` Cell 12):
  1. For DICOM: Read via `pydicom.dcmread(stream, force=True)`, apply `RescaleSlope` and `RescaleIntercept`, invert if `PhotometricInterpretation == "MONOCHROME1"`, min-max scale to uint8 range $[0, 255]$
  2. For standard images: PIL grayscale ('L') convert to uint8 array
  3. Exact PyTorch `F.interpolate(tensor, size=(224, 224), mode="bilinear", align_corners=False)` on uint8 array
  4. Convert to PIL, ToTensor, 3-channel repeat, ImageNet normalization
- **Output Activation**: Single Sigmoid neuron
- **Class Mapping**:
  - Sigmoid float $P(\text{abnormal})$
  - Label is `"Abnormal"` if $P \ge 0.7574001550674438$, otherwise `"Normal"`
- **Decision Threshold**: `0.7574` (calibrated checkpoint decision threshold)

---

### 4. Knee Osteoarthritis
- **Checkpoint**: `backend/models/models/knee/MediSense_Knee_EfficientNetB5_CleanLab_Final.pth`
- **Framework**: PyTorch (`torch`, CPU mode)
- **Architecture**: `EfficientNetB5_Knee` (EfficientNet-B5 with custom classifier head)
- **Input Dimensions**: $224 \times 224 \times 3$
- **Preprocessing** (from `knee-osteoarthritis-notebook.ipynb`):
  1. PIL RGB decode
  2. Plain resize to $224 \times 224$
  3. Convert to Tensor, normalize with ImageNet Mean $[0.485, 0.456, 0.406]$ and Std $[0.229, 0.224, 0.225]$
- **Output Activation**: Softmax over 5 logits
- **Class Mapping**:
  - Index `0`: `"KL-0"` (Normal)
  - Index `1`: `"KL-1"` (Doubtful)
  - Index `2`: `"KL-2"` (Mild)
  - Index `3`: `"KL-3"` (Moderate)
  - Index `4`: `"KL-4"` (Severe)

---

### 5. Chest Pathologies
- **Checkpoint**: `backend/models/models/chest/chest_model.pth`
- **Framework**: PyTorch (`torch`, CPU mode)
- **Architecture**: DenseNet-121 multi-label classifier
- **Input Dimensions**: $224 \times 224 \times 3$
- **Preprocessing** (from `chest-notebook.ipynb`):
  1. PIL RGB decode
  2. Resize to $224 \times 224$
  3. Convert to Tensor, normalize with ImageNet Mean $[0.485, 0.456, 0.406]$ and Std $[0.229, 0.224, 0.225]$
- **Output Activation**: 14 independent Sigmoid outputs (probabilities do not sum to 100%)
- **Pathologies (14 Monitored Conditions)**:
  `Atelectasis`, `Cardiomegaly`, `Consolidation`, `Edema`, `Effusion`, `Emphysema`, `Fibrosis`, `Hernia`, `Infiltration`, `Mass`, `Nodule`, `Pleural_Thickening`, `Pneumonia`, `Pneumothorax`
- **Decision Threshold**: Uncalibrated flat `0.50` threshold across all 14 labels (notebook `best_thresholds` was not saved). Multiple labels exceeding 0.50 are flagged. If 0 labels exceed 0.50, status defaults to `"No Finding (Derived)"`.

---

## Documented Sample-Set Results & Clinical Limitations

### 1. Bone Tumor Whole-Image Skew (Resolved via Optional ROI Step)
- **Training Setup**: In the BTXRD dataset, Benign and Malignant training images had LabelMe JSON annotations and were strictly cropped around the lesion using `crop_with_padding(..., padding=0.10)`. Normal images had no lesion annotations and were trained as whole images.
- **Observed Behavior on Whole Images**:
  - `tumor_benign.jpeg` (Ground Truth: Benign) &rarr; Whole image: Normal 88.75%, Benign 1.83%, Malignant 9.42%.
  - `tumor_malignant.jpeg` (Ground Truth: Malignant) &rarr; Whole image: Normal 77.67%, Benign 6.45%, Malignant 15.88%.
  - `tumor_normal.jpeg` (Ground Truth: Normal) &rarr; Whole image: Normal 89.40%.
- **Observed Behavior with Targeted ROI Crop**:
  - `tumor_benign.jpeg` &rarr; ROI Crop: Normal drops to 56.18%, Benign increases to 12.70%, Malignant increases to 31.12% (in Fold 3, Malignant reaches 63.37%).
  - `tumor_malignant.jpeg` &rarr; ROI Crop: Normal drops to 40.32%, Benign + Malignant pathological mass rises to 59.69%.
- **Resolution**: Implemented an interactive ROI selection step in the web UI and API (`roi_box`). If whole image is analyzed, prominent notices specify: *"Whole-image analysis is outside the model's training setup. Results may be unreliable and are not a screening result."*

### 2. Knee Osteoarthritis Subtle Feature Sensitivity
- Early-stage osteophytes and marginal joint space narrowing in KL-1 and KL-2 samples are subtle on global $224 \times 224$ radiographs, causing sample borderline scans to classify as `KL-0`.
- Handled by reporting top-2 differential grades and displaying the standard Kellgren-Lawrence clinical reference guide labeled clearly as reference.

### 3. Chest Multi-Label Independence
- All 14 outputs represent independent binary sigmoid probabilities. They do not sum to 100%.
- A flat 0.50 decision threshold is applied without per-pathology calibrated cutoffs.
