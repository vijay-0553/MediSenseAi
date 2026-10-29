import tensorflow as tf
from tensorflow.keras import layers

@tf.keras.utils.register_keras_serializable(name="CBAM")
class CBAM(layers.Layer):
    """
    Convolutional Block Attention Module (CBAM) for Keras
    Reproduced exactly from bone-fracture-notebook.ipynb
    """
    def __init__(self, reduction_ratio=16, kernel_size=7, **kwargs):
        super().__init__(**kwargs)
        self.reduction_ratio = reduction_ratio
        self.kernel_size = kernel_size

    def build(self, input_shape):
        channels = int(input_shape[-1])
        hidden = max(channels // self.reduction_ratio, 1)

        self.channel_mlp_1 = layers.Dense(hidden, activation="relu")
        self.channel_mlp_2 = layers.Dense(channels)
        self.spatial_conv = layers.Conv2D(
            filters=1,
            kernel_size=self.kernel_size,
            padding="same",
            activation="sigmoid"
        )
        super().build(input_shape)

    def call(self, inputs):
        avg_pool = tf.reduce_mean(inputs, axis=[1, 2], keepdims=True)
        max_pool = tf.reduce_max(inputs, axis=[1, 2], keepdims=True)

        avg_attention = self.channel_mlp_2(self.channel_mlp_1(avg_pool))
        max_attention = self.channel_mlp_2(self.channel_mlp_1(max_pool))

        channel_attention = tf.nn.sigmoid(avg_attention + max_attention)
        x = inputs * channel_attention

        avg_spatial = tf.reduce_mean(x, axis=-1, keepdims=True)
        max_spatial = tf.reduce_max(x, axis=-1, keepdims=True)

        spatial_input = tf.concat([avg_spatial, max_spatial], axis=-1)
        spatial_attention = self.spatial_conv(spatial_input)

        return x * spatial_attention

    def get_config(self):
        config = super().get_config()
        config.update({
            "reduction_ratio": self.reduction_ratio,
            "kernel_size": self.kernel_size,
        })
        return config
