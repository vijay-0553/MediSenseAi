import io
from typing import Optional, Tuple, Union
import torch
from PIL import Image
from torchvision import transforms

IMAGE_SIZE = 384
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# Exact evaluation transform from btxrtd-without-cbam.ipynb Cell 8
eval_transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

def crop_with_padding(
    img: Image.Image,
    bbox: Optional[Union[Tuple[float, float, float, float], list]] = None,
    padding: float = 0.10
) -> Image.Image:
    """
    Exact implementation from btxrtd-without-cbam.ipynb Cell 7.
    Supports both pixel coordinates and normalized [0.0..1.0] coordinates.
    When bbox is None, returns img directly (whole-image mode).
    """
    if bbox is None:
        return img

    w, h = img.size
    x1, y1, x2, y2 = bbox

    # Denormalize if normalized 0..1 coordinates provided
    if max(x1, x2, y1, y2) <= 1.0:
        x1, x2 = x1 * w, x2 * w
        y1, y2 = y1 * h, y2 * h

    x1, x2 = sorted([max(0.0, min(float(w - 1), float(x1))), max(0.0, min(float(w - 1), float(x2)))])
    y1, y2 = sorted([max(0.0, min(float(h - 1), float(y1))), max(0.0, min(float(h - 1), float(y2)))])

    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)

    x1 = max(0, int(round(x1 - bw * padding)))
    y1 = max(0, int(round(y1 - bh * padding)))
    x2 = min(w, int(round(x2 + bw * padding)))
    y2 = min(h, int(round(y2 + bh * padding)))

    if x2 <= x1 or y2 <= y1:
        return img

    return img.crop((x1, y1, x2, y2))

def preprocess_tumor_image(image_bytes: bytes, bbox=None) -> torch.Tensor:
    """
    Preprocess raw image bytes for Bone Tumor ResNet-50 5-fold ensemble:
    1. Load image and convert to RGB
    2. crop_with_padding(img, bbox)
    3. Direct Resize to (384, 384)
    4. ToTensor
    5. ImageNet Normalize
    6. Returns shape (1, 3, 384, 384)
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cropped = crop_with_padding(img, bbox=bbox, padding=0.10)
    tensor = eval_transform(cropped)
    return tensor.unsqueeze(0)
