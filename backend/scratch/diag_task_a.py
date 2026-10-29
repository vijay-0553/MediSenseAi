"""
Task A Reproduction & Diagnostics Script
Inspects GET /api/report/{id}/image and PDF generation for all 5 modules using real samples.
"""
import io
import sys
from pathlib import Path
from PIL import Image
import pypdf

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.model_manager import model_manager

def run_diagnostics():
    print("=" * 80)
    print("TASK A: REPRODUCING RADIOGRAPH DISPLAY BEHAVIOR ACROSS 5 MODULES")
    print("=" * 80)

    model_manager.load_all()
    client = TestClient(app)

    # 1. Register and Login to get a valid JWT
    user_email = "radiology_qa@medisense.ai"
    reg_resp = client.post("/api/auth/register", json={
        "email": user_email,
        "password": "Password123!",
        "name": "Dr. Reproduction QA",
        "age": 42,
        "sex": "Female",
        "contact": "+1-555-0144"
    })
    if reg_resp.status_code == 201:
        token = reg_resp.json()["access_token"]
    else:
        login_resp = client.post("/api/auth/login", json={
            "email": user_email,
            "password": "Password123!"
        })
        token = login_resp.json()["access_token"]

    auth_headers = {"Authorization": f"Bearer {token}"}

    samples = [
        ("fracture", backend_dir / "samples" / "fracture" / "fractured_01.png"),
        ("tumor", backend_dir / "samples" / "tumor" / "tumor_benign.jpeg"),
        ("spine", backend_dir / "samples" / "spine" / "spine_abnormal.dicom"),
        ("knee", backend_dir / "samples" / "knee" / "knee_KL0.png"),
        ("chest", backend_dir / "samples" / "chest" / "chest_cardiomegaly.png"),
    ]

    for module, sample_path in samples:
        print(f"\n[{module.upper()}] Sample: {sample_path.name} ({sample_path.stat().st_size} bytes)")
        
        # Upload to /api/jobs with auth
        with open(sample_path, "rb") as f:
            file_bytes = f.read()

        job_resp = client.post(
            "/api/jobs",
            data={"module": module},
            files={"file": (sample_path.name, file_bytes, "application/octet-stream")},
            headers=auth_headers
        )
        assert job_resp.status_code == 202, f"Failed job submit: {job_resp.text}"
        job_id = job_resp.json()["job_id"]

        # Poll
        import time
        for _ in range(60):
            status_resp = client.get(f"/api/jobs/{job_id}", headers=auth_headers)
            status_data = status_resp.json()
            if status_data["status"] in ("done", "failed"):
                break
            time.sleep(0.5)

        assert status_data["status"] == "done", f"Job failed: {status_data}"
        report_id = status_data["result"]["report_id"]
        print(f"  Job complete. Report ID: {report_id}")

        # Check Unauthenticated Image Fetch (as standard browser <img src="..."> would do)
        no_auth_resp = client.get(f"/api/report/{report_id}/image")
        print(f"  Unauthenticated fetch: HTTP {no_auth_resp.status_code} ({no_auth_resp.text})")

        # Check Authenticated Image Fetch
        auth_img_resp = client.get(f"/api/report/{report_id}/image", headers=auth_headers)
        print(f"  Authenticated fetch: HTTP {auth_img_resp.status_code}, Content-Type: {auth_img_resp.headers.get('content-type')}, Size: {len(auth_img_resp.content)} bytes")
        
        # Analyze the received image bytes
        img = Image.open(io.BytesIO(auth_img_resp.content))
        print(f"  Image details: Format: {img.format}, Mode: {img.mode}, Dimensions: {img.size}")
        
        # Check pixel stats (to confirm not blank/all zero)
        import numpy as np
        arr = np.array(img)
        print(f"  Pixel stats: Min: {arr.min()}, Max: {arr.max()}, Mean: {arr.mean():.2f}, Dtype: {arr.dtype}")

        # Save copy to inspect
        diag_path = backend_dir / "storage" / "reports" / f"diag_{module}.png"
        img.save(diag_path)
        print(f"  Saved inspection PNG to: {diag_path}")

        # Check PDF size and radiograph presence
        pdf_path = backend_dir / "storage" / "reports" / report_id / "report.pdf"
        print(f"  PDF file exists: {pdf_path.exists()}, Size: {pdf_path.stat().st_size if pdf_path.exists() else 0} bytes")

if __name__ == "__main__":
    run_diagnostics()
