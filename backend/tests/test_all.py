"""
MediSense AI - PyTest Automated Test Suite
Covers:
1. System Health (/api/health)
2. Input Validation (invalid file extensions, empty files, corrupt images)
3. Direct Model Prediction Endpoints (/api/predict/{module}) on real clinical samples
4. Asynchronous Job & Real-Event Flow (/api/jobs)
5. Report Generation, Preview Image, and PDF Report Verification
6. Authentication & User Profile Management (register, login, me, password update, avatar)
7. Security & Artifact Ownership Isolation between distinct users
"""

import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from main import app
from db import init_db
from services.model_manager import model_manager

# Ensure DB and models are initialized
init_db()
model_manager.load_all()

client = TestClient(app)
SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


# --------------------------------------------------------------------------
# 1. System Health Tests
# --------------------------------------------------------------------------
def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "modules" in data
    for module_name in ["fracture", "spine", "knee", "chest", "tumor"]:
        assert module_name in data["modules"]
        assert data["modules"][module_name]["loaded"] is True


# --------------------------------------------------------------------------
# 2. Input Validation & Error Handling Tests
# --------------------------------------------------------------------------
def test_invalid_file_extension():
    response = client.post(
        "/api/predict/fracture",
        files={"file": ("test.txt", b"plain text data", "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_empty_file_upload():
    response = client.post(
        "/api/predict/fracture",
        files={"file": ("empty.png", b"", "image/png")}
    )
    assert response.status_code == 400
    assert "The uploaded file is empty" in response.json()["detail"]


def test_corrupt_image_upload():
    response = client.post(
        "/api/predict/fracture",
        files={"file": ("corrupt.png", b"NOT_AN_IMAGE_HEADER_DATA_CORRUPT", "image/png")}
    )
    # Backend catches image parsing error cleanly
    assert response.status_code in (400, 500)
    assert "error" in response.json() or "detail" in response.json()


def test_dicom_on_unsupported_module():
    # Only spine supports DICOM
    dicom_sample = SAMPLES_DIR / "spine" / "spine_normal.dicom"
    if dicom_sample.exists():
        with open(dicom_sample, "rb") as f:
            content = f.read()
        response = client.post(
            "/api/predict/fracture",
            files={"file": ("sample.dcm", content, "application/octet-stream")}
        )
        assert response.status_code == 400
        assert "DICOM format is currently calibrated for the Spine module only" in response.json()["detail"]


# --------------------------------------------------------------------------
# 3. Model Prediction Tests (Valid Schemas & Probabilities)
# --------------------------------------------------------------------------
def test_predict_fracture():
    sample = SAMPLES_DIR / "fracture" / "fractured_01.png"
    assert sample.exists()
    with open(sample, "rb") as f:
        resp = client.post(
            "/api/predict/fracture",
            files={"file": (sample.name, f.read(), "image/png")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "fracture"
    assert data["prediction"] in ("fractured", "not fractured")
    assert 0.0 <= data["confidence"] <= 1.0
    assert "probabilities" in data
    assert 0.0 <= data["probabilities"]["fractured"] <= 1.0
    assert 0.0 <= data["probabilities"]["not fractured"] <= 1.0
    assert abs(sum(data["probabilities"].values()) - 1.0) < 1e-3
    assert "notices" in data


def test_predict_tumor():
    sample = SAMPLES_DIR / "tumor" / "tumor_benign.jpeg"
    assert sample.exists()
    with open(sample, "rb") as f:
        resp = client.post(
            "/api/predict/tumor",
            files={"file": (sample.name, f.read(), "image/jpeg")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "tumor"
    assert data["prediction"] in ("Normal", "Benign", "Malignant")
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["probabilities"]) == 3
    assert abs(sum(data["probabilities"].values()) - 1.0) < 1e-3
    assert any("ROI-cropped" in n for n in data["notices"])


def test_predict_spine_dicom():
    sample = SAMPLES_DIR / "spine" / "spine_abnormal.dicom"
    assert sample.exists()
    with open(sample, "rb") as f:
        resp = client.post(
            "/api/predict/spine",
            files={"file": (sample.name, f.read(), "application/octet-stream")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "spine"
    assert data["prediction"] in ("Normal", "Abnormal")
    assert 0.0 <= data["probability_abnormal"] <= 1.0
    assert data["decision_threshold"] == 0.7574
    assert abs(sum(data["probabilities"].values()) - 1.0) < 1e-3


def test_predict_knee():
    sample = SAMPLES_DIR / "knee" / "knee_KL0.png"
    assert sample.exists()
    with open(sample, "rb") as f:
        resp = client.post(
            "/api/predict/knee",
            files={"file": (sample.name, f.read(), "image/png")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "knee"
    assert data["prediction"] in ("KL-0", "KL-1", "KL-2", "KL-3", "KL-4")
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["top2"]) == 2
    assert "standard kl grade description" in data["reference_description"].lower()


def test_predict_chest():
    sample = SAMPLES_DIR / "chest" / "chest_cardiomegaly.png"
    assert sample.exists()
    with open(sample, "rb") as f:
        resp = client.post(
            "/api/predict/chest",
            files={"file": (sample.name, f.read(), "image/png")}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["module"] == "chest"
    assert len(data["all_probabilities"]) == 14
    for pathology, prob in data["all_probabilities"].items():
        assert 0.0 <= prob <= 1.0
    assert any("uncalibrated 0.5 threshold" in n for n in data["notices"])


# --------------------------------------------------------------------------
# 4. Job Flow & Report Endpoints Tests
# --------------------------------------------------------------------------
def test_job_flow_and_pdf_generation():
    sample = SAMPLES_DIR / "fracture" / "not_fractured_01.png"
    assert sample.exists()
    with open(sample, "rb") as f:
        content = f.read()

    # 1. Create Job
    job_resp = client.post(
        "/api/jobs",
        data={"module": "fracture"},
        files={"file": (sample.name, content, "image/png")}
    )
    assert job_resp.status_code == 202
    job_id = job_resp.json()["job_id"]
    assert job_id.startswith("JOB-")

    # 2. Poll until completed
    import time
    done = False
    final_job = None
    for _ in range(30):
        time.sleep(0.4)
        poll = client.get(f"/api/jobs/{job_id}")
        assert poll.status_code == 200
        final_job = poll.json()
        if final_job["status"] in ("done", "failed"):
            done = True
            break

    assert done is True
    assert final_job["status"] == "done"
    result = final_job["result"]
    report_id = result["report_id"]

    # 3. Retrieve preview image
    img_resp = client.get(f"/api/report/{report_id}/image")
    assert img_resp.status_code == 200
    assert img_resp.headers["content-type"] == "image/png"
    assert len(img_resp.content) > 100

    # 4. Retrieve PDF report
    pdf_resp = client.get(f"/api/report/{report_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
    assert len(pdf_resp.content) > 2000


# --------------------------------------------------------------------------
# 5. Authentication, User Profile, and Security Ownership Tests
# --------------------------------------------------------------------------
def test_auth_workflow_and_artifact_ownership():
    # A. Register User Alpha
    email_a = f"alpha_{pytest.__version__}@test.org".lower()
    reg_a = client.post("/api/auth/register", json={
        "name": "Alpha User",
        "age": 28,
        "sex": "Female",
        "contact": "+1 555 111 2222",
        "email": email_a,
        "password": "PasswordAlpha123!",
    })
    assert reg_a.status_code in (201, 400)

    # Login User Alpha
    login_a = client.post("/api/auth/login", json={
        "email": email_a,
        "password": "PasswordAlpha123!",
    })
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # B. Test GET /api/me
    me_a = client.get("/api/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["email"] == email_a

    # C. Create authenticated Job under User Alpha
    sample = SAMPLES_DIR / "knee" / "knee_KL0.png"
    with open(sample, "rb") as f:
        job_resp = client.post(
            "/api/jobs",
            headers=headers_a,
            data={"module": "knee"},
            files={"file": (sample.name, f.read(), "image/png")}
        )
    assert job_resp.status_code == 202
    job_id = job_resp.json()["job_id"]

    # Poll until done
    import time
    for _ in range(30):
        time.sleep(0.4)
        p = client.get(f"/api/jobs/{job_id}", headers=headers_a)
        if p.json()["status"] == "done":
            report_id = p.json()["result"]["report_id"]
            break

    # D. Register User Beta
    email_b = f"beta_{pytest.__version__}@test.org".lower()
    reg_b = client.post("/api/auth/register", json={
        "name": "Beta User",
        "age": 42,
        "sex": "Male",
        "contact": "+1 555 333 4444",
        "email": email_b,
        "password": "PasswordBeta123!",
    })
    assert reg_b.status_code in (201, 400)
    login_b = client.post("/api/auth/login", json={
        "email": email_b,
        "password": "PasswordBeta123!",
    })
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # E. Verify User Beta CANNOT read User Alpha's job or reports (403 Forbidden)
    assert client.get(f"/api/jobs/{job_id}", headers=headers_b).status_code == 403
    assert client.get(f"/api/report/{report_id}/image", headers=headers_b).status_code == 403
    assert client.get(f"/api/report/{report_id}/pdf", headers=headers_b).status_code == 403

    # F. Verify User Alpha CAN read their own report
    assert client.get(f"/api/report/{report_id}/pdf", headers=headers_a).status_code == 200


# --------------------------------------------------------------------------
# 6. Task A & Task H Verification: Non-Blank PNG & %PDF for All 5 Modules
# --------------------------------------------------------------------------
def test_image_endpoint_valid_nonblank_png_all_modules():
    """
    Verifies Task A: GET /api/report/{id}/image returns a valid, non-blank PNG
    with proper dimensions and non-degenerate extrema for each of the 5 modules.
    """
    module_samples = [
        ("fracture", SAMPLES_DIR / "fracture" / "fractured_01.png"),
        ("spine", SAMPLES_DIR / "spine" / "spine_abnormal.dicom"),
        ("knee", SAMPLES_DIR / "knee" / "knee_KL3.png"),
        ("chest", SAMPLES_DIR / "chest" / "chest_cardiomegaly.png"),
        ("tumor", SAMPLES_DIR / "tumor" / "tumor_benign.jpeg"),
    ]

    for mod, sample_path in module_samples:
        assert sample_path.exists(), f"Sample missing: {sample_path}"
        with open(sample_path, "rb") as f:
            content = f.read()

        # Run direct prediction to create report
        pred_resp = client.post(
            f"/api/predict/{mod}",
            files={"file": (sample_path.name, content, "application/octet-stream")}
        )
        assert pred_resp.status_code == 200, f"Predict failed for {mod}: {pred_resp.text}"
        report_id = pred_resp.json()["report_id"]

        # Fetch image endpoint
        img_resp = client.get(f"/api/report/{report_id}/image")
        assert img_resp.status_code == 200
        assert img_resp.headers["content-type"] == "image/png"
        assert len(img_resp.content) > 1000, f"Image for {mod} too small: {len(img_resp.content)} bytes"

        # Validate with PIL that it is a valid, readable PNG and NOT blank
        img = Image.open(io.BytesIO(img_resp.content))
        assert img.format == "PNG"
        assert img.width > 50 and img.height > 50, f"Invalid dimensions for {mod}: {img.size}"

        # Verify not completely black or completely white
        grayscale = img.convert("L")
        extrema = grayscale.getextrema()
        assert extrema[0] != extrema[1], f"Image for {mod} is completely blank/monochrome: extrema={extrema}"
        assert extrema[1] > 20, f"Image for {mod} is all black: extrema={extrema}"


def test_pdf_endpoint_returns_valid_pdf_all_modules():
    """
    Verifies Task B: GET /api/report/{id}/pdf returns a valid %PDF file with sufficient size.
    """
    module_samples = [
        ("fracture", SAMPLES_DIR / "fracture" / "fractured_02.png"),
        ("spine", SAMPLES_DIR / "spine" / "spine_normal.dicom"),
        ("knee", SAMPLES_DIR / "knee" / "knee_KL0.png"),
        ("chest", SAMPLES_DIR / "chest" / "chest_nofinding.png"),
        ("tumor", SAMPLES_DIR / "tumor" / "tumor_normal.jpeg"),
    ]

    for mod, sample_path in module_samples:
        assert sample_path.exists()
        with open(sample_path, "rb") as f:
            content = f.read()

        pred_resp = client.post(
            f"/api/predict/{mod}",
            files={"file": (sample_path.name, content, "application/octet-stream")}
        )
        assert pred_resp.status_code == 200
        report_id = pred_resp.json()["report_id"]

        pdf_resp = client.get(f"/api/report/{report_id}/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert pdf_resp.content.startswith(b"%PDF")
        assert len(pdf_resp.content) > 5000


# --------------------------------------------------------------------------
# 7. Task C Verification: Tumor ROI Request Validation
# --------------------------------------------------------------------------
def test_tumor_roi_request_validation():
    """
    Verifies Task C: POST /api/jobs and POST /api/predict/tumor with:
    1. Valid bounding box -> analysis_mode="roi_cropped"
    2. Invalid bounding box (malformed, inverted, out of range) -> 400 Bad Request
    3. No bounding box -> analysis_mode="whole_image_no_roi" with prominent caveat notices
    """
    sample = SAMPLES_DIR / "tumor" / "tumor_benign.jpeg"
    assert sample.exists()
    with open(sample, "rb") as f:
        content = f.read()

    # Case 1: Valid ROI Box (JSON format)
    resp_valid = client.post(
        "/api/predict/tumor",
        data={"roi_box": "[0.2, 0.25, 0.75, 0.8]"},
        files={"file": (sample.name, content, "image/jpeg")}
    )
    assert resp_valid.status_code == 200
    data_valid = resp_valid.json()
    assert data_valid["analysis_mode"] == "roi_cropped"
    assert "roi_box" in data_valid
    assert any("ROI-guided" in n for n in data_valid.get("notices", []))

    # Case 2: Invalid ROI Box - Malformed string
    resp_malformed = client.post(
        "/api/predict/tumor",
        data={"roi_box": "not_a_valid_coordinate_list"},
        files={"file": (sample.name, content, "image/jpeg")}
    )
    assert resp_malformed.status_code == 400
    assert "Invalid roi_box" in resp_malformed.json()["detail"]

    # Case 3: Invalid ROI Box - Inverted coordinates (x1 >= x2)
    resp_inverted = client.post(
        "/api/predict/tumor",
        data={"roi_box": "[0.8, 0.2, 0.2, 0.8]"},
        files={"file": (sample.name, content, "image/jpeg")}
    )
    assert resp_inverted.status_code == 400

    # Case 4: Invalid ROI Box - Out of range (negative or > 1)
    resp_negative = client.post(
        "/api/predict/tumor",
        data={"roi_box": "[-0.1, 0.2, 0.5, 0.8]"},
        files={"file": (sample.name, content, "image/jpeg")}
    )
    assert resp_negative.status_code == 400

    # Case 5: No ROI Box (Whole image mode)
    resp_no_box = client.post(
        "/api/predict/tumor",
        files={"file": (sample.name, content, "image/jpeg")}
    )
    assert resp_no_box.status_code == 200
    data_no_box = resp_no_box.json()
    assert data_no_box["analysis_mode"] == "whole_image_no_roi"
    # Prominent caveat notices must be present
    notices = data_no_box.get("notices", [])
    assert any("training setup" in n.lower() for n in notices)
    assert any("not a screening result" in n.lower() for n in notices)

