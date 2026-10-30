import logging
import threading
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import torch
import torchvision.models as tv_models
import tensorflow as tf

from config import settings
from architectures.cbam_keras import CBAM as KerasCBAM
from architectures.spine_cbam import MediSenseDenseNet201
from architectures.knee_efficientnet import EfficientNetB5_Knee

logger = logging.getLogger("medisense.model_manager")
logging.basicConfig(level=logging.INFO)

class ModelManager:
    """
    Central registry and thread-safe loader for MediSense AI models.
    Keeps checkpoints in memory, manages devices, provides warm-up and thread locking.
    """
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Initialized ModelManager on device: {self.device}")

        # Thread locks to guard inference execution per model
        self.locks = {
            "fracture": threading.Lock(),
            "spine": threading.Lock(),
            "knee": threading.Lock(),
            "chest": threading.Lock(),
            "tumor": threading.Lock(),
        }

        # Centralized paths
        self.paths = {
            "fracture": settings.MODELS_DIR / "fracture" / "DenseNet201_CBAM_Final.keras",
            "spine": settings.MODELS_DIR / "spine" / "medisense_spine_densenet201_cbam.pth",
            "knee": settings.MODELS_DIR / "knee" / "MediSense_Knee_EfficientNetB5_CleanLab_Final.pth",
            "chest": settings.MODELS_DIR / "chest" / "chest_model.pth",
            "tumor": [
                settings.MODELS_DIR / "bone_tumor" / f"resnet50_baseline_fold{fold}.pth"
                for fold in range(1, 6)
            ],
        }

        # Model containers
        self.models: Dict[str, Any] = {}
        self.model_status: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Any] = {}

    def load_fracture(self) -> bool:
        path = self.paths["fracture"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")
            logger.info(f"Loading Fracture model from {path}...")
            model = tf.keras.models.load_model(
                str(path),
                custom_objects={"CBAM": KerasCBAM},
                compile=False
            )
            self.models["fracture"] = model
            self.model_status["fracture"] = {
                "loaded": True,
                "framework": "TensorFlow/Keras",
                "format": "Keras 3 (.keras)",
                "device": "CPU" if not tf.config.list_physical_devices("GPU") else "GPU",
                "path": str(path.name),
            }
            logger.info("Fracture model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Fracture model: {e}", exc_info=True)
            self.model_status["fracture"] = {
                "loaded": False,
                "error": str(e),
                "path": str(path.name),
            }
            return False

    def load_spine(self) -> bool:
        path = self.paths["spine"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")
            logger.info(f"Loading Spine model from {path}...")
            ckpt = torch.load(str(path), map_location=self.device, weights_only=False)
            model = MediSenseDenseNet201()
            model.load_state_dict(ckpt["state_dict"])
            model.to(self.device)
            model.eval()

            self.models["spine"] = model
            threshold = float(ckpt.get("threshold", 0.7574001550674438))
            self.metadata["spine"] = {
                "model_name": ckpt.get("model_name", "MediSense DenseNet-201 + CBAM"),
                "threshold": threshold,
                "img_size": ckpt.get("img_size", 224),
                "classes": ["Normal", "Abnormal"],
            }
            self.model_status["spine"] = {
                "loaded": True,
                "framework": "PyTorch",
                "device": str(self.device),
                "threshold": threshold,
                "path": str(path.name),
            }
            logger.info(f"Spine model loaded successfully with threshold {threshold:.4f}.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Spine model: {e}", exc_info=True)
            self.model_status["spine"] = {
                "loaded": False,
                "error": str(e),
                "path": str(path.name),
            }
            return False

    def load_knee(self) -> bool:
        path = self.paths["knee"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")
            logger.info(f"Loading Knee model from {path}...")
            ckpt = torch.load(str(path), map_location=self.device, weights_only=False)
            model = EfficientNetB5_Knee(num_classes=ckpt.get("num_classes", 5))
            model.load_state_dict(ckpt["model_state_dict"])
            model.to(self.device)
            model.eval()

            self.models["knee"] = model
            classes = ckpt.get("class_names", ["KL-0", "KL-1", "KL-2", "KL-3", "KL-4"])
            self.metadata["knee"] = {
                "class_names": classes,
                "num_classes": len(classes),
                "image_size": ckpt.get("image_size", 224),
            }
            self.model_status["knee"] = {
                "loaded": True,
                "framework": "PyTorch",
                "device": str(self.device),
                "classes": classes,
                "path": str(path.name),
            }
            logger.info("Knee model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Knee model: {e}", exc_info=True)
            self.model_status["knee"] = {
                "loaded": False,
                "error": str(e),
                "path": str(path.name),
            }
            return False

    def load_chest(self) -> bool:
        path = self.paths["chest"]
        try:
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {path}")
            logger.info(f"Loading Chest model from {path}...")
            ckpt = torch.load(str(path), map_location=self.device, weights_only=False)
            
            # DenseNet-121 baseline with 14 disease outputs
            model = tv_models.densenet121(weights=None)
            model.classifier = torch.nn.Linear(model.classifier.in_features, 14)
            model.load_state_dict(ckpt["model_state_dict"])
            model.to(self.device)
            model.eval()

            self.models["chest"] = model
            pathologies = ckpt.get("pathologies", [
                "Atelectasis", "Cardiomegaly", "Effusion", "Infiltration", "Mass",
                "Nodule", "Pneumonia", "Pneumothorax", "Consolidation", "Edema",
                "Emphysema", "Fibrosis", "Pleural_Thickening", "Hernia"
            ])
            self.metadata["chest"] = {
                "pathologies": pathologies,
                "image_size": ckpt.get("image_size", 224),
                "default_threshold": 0.50,
            }
            self.model_status["chest"] = {
                "loaded": True,
                "framework": "PyTorch",
                "device": str(self.device),
                "pathologies_count": len(pathologies),
                "path": str(path.name),
            }
            logger.info(f"Chest model loaded successfully with {len(pathologies)} pathologies.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Chest model: {e}", exc_info=True)
            self.model_status["chest"] = {
                "loaded": False,
                "error": str(e),
                "path": str(path.name),
            }
            return False

    def load_tumor(self) -> bool:
        paths = self.paths["tumor"]
        try:
            fold_models: List[torch.nn.Module] = []
            classes = ["Normal", "Benign", "Malignant"]
            for i, p in enumerate(paths, start=1):
                if not p.exists():
                    raise FileNotFoundError(f"Fold {i} model file not found: {p}")
                ckpt = torch.load(str(p), map_location=self.device, weights_only=False)
                model = tv_models.resnet50(weights=None)
                model.fc = torch.nn.Linear(2048, 3)
                model.load_state_dict(ckpt["model_state_dict"])
                model.to(self.device)
                model.eval()
                fold_models.append(model)
                if "class_names" in ckpt:
                    classes = ckpt["class_names"]

            self.models["tumor"] = fold_models
            self.metadata["tumor"] = {
                "classes": classes,
                "folds_count": len(fold_models),
                "image_size": 384,
                "analysis_mode": "whole_image_no_roi",
            }
            self.model_status["tumor"] = {
                "loaded": True,
                "framework": "PyTorch (5-Fold Ensemble)",
                "device": str(self.device),
                "folds_loaded": len(fold_models),
                "classes": classes,
            }
            logger.info(f"Bone Tumor model ensemble ({len(fold_models)} folds) loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load Tumor model ensemble: {e}", exc_info=True)
            self.model_status["tumor"] = {
                "loaded": False,
                "error": str(e),
            }
            return False

    def warmup(self):
        """
        Runs dummy forward passes through each loaded model to initialize runtime caches
        and eliminate first-request cold-start latency.
        """
        logger.info("Warming up models with synthetic zero-tensors...")
        try:
            if "fracture" in self.models:
                with self.locks["fracture"]:
                    dummy_tf = np.zeros((1, 224, 224, 3), dtype=np.float32)
                    self.models["fracture"].predict(dummy_tf, verbose=0)
            
            with torch.inference_mode():
                dummy_224 = torch.zeros((1, 3, 224, 224), device=self.device)
                if "spine" in self.models:
                    with self.locks["spine"]:
                        self.models["spine"](dummy_224)
                if "knee" in self.models:
                    with self.locks["knee"]:
                        self.models["knee"](dummy_224)
                if "chest" in self.models:
                    with self.locks["chest"]:
                        self.models["chest"](dummy_224)
                if "tumor" in self.models:
                    dummy_384 = torch.zeros((1, 3, 384, 384), device=self.device)
                    with self.locks["tumor"]:
                        for m in self.models["tumor"]:
                            m(dummy_384)
            logger.info("Model warmup completed successfully.")
        except Exception as e:
            logger.warning(f"Model warmup encountered a non-fatal error: {e}")

    def load_all(self):
        """Loads all 9 checkpoints into memory and runs warmup."""
        logger.info("=== Loading all 9 MediSense checkpoints ===")
        try:
            from ensure_models import ensure_all_models
            ensure_all_models()
        except Exception as e:
            logger.warning(f"Automatic model verification note: {e}")

        self.load_fracture()
        self.load_spine()
        self.load_knee()
        self.load_chest()
        self.load_tumor()
        self.warmup()
        logger.info("=== Model loading and warmup sequence completed ===")

    def get_status(self) -> Dict[str, Any]:
        return {
            "device": str(self.device),
            "modules": self.model_status,
        }

model_manager = ModelManager()
