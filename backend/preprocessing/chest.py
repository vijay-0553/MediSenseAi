import io
import torch
from PIL import Image
from torchvision import transforms

IMG_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

eval_transform = transforms.Compose([
    transforms.Resize((IMG_SIZE, IMG_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
])

def preprocess_chest_image(image_bytes: bytes) -> torch.Tensor:
    """
    Preprocess raw image bytes for Chest DenseNet-121 model:
    1. Load image and convert to RGB
    2. Resize to 224x224
    3. ToTensor
    4. ImageNet Normalize
    5. Returns shape (1, 3, 224, 224)
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = eval_transform(img)
    return tensor.unsqueeze(0)
