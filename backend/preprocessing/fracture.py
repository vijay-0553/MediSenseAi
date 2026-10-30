import io
import numpy as np
from PIL import Image

IMG_SIZE = 224

def preprocess_fracture_image(image_bytes: bytes) -> np.ndarray:
    """
    Standard ImageNet-normalized tensor for DenseNet201.
    Uses PIL & NumPy with zero TensorFlow overhead to maintain strict < 150MB RAM footprint.
    """
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    norm = (arr - mean) / std
    return np.expand_dims(norm, axis=0)
