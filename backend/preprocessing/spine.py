import io
import numpy as np
import pydicom
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

def dicom_to_uint8(dcm_bytes: bytes) -> np.ndarray:
    """
    Exact DICOM extraction from spine-notebook.ipynb Cell 12:
    - RescaleSlope and RescaleIntercept
    - MONOCHROME1 photometric interpretation inversion
    - Min-max scaling and clip to 0..255 uint8 array
    """
    with io.BytesIO(dcm_bytes) as stream:
        ds = pydicom.dcmread(stream, force=True)

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

    return (image * 255.0).clip(0, 255).astype(np.uint8)

def resize_uint8(image: np.ndarray) -> np.ndarray:
    """
    Exact F.interpolate bilinear resize from spine-notebook.ipynb Cell 12.
    """
    tensor = torch.from_numpy(image).float()[None, None]
    tensor = F.interpolate(
        tensor,
        size=(IMG_SIZE, IMG_SIZE),
        mode="bilinear",
        align_corners=False
    )
    return tensor[0, 0].clamp(0, 255).byte().numpy()

eval_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.ToTensor(),
    transforms.Lambda(lambda x: x.repeat(3, 1, 1)),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

def preprocess_spine_image(image_bytes: bytes, filename: str = "") -> torch.Tensor:
    """
    Preprocess raw image bytes for Spine MediSenseDenseNet201-CBAM model:
    Replicates exact pipeline from spine-notebook.ipynb.
    Supports DICOM, JPEG, and PNG.
    """
    fname = filename.lower()
    is_dicom = (
        fname.endswith(".dcm")
        or fname.endswith(".dicom")
        or image_bytes[:4] == b"DICM"
        or (len(image_bytes) > 132 and image_bytes[128:132] == b"DICM")
    )

    if is_dicom:
        raw_uint8 = dicom_to_uint8(image_bytes)
    else:
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("L")
        raw_uint8 = np.array(pil_img, dtype=np.uint8)

    resized_uint8 = resize_uint8(raw_uint8)
    tensor = eval_transform(resized_uint8)
    return tensor.unsqueeze(0)
