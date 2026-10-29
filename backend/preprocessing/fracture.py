import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.densenet import preprocess_input

IMG_SIZE = 224

def preprocess_fracture_image(image_bytes: bytes) -> np.ndarray:
    """
    Exact notebook implementation (bone-fracture-notebook.ipynb Cell 10 and 11):
    1. tf.io.decode_image
    2. tf.image.resize to [224, 224] (Bilinear)
    3. tf.cast to float32
    4. densenet.preprocess_input
    5. expand_dims(axis=0)
    """
    image = tf.io.decode_image(image_bytes, channels=3, expand_animations=False)
    image.set_shape([None, None, 3])
    image = tf.image.resize(image, [IMG_SIZE, IMG_SIZE])
    image = tf.cast(image, tf.float32)
    image = preprocess_input(image)
    batch = tf.expand_dims(image, axis=0)
    return batch.numpy()
