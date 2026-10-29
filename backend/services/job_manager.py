import concurrent.futures
from datetime import datetime, timezone
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from inference.chest import predict_chest
from inference.fracture import predict_fracture
from inference.knee import predict_knee
from inference.spine import predict_spine
from inference.tumor import predict_tumor
from reports.pdf_builder import build_report_pdf
from services.storage import storage_service

logger = logging.getLogger("medisense.jobs")

class JobManager:
    """
    Asynchronous job manager executing model inference and PDF report generation
    in background worker threads, freeing the FastAPI async event loop.
    """
    def __init__(self, max_workers: int = 4):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="medisense-job-worker"
        )

    def cleanup_old_jobs(self, max_age_seconds: int = 3600 * 24):
        now = time.time()
        expired = [
            jid for jid, job in self.jobs.items()
            if now - job.get("created_at", now) > max_age_seconds
        ]
        for jid in expired:
            del self.jobs[jid]

    def create_job(
        self,
        module: str,
        filename: str,
        content: bytes,
        user_id: Optional[str] = None,
        patient_info: Optional[Dict[str, Any]] = None,
        roi_box: Optional[List[float]] = None,
    ) -> str:
        self.cleanup_old_jobs()
        job_id = f"JOB-{uuid.uuid4().hex[:12].upper()}"
        
        self.jobs[job_id] = {
            "job_id": job_id,
            "user_id": user_id,
            "patient_info": patient_info,
            "module": module,
            "filename": filename,
            "roi_box": roi_box,
            "status": "received",
            "progress_stage": 2,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        # Submit task to the worker pool off the event loop
        self.executor.submit(
            self._process_job_worker,
            job_id=job_id,
            module=module,
            filename=filename,
            content=content,
            user_id=user_id,
            patient_info=patient_info,
            roi_box=roi_box,
        )
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def _process_job_worker(
        self,
        job_id: str,
        module: str,
        filename: str,
        content: bytes,
        user_id: Optional[str] = None,
        patient_info: Optional[Dict[str, Any]] = None,
        roi_box: Optional[List[float]] = None,
    ):
        try:
            job = self.jobs.get(job_id)
            if not job:
                return

            # 1. Update status to analyzing (Stage 3)
            job["status"] = "analyzing"
            job["progress_stage"] = 3
            job["updated_at"] = time.time()

            report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
            timestamp = datetime.now(timezone.utc).isoformat()

            # 2. Run model inference guarded by per-model locks
            normalized_module = module.strip().lower()
            if normalized_module == "fracture":
                result = predict_fracture(content)
            elif normalized_module == "spine":
                result = predict_spine(content, filename=filename)
            elif normalized_module == "knee":
                result = predict_knee(content)
            elif normalized_module == "chest":
                result = predict_chest(content)
            elif normalized_module == "tumor":
                result = predict_tumor(content, bbox=roi_box)
            else:
                raise ValueError(f"Unknown module '{module}'")

            result["report_id"] = report_id
            result["timestamp"] = timestamp
            result["filename"] = filename
            if user_id:
                result["user_id"] = user_id
            if roi_box:
                result["roi_box"] = roi_box

            # 3. Persist prediction result & preview.png
            storage_service.save_prediction(
                report_id=report_id,
                result=result,
                image_bytes=content,
                filename=filename,
            )

            # 4. Update status to generating_report (Stage 4)
            job["status"] = "generating_report"
            job["progress_stage"] = 4
            job["updated_at"] = time.time()

            # 5. Generate PDF report
            preview_path = storage_service.get_preview_path(report_id)
            build_report_pdf(
                result=result,
                patient=patient_info,
                image_path=str(preview_path) if preview_path else None,
            )

            # 6. Mark job complete (Stage 5)
            job["status"] = "done"
            job["progress_stage"] = 5
            job["result"] = result
            job["updated_at"] = time.time()
            logger.info(f"Job {job_id} successfully completed for module '{module}'. Report ID: {report_id}")

        except Exception as e:
            logger.exception(f"Execution error for job {job_id} on module '{module}': {e}")
            job = self.jobs.get(job_id)
            if job:
                job["status"] = "failed"
                job["error"] = f"Analysis failed: {str(e)}"
                job["updated_at"] = time.time()

job_manager = JobManager()
