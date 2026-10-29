import io
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from config import settings
from preprocessing.spine import dicom_to_uint8

logger = logging.getLogger("medisense.storage")

class StorageService:
    def __init__(self, reports_dir: Path = settings.REPORTS_DIR):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def save_prediction(
        self,
        report_id: str,
        result: Dict[str, Any],
        image_bytes: bytes,
        filename: str = ""
    ) -> Path:
        """
        Persists report data under backend/storage/reports/<report_id>/ :
        - result.json: prediction metadata & outputs
        - preview.png: browser/PDF display image (DICOM rendered via dicom_to_uint8;
          if roi_box provided, overlays the selected lesion boundary).
        """
        report_folder = self.reports_dir / report_id
        report_folder.mkdir(parents=True, exist_ok=True)

        preview_path = report_folder / "preview.png"
        fname_lower = filename.lower()
        is_dicom = (
            fname_lower.endswith(".dcm")
            or fname_lower.endswith(".dicom")
            or image_bytes[:4] == b"DICM"
            or (len(image_bytes) > 132 and image_bytes[128:132] == b"DICM")
        )

        try:
            if is_dicom:
                uint8_arr = dicom_to_uint8(image_bytes)
                img = Image.fromarray(uint8_arr).convert("RGB")
            else:
                img = Image.open(io.BytesIO(image_bytes))
                img = ImageOps.exif_transpose(img)
                if img.mode != "RGB":
                    img = img.convert("RGB")

            # Overlay ROI box if provided
            roi_box = result.get("roi_box")
            if roi_box and len(roi_box) == 4:
                w, h = img.size
                x1, y1, x2, y2 = roi_box
                if max(x1, x2, y1, y2) <= 1.0:
                    x1, x2 = x1 * w, x2 * w
                    y1, y2 = y1 * h, y2 * h
                x1, x2 = sorted([max(0.0, min(float(w - 1), float(x1))), max(0.0, min(float(w - 1), float(x2)))])
                y1, y2 = sorted([max(0.0, min(float(h - 1), float(y1))), max(0.0, min(float(h - 1), float(y2)))])
                
                draw = ImageDraw.Draw(img)
                stroke_w = max(3, int(min(w, h) * 0.005))
                draw.rectangle([x1, y1, x2, y2], outline="#1565C0", width=stroke_w)

            img.save(preview_path, format="PNG")

        except Exception as e:
            logger.error(f"Failed to save preview image for report {report_id}: {e}")
            fallback_img = Image.new("L", (256, 256), color=128)
            fallback_img.save(preview_path, format="PNG")

        # Save result.json
        json_path = report_folder / "result.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        return report_folder

    def get_preview_path(self, report_id: str) -> Optional[Path]:
        img_path = self.reports_dir / report_id / "preview.png"
        if img_path.exists() and img_path.is_file():
            return img_path
        return None

    def get_result(self, report_id: str) -> Optional[Dict[str, Any]]:
        json_path = self.reports_dir / report_id / "result.json"
        if json_path.exists() and json_path.is_file():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading result.json for {report_id}: {e}")
                return None
        return None

    def get_pdf_path(self, report_id: str) -> Optional[Path]:
        pdf_path = self.reports_dir / report_id / "report.pdf"
        if pdf_path.exists() and pdf_path.is_file():
            return pdf_path
        return None

    def cleanup_old_reports(self, ttl_hours: int = settings.REPORT_TTL_HOURS) -> int:
        cutoff_sec = time.time() - (ttl_hours * 3600)
        deleted_count = 0

        if not self.reports_dir.exists():
            return 0

        for folder in self.reports_dir.iterdir():
            if folder.is_dir():
                try:
                    mtime = folder.stat().st_mtime
                    if mtime < cutoff_sec:
                        shutil.rmtree(folder)
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to cleanup report directory {folder}: {e}")

        return deleted_count

storage_service = StorageService()
