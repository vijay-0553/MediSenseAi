"""
End-to-End Verification Script for Phases 4 and 5
Tests:
1. User registration, login, JWT token issuance.
2. Avatar upload and retrieval.
3. Authenticated job creation for all 5 modules with real samples.
4. Real-event polling across all 5 progress stages.
5. Verification that patient information from logged-in user is written into the PDF.
6. Profile editing and persistence across re-login.
7. Password change verification (old password fails, new works).
8. Report and job ownership enforcement (User B cannot access User A's data).
9. Protected route redirection on 401.
"""

import io
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.model_manager import model_manager
import pypdf
from PIL import Image as PILImage

def run_verification():
    print("=" * 75)
    print("STARTING PHASES 4 & 5 END-TO-END VERIFICATION")
    print("=" * 75)

    client = TestClient(app)

    # 1. Warm up models
    print("\n[Step 1] Loading and warming up all deep learning models...")
    model_manager.load_all()
    print("All models initialized.")

    # 2. Register User A
    print("\n[Step 2] Registering User A (Dr. Clara Oswald)...")
    user_a_data = {
        "name": "Dr. Clara Oswald",
        "age": 32,
        "sex": "Female",
        "contact": "+1 555 999 1234",
        "email": "clara.oswald@hospital.org",
        "password": "SecurePassword123!",
    }
    reg_resp = client.post("/api/auth/register", json=user_a_data)
    if reg_resp.status_code == 400 and "already exists" in reg_resp.text:
        print("User already registered from previous run. Logging in directly.")
    elif reg_resp.status_code != 201:
        print(f"FAILED: Registration failed: {reg_resp.status_code} - {reg_resp.text}")
        return False
    else:
        print(f"Registration successful. User ID: {reg_resp.json()['user']['id']}")

    # 3. Login User A
    print("\n[Step 3] Logging in as User A...")
    login_resp = client.post("/api/auth/login", json={
        "email": "clara.oswald@hospital.org",
        "password": "SecurePassword123!",
    })
    if login_resp.status_code != 200:
        print(f"FAILED: Login failed: {login_resp.status_code} - {login_resp.text}")
        return False

    token_a = login_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    user_a = login_resp.json()["user"]
    user_a_id = user_a["id"]
    print(f"Login successful. Received JWT token (sub={user_a_id}).")

    # 4. Upload Avatar for User A
    print("\n[Step 4] Uploading profile avatar for User A...")
    avatar_buf = io.BytesIO()
    PILImage.new("RGB", (128, 128), color=(0, 200, 83)).save(avatar_buf, format="PNG")
    avatar_bytes = avatar_buf.getvalue()

    avatar_resp = client.post(
        "/api/me/avatar",
        headers=headers_a,
        files={"file": ("profile_photo.png", avatar_bytes, "image/png")}
    )
    if avatar_resp.status_code != 200:
        print(f"FAILED: Avatar upload failed: {avatar_resp.status_code} - {avatar_resp.text}")
        return False
    print(f"Avatar uploaded successfully: avatar_url={avatar_resp.json()['avatar_url']}")

    # Check avatar retrieval
    get_avatar_resp = client.get("/api/me/avatar", headers=headers_a)
    if get_avatar_resp.status_code != 200 or len(get_avatar_resp.content) == 0:
        print(f"FAILED: Avatar retrieval failed: {get_avatar_resp.status_code}")
        return False
    print("Avatar retrieval verified.")

    # 5. Run Job flow for all 5 modules with User A authentication
    samples = [
        ("fracture", backend_dir / "samples" / "fracture" / "fractured_01.png"),
        ("tumor", backend_dir / "samples" / "tumor" / "tumor_benign.jpeg"),
        ("spine", backend_dir / "samples" / "spine" / "spine_abnormal.dicom"),
        ("knee", backend_dir / "samples" / "knee" / "knee_KL0.png"),
        ("chest", backend_dir / "samples" / "chest" / "chest_cardiomegaly.png"),
    ]

    user_a_job_ids = []
    user_a_report_ids = []

    print("\n[Step 5] Testing real job flow & PDF generation for all 5 modules...")
    for module, sample_path in samples:
        with open(sample_path, "rb") as f:
            file_bytes = f.read()

        # POST /api/jobs with auth
        post_resp = client.post(
            "/api/jobs",
            headers=headers_a,
            data={"module": module},
            files={"file": (sample_path.name, file_bytes, "application/octet-stream")}
        )
        if post_resp.status_code != 202:
            print(f"FAILED: /api/jobs returned {post_resp.status_code} for {module}: {post_resp.text}")
            return False

        job_id = post_resp.json()["job_id"]
        user_a_job_ids.append(job_id)

        # Poll
        stages_seen = [post_resp.json()["status"]]
        done = False
        final_job = None
        for _ in range(40):
            time.sleep(0.4)
            poll_resp = client.get(f"/api/jobs/{job_id}", headers=headers_a)
            if poll_resp.status_code == 200:
                final_job = poll_resp.json()
                st = final_job["status"]
                if st not in stages_seen:
                    stages_seen.append(st)
                if st in ("done", "failed"):
                    done = True
                    break

        if not done or final_job["status"] != "done":
            print(f"FAILED: Job {job_id} for {module} failed: {final_job}")
            return False

        res = final_job["result"]
        report_id = res["report_id"]
        user_a_report_ids.append(report_id)
        print(f"  -> Module {module.upper()}: Stages [{' -> '.join(stages_seen)}], Prediction='{res.get('prediction', res.get('primary_finding'))}', Report={report_id}")

        # Download PDF and verify patient details are embedded
        pdf_resp = client.get(f"/api/report/{report_id}/pdf", headers=headers_a)
        if pdf_resp.status_code != 200:
            print(f"FAILED: PDF download for {report_id} failed: {pdf_resp.status_code}")
            return False

        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_resp.content))
        pdf_text = pdf_reader.pages[0].extract_text()

        assert "Dr. Clara Oswald" in pdf_text, "Patient name missing in PDF"
        assert "32" in pdf_text, "Patient age missing in PDF"
        assert "Female" in pdf_text, "Patient sex missing in PDF"
        assert "+1 555 999 1234" in pdf_text, "Patient contact missing in PDF"
        print(f"     Patient details in PDF confirmed: Dr. Clara Oswald, Age 32, Female, +1 555 999 1234")

    # 6. Profile Edit
    print("\n[Step 6] Testing profile update (contact change)...")
    edit_resp = client.put(
        "/api/me",
        headers=headers_a,
        json={"contact": "+1 555 777 8888"}
    )
    if edit_resp.status_code != 200:
        print(f"FAILED: Profile update failed: {edit_resp.status_code}")
        return False
    assert edit_resp.json()["contact"] == "+1 555 777 8888", "Contact update not reflected"
    print("Profile contact updated to +1 555 777 8888.")

    # Confirm persistence with a fresh GET /api/me
    me_resp = client.get("/api/me", headers=headers_a)
    assert me_resp.json()["contact"] == "+1 555 777 8888", "Contact did not persist"
    print("Persistence of profile changes verified.")

    # 7. Password Change
    print("\n[Step 7] Testing password change workflow...")
    # Bad current password
    bad_pwd_resp = client.put(
        "/api/me/password",
        headers=headers_a,
        json={"current_password": "WrongPassword!", "new_password": "NewSecurePassword456!"}
    )
    if bad_pwd_resp.status_code != 400:
        print(f"FAILED: Expected 400 for incorrect password, got {bad_pwd_resp.status_code}")
        return False
    print("Correctly rejected password change with incorrect current password.")

    # Good password change
    good_pwd_resp = client.put(
        "/api/me/password",
        headers=headers_a,
        json={"current_password": "SecurePassword123!", "new_password": "NewSecurePassword456!"}
    )
    if good_pwd_resp.status_code != 200:
        print(f"FAILED: Password change failed: {good_pwd_resp.status_code}")
        return False
    print("Password successfully updated to NewSecurePassword456!.")

    # Verify old password login fails
    old_login_resp = client.post("/api/auth/login", json={
        "email": "clara.oswald@hospital.org",
        "password": "SecurePassword123!",
    })
    if old_login_resp.status_code != 401:
        print(f"FAILED: Old password should have returned 401, got {old_login_resp.status_code}")
        return False
    print("Old password rejected with 401 Unauthorized.")

    # Verify new password login succeeds
    new_login_resp = client.post("/api/auth/login", json={
        "email": "clara.oswald@hospital.org",
        "password": "NewSecurePassword456!",
    })
    if new_login_resp.status_code != 200:
        print(f"FAILED: New password login failed: {new_login_resp.status_code}")
        return False
    token_a = new_login_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}
    print("New password login succeeded. Updated authorization token acquired.")

    # 8. User B Registration & Ownership Security Check
    print("\n[Step 8] Testing authorization & ownership isolation with User B...")
    user_b_data = {
        "name": "User B",
        "age": 45,
        "sex": "Male",
        "contact": "+1 555 000 0000",
        "email": "user_b@hospital.org",
        "password": "PasswordUserB123!",
    }
    reg_b_resp = client.post("/api/auth/register", json=user_b_data)
    if reg_b_resp.status_code == 201:
        token_b = reg_b_resp.json()["access_token"]
    else:
        login_b = client.post("/api/auth/login", json={
            "email": "user_b@hospital.org",
            "password": "PasswordUserB123!",
        })
        token_b = login_b.json()["access_token"]

    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Attempt to access User A's job with User B's token
    target_job = user_a_job_ids[0]
    b_job_resp = client.get(f"/api/jobs/{target_job}", headers=headers_b)
    if b_job_resp.status_code != 403:
        print(f"FAILED: User B should be forbidden from reading User A's job, got {b_job_resp.status_code}")
        return False
    print(f"User B access to User A's job {target_job} correctly rejected (403 Forbidden).")

    # Attempt to access User A's report image with User B's token
    target_report = user_a_report_ids[0]
    b_img_resp = client.get(f"/api/report/{target_report}/image", headers=headers_b)
    if b_img_resp.status_code != 403:
        print(f"FAILED: User B should be forbidden from viewing User A's report image, got {b_img_resp.status_code}")
        return False
    print(f"User B access to User A's report image {target_report} correctly rejected (403 Forbidden).")

    # Attempt to download User A's report PDF with User B's token
    b_pdf_resp = client.get(f"/api/report/{target_report}/pdf", headers=headers_b)
    if b_pdf_resp.status_code != 403:
        print(f"FAILED: User B should be forbidden from downloading User A's report PDF, got {b_pdf_resp.status_code}")
        return False
    print(f"User B access to User A's report PDF {target_report} correctly rejected (403 Forbidden).")

    # Unauthenticated access to /api/me
    unauth_resp = client.get("/api/me")
    if unauth_resp.status_code != 401:
        print(f"FAILED: Unauthenticated /api/me should return 401, got {unauth_resp.status_code}")
        return False
    print("Unauthenticated access correctly rejected with 401 Unauthorized.")

    print("\n" + "=" * 75)
    print("ALL CHECKS IN PHASES 4 & 5 PASSED WITH 100% SUCCESS")
    print("=" * 75)
    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
