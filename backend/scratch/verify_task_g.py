"""
Security Verification Script for Task G
Tests:
(a) Server refuses to start with missing or default JWT_SECRET
(b) 401 Unauthorized on protected endpoints without token
(c) Multi-tenant isolation: User B gets 403 on User A's job, image, and PDF
(d) Image endpoint requires authorization (or token) and rejects unauthorized calls
"""
import os
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.model_manager import model_manager

def run_security_checks():
    print("=" * 80)
    print("TASK G: SECURITY AND AUTHORIZATION VERIFICATION")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # (a) Refuse to start with missing or default JWT_SECRET
    # -------------------------------------------------------------------------
    print("\n--- (a) Testing Startup Rejection on Missing/Default JWT_SECRET ---")
    
    # Test missing JWT_SECRET
    env_missing = os.environ.copy()
    env_missing["JWT_SECRET"] = ""
    cmd = [sys.executable, "-c", "from config import settings"]
    proc_missing = subprocess.run(cmd, cwd=str(backend_dir), env=env_missing, capture_output=True, text=True)
    print(f"Empty JWT_SECRET exit code: {proc_missing.returncode}")
    print(f"Error output snippet:\n{proc_missing.stderr[-250:].strip()}")
    assert proc_missing.returncode != 0
    assert "Application startup refused: JWT_SECRET is missing" in proc_missing.stderr
    print(">>> PASS: Refused to start with empty JWT_SECRET.")

    # Test default placeholder JWT_SECRET
    env_default = os.environ.copy()
    env_default["JWT_SECRET"] = "your_secure_random_jwt_secret_here"
    proc_default = subprocess.run(cmd, cwd=str(backend_dir), env=env_default, capture_output=True, text=True)
    print(f"\nDefault placeholder JWT_SECRET exit code: {proc_default.returncode}")
    print(f"Error output snippet:\n{proc_default.stderr[-250:].strip()}")
    assert proc_default.returncode != 0
    assert "Application startup refused: JWT_SECRET is missing or using default" in proc_default.stderr
    print(">>> PASS: Refused to start with default placeholder JWT_SECRET.")

    # -------------------------------------------------------------------------
    # (b) Unauthenticated requests get 401 on /api/me
    # -------------------------------------------------------------------------
    print("\n--- (b) Testing Unauthenticated Requests (401 Unauthorized) ---")
    client = TestClient(app)

    me_resp = client.get("/api/me")
    print(f"GET /api/me without token: HTTP {me_resp.status_code} ({me_resp.json()})")
    assert me_resp.status_code == 401
    print(">>> PASS: /api/me correctly rejects unauthenticated calls with 401.")

    # -------------------------------------------------------------------------
    # (c) Multi-Tenant Access Control & Ownership Isolation
    # -------------------------------------------------------------------------
    print("\n--- (c) Multi-Tenant Isolation: User B Cannot Access User A's Artifacts ---")
    model_manager.load_all()
    
    # Register User A with unique email
    import time
    ts = int(time.time())
    user_a_email = f"user_a_{ts}@hospital.org"
    reg_a = client.post("/api/auth/register", json={
        "email": user_a_email,
        "password": "Password123!",
        "name": "Dr. Alice UserA",
        "age": 38,
        "sex": "Female",
        "contact": "+1-555-0101"
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register User B with unique email
    user_b_email = f"user_b_{ts}@hospital.org"
    reg_b = client.post("/api/auth/register", json={
        "email": user_b_email,
        "password": "Password123!",
        "name": "Dr. Bob UserB",
        "age": 45,
        "sex": "Male",
        "contact": "+1-555-0102"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A submits a job
    sample_file = backend_dir / "samples" / "knee" / "knee_KL0.png"
    with open(sample_file, "rb") as f:
        file_bytes = f.read()

    job_resp = client.post(
        "/api/jobs",
        data={"module": "knee"},
        files={"file": ("knee_KL0.png", file_bytes, "image/png")},
        headers=headers_a
    )
    job_id = job_resp.json()["job_id"]

    # Poll until done
    import time
    for _ in range(40):
        status_resp = client.get(f"/api/jobs/{job_id}", headers=headers_a)
        if status_resp.json()["status"] in ("done", "failed"):
            break
        time.sleep(0.5)

    assert status_resp.json()["status"] == "done"
    report_id = status_resp.json()["result"]["report_id"]
    print(f"User A created Job: {job_id}, Report: {report_id}")

    # User B attempts to access User A's job
    job_b_resp = client.get(f"/api/jobs/{job_id}", headers=headers_b)
    print(f"User B accessing User A's Job: HTTP {job_b_resp.status_code} ({job_b_resp.json()})")
    assert job_b_resp.status_code == 403
    print(">>> PASS: User B blocked from accessing User A's job with 403 Forbidden.")

    # User B attempts to access User A's report image
    img_b_resp = client.get(f"/api/report/{report_id}/image", headers=headers_b)
    print(f"User B accessing User A's Image: HTTP {img_b_resp.status_code} ({img_b_resp.json()})")
    assert img_b_resp.status_code == 403
    print(">>> PASS: User B blocked from accessing User A's report image with 403 Forbidden.")

    # User B attempts to access User A's report PDF
    pdf_b_resp = client.get(f"/api/report/{report_id}/pdf", headers=headers_b)
    print(f"User B accessing User A's PDF: HTTP {pdf_b_resp.status_code} ({pdf_b_resp.json()})")
    assert pdf_b_resp.status_code == 403
    print(">>> PASS: User B blocked from accessing User A's report PDF with 403 Forbidden.")

    # -------------------------------------------------------------------------
    # (d) Image endpoint behavior (auth header vs no auth)
    # -------------------------------------------------------------------------
    print("\n--- (d) Testing Image Endpoint Authorization ---")
    img_no_auth = client.get(f"/api/report/{report_id}/image")
    print(f"Image fetch WITHOUT auth: HTTP {img_no_auth.status_code} ({img_no_auth.json()})")
    assert img_no_auth.status_code == 403

    img_with_auth = client.get(f"/api/report/{report_id}/image", headers=headers_a)
    print(f"Image fetch WITH User A auth: HTTP {img_with_auth.status_code}, Content-Type: {img_with_auth.headers.get('content-type')}, Size: {len(img_with_auth.content)} bytes")
    assert img_with_auth.status_code == 200
    assert img_with_auth.headers.get("content-type") == "image/png"
    print(">>> PASS: Image endpoint strictly enforces authorization.")

    print("\nALL TASK G SECURITY CHECKS PASSED SUCCESSFULLY.")

if __name__ == "__main__":
    run_security_checks()
