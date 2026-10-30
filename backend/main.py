import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image
from sqlalchemy.orm import Session

from config import settings
from db import Base, engine, get_db
from db_models import User
from inference.chest import predict_chest
from inference.fracture import predict_fracture
from inference.knee import predict_knee
from inference.spine import predict_spine
from inference.tumor import predict_tumor
from reports.pdf_builder import build_report_pdf
from schemas import (
    AuthResponse,
    UserLogin,
    UserPasswordUpdate,
    UserRegister,
    UserResponse,
    UserUpdate,
)
from services.auth import (
    check_login_rate_limit,
    clear_failed_logins,
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    record_failed_login,
    verify_password,
)
from services.job_manager import job_manager
from services.model_manager import model_manager
from services.storage import storage_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("medisense.api")

async def periodic_cleanup():
    """Background task to clean up expired reports and jobs periodically."""
    while True:
        try:
            await asyncio.sleep(3600)  # hourly
            deleted = storage_service.cleanup_old_reports(settings.REPORT_TTL_HOURS)
            job_manager.cleanup_old_jobs(3600 * 24)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired report directories.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Error in periodic cleanup task: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MediSense AI backend service...")
    # Initialize SQLite database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized.")
    # Load all models and warm them up
    await asyncio.to_thread(model_manager.load_all)
    logger.info("All model loaders and warmups executed.")
    cleanup_task = asyncio.create_task(periodic_cleanup())
    yield
    cleanup_task.cancel()
    logger.info("Shutting down MediSense AI backend service.")

app = FastAPI(
    title="MediSense AI API",
    description="Multi-Module Deep Learning Medical Imaging Analysis API with Authentication",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".dcm", ".dicom"}
VALID_MODULES = {"fracture", "tumor", "spine", "knee", "chest"}

def validate_upload(module: str, filename: str, content: bytes):
    normalized_module = module.strip().lower()
    if normalized_module not in VALID_MODULES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown module '{module}'. Valid modules are: {', '.join(sorted(VALID_MODULES))}"
        )

    sanitized_filename = filename.replace("\\", "/").split("/")[-1]
    ext = "." + sanitized_filename.split(".")[-1].lower() if "." in sanitized_filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed formats are JPG, JPEG, PNG, and DICOM (.dcm, .dicom)."
        )

    if ext in {".dcm", ".dicom"} and normalized_module != "spine":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DICOM format is currently calibrated for the Spine module only. Please upload JPG or PNG for {module}."
        )

    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty."
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB limit."
        )

def user_to_response(user: User) -> UserResponse:
    avatar_url = f"/api/me/avatar" if user.avatar_filename else None
    return UserResponse(
        id=user.id,
        name=user.name,
        age=user.age,
        sex=user.sex,
        contact=user.contact,
        email=user.email,
        avatar_url=avatar_url,
        created_at=user.created_at,
    )


# -------------------------------------------------------------
# 1. Health & Root Endpoints
# -------------------------------------------------------------
@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "MediSense AI Backend",
        "status": "online",
        "docs": "/docs",
        "health": "/api/health",
        "version": "1.0.0",
    }

@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """
    Returns real per-model status (loaded / failed + reason) and server environment.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": str(model_manager.device),
        "modules": model_manager.get_status()["modules"],
    }


# -------------------------------------------------------------
# 2. Authentication & User Profile Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(req: UserRegister, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    user = User(
        name=req.name.strip(),
        age=req.age,
        sex=req.sex.strip(),
        contact=req.contact.strip(),
        email=clean_email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(access_token=token, user=user_to_response(user))


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(req: UserLogin, db: Session = Depends(get_db)):
    clean_email = req.email.strip().lower()
    check_login_rate_limit(clean_email)

    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(req.password, user.password_hash):
        record_failed_login(clean_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    clear_failed_logins(clean_email)
    token = create_access_token({"sub": user.id, "email": user.email})
    return AuthResponse(access_token=token, user=user_to_response(user))


@app.get("/api/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return user_to_response(current_user)


@app.put("/api/me", response_model=UserResponse)
async def update_me(
    req: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if req.email:
        clean_email = req.email.strip().lower()
        if clean_email != current_user.email:
            existing = db.query(User).filter(User.email == clean_email).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This email address is already in use by another account."
                )
            current_user.email = clean_email

    if req.name is not None:
        current_user.name = req.name.strip()
    if req.age is not None:
        current_user.age = req.age
    if req.sex is not None:
        current_user.sex = req.sex.strip()
    if req.contact is not None:
        current_user.contact = req.contact.strip()

    db.commit()
    db.refresh(current_user)
    return user_to_response(current_user)


@app.put("/api/me/password")
async def update_password(
    req: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(req.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    if len(req.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long."
        )

    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@app.post("/api/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    raw_filename = file.filename or "avatar.png"
    ext = "." + raw_filename.split(".")[-1].lower() if "." in raw_filename else ".png"
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Avatar must be a valid image (JPG, PNG, WebP)."
        )

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar image size must be under 5 MB."
        )

    avatar_filename = f"{current_user.id}{ext}"
    avatar_path = settings.AVATARS_DIR / avatar_filename

    try:
        # Validate that content is readable as image
        import io
        img = Image.open(io.BytesIO(content))
        img.verify()
        with open(avatar_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save avatar image: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image."
        )

    current_user.avatar_filename = avatar_filename
    db.commit()
    db.refresh(current_user)
    return user_to_response(current_user)


@app.get("/api/me/avatar")
async def get_avatar(current_user: User = Depends(get_current_user)):
    if not current_user.avatar_filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No avatar set.")
    avatar_path = settings.AVATARS_DIR / current_user.avatar_filename
    if not avatar_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file missing.")
    return FileResponse(avatar_path)


# -------------------------------------------------------------
# 3. Asynchronous Job Flow
# -------------------------------------------------------------
@app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    module: str = Form(...),
    file: UploadFile = File(...),
    roi_box: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_optional_user)
) -> Dict[str, Any]:
    """
    Create an asynchronous analysis job.
    Returns 202 Accepted with job_id immediately so progress bar is driven by real events.
    """
    raw_filename = file.filename or "uploaded_xray"
    sanitized_filename = raw_filename.replace("\\", "/").split("/")[-1]

    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file for job: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content."
        )

    validate_upload(module, sanitized_filename, content)
    normalized_module = module.strip().lower()

    # Parse and validate roi_box if provided
    parsed_roi = None
    if roi_box and roi_box.strip():
        try:
            val_str = roi_box.strip()
            if val_str.startswith("[") and val_str.endswith("]"):
                import json
                parsed_roi = [float(v) for v in json.loads(val_str)]
            else:
                parsed_roi = [float(v.strip()) for v in val_str.split(",")]
            if len(parsed_roi) != 4:
                raise ValueError()
            x1, y1, x2, y2 = parsed_roi
            if not (0.0 <= x1 < x2 and 0.0 <= y1 < y2):
                raise ValueError()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid roi_box format. Must provide [x1, y1, x2, y2] with x1 < x2 and y1 < y2."
            )

    # Populate patient info from authenticated user if available
    patient_info = None
    user_id = None
    if current_user:
        user_id = current_user.id
        patient_info = {
            "name": current_user.name,
            "age": current_user.age,
            "sex": current_user.sex,
            "contact": current_user.contact,
        }

    job_id = job_manager.create_job(
        module=normalized_module,
        filename=sanitized_filename,
        content=content,
        user_id=user_id,
        patient_info=patient_info,
        roi_box=parsed_roi,
    )

    return {
        "job_id": job_id,
        "status": "received",
    }


@app.get("/api/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    current_user: Optional[User] = Depends(get_optional_user)
) -> Dict[str, Any]:
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found or expired."
        )

    # Ownership check: if job has user_id, ensure caller matches
    if job.get("user_id"):
        if not current_user or current_user.id != job["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not own this analysis job."
            )

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "progress_stage": job["progress_stage"],
        "result": job.get("result"),
        "error": job.get("error"),
    }


# -------------------------------------------------------------
# 4. Report Artifact Endpoints
# -------------------------------------------------------------
@app.get("/api/report/{report_id}/image")
async def get_report_image(
    report_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    user = current_user
    if not user and token:
        try:
            payload = decode_access_token(token)
            uid = payload.get("sub")
            if uid:
                user = db.query(User).filter(User.id == uid).first()
        except Exception:
            pass

    if report_id.startswith("JOB-"):
        job = job_manager.get_job(report_id)
        if job and job.get("result") and job["result"].get("report_id"):
            report_id = job["result"]["report_id"]

    result = storage_service.get_result(report_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found."
        )

    # Check ownership if report is bound to a user
    if result.get("user_id"):
        if not user or user.id != result["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to view this report."
            )

    preview_path = storage_service.get_preview_path(report_id)
    if not preview_path or not preview_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Preview image for report '{report_id}' not found."
        )

    return FileResponse(
        path=preview_path,
        media_type="image/png",
        filename=f"preview_{report_id}.png"
    )


@app.get("/api/report/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    user = current_user
    if not user and token:
        try:
            payload = decode_access_token(token)
            uid = payload.get("sub")
            if uid:
                user = db.query(User).filter(User.id == uid).first()
        except Exception:
            pass

    if report_id.startswith("JOB-"):
        job = job_manager.get_job(report_id)
        if job and job.get("result") and job["result"].get("report_id"):
            report_id = job["result"]["report_id"]

    result = storage_service.get_result(report_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found."
        )

    # Check ownership if report is bound to a user
    if result.get("user_id"):
        if not user or user.id != result["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You do not have permission to download this report."
            )

    pdf_path = storage_service.get_pdf_path(report_id)
    if not pdf_path or not pdf_path.exists():
        preview_path = storage_service.get_preview_path(report_id)
        patient_info = None
        if user:
            patient_info = {
                "name": user.name,
                "age": user.age,
                "sex": user.sex,
                "contact": user.contact,
            }
        built_path = build_report_pdf(
            result=result,
            patient=patient_info,
            image_path=str(preview_path) if preview_path else None
        )
        pdf_path = Path(built_path)

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="MediSense_Report_{report_id}.pdf"'
        }
    )


# -------------------------------------------------------------
# 5. Direct Predict Endpoint (Used by Tests / Direct Clients)
# -------------------------------------------------------------
@app.post("/api/predict/{module}")
async def predict_module(
    module: str,
    file: UploadFile = File(...),
    roi_box: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_optional_user)
) -> Dict[str, Any]:
    raw_filename = file.filename or "uploaded_xray"
    sanitized_filename = raw_filename.replace("\\", "/").split("/")[-1]

    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not read uploaded file content."
        )

    validate_upload(module, sanitized_filename, content)
    normalized_module = module.strip().lower()

    parsed_roi = None
    if roi_box and roi_box.strip():
        try:
            val_str = roi_box.strip()
            if val_str.startswith("[") and val_str.endswith("]"):
                import json
                parsed_roi = [float(v) for v in json.loads(val_str)]
            else:
                parsed_roi = [float(v.strip()) for v in val_str.split(",")]
            if len(parsed_roi) != 4:
                raise ValueError()
            x1, y1, x2, y2 = parsed_roi
            if not (0.0 <= x1 < x2 and 0.0 <= y1 < y2):
                raise ValueError()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid roi_box format."
            )

    report_id = f"RPT-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    try:
        # Offload synchronous ML model inference to threadpool
        if normalized_module == "fracture":
            result = await asyncio.to_thread(predict_fracture, content)
        elif normalized_module == "spine":
            result = await asyncio.to_thread(predict_spine, content, filename=sanitized_filename)
        elif normalized_module == "knee":
            result = await asyncio.to_thread(predict_knee, content)
        elif normalized_module == "chest":
            result = await asyncio.to_thread(predict_chest, content)
        elif normalized_module == "tumor":
            result = await asyncio.to_thread(predict_tumor, content, bbox=parsed_roi)
        else:
            raise HTTPException(status_code=400, detail="Invalid module")

        result["report_id"] = report_id
        result["timestamp"] = timestamp
        result["filename"] = sanitized_filename
        if current_user:
            result["user_id"] = current_user.id

        patient_info = None
        if current_user:
            patient_info = {
                "name": current_user.name,
                "age": current_user.age,
                "sex": current_user.sex,
                "contact": current_user.contact,
            }

        # Save to storage
        storage_service.save_prediction(
            report_id=report_id,
            result=result,
            image_bytes=content,
            filename=sanitized_filename,
        )

        # Generate PDF report
        preview_path = storage_service.get_preview_path(report_id)
        build_report_pdf(
            result=result,
            patient=patient_info,
            image_path=str(preview_path) if preview_path else None,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Inference error on module '{module}': {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Inference failed",
                "detail": f"An error occurred while processing the X-ray for module '{module}': {str(e)}",
                "report_id": report_id,
                "timestamp": timestamp,
            }
        )
