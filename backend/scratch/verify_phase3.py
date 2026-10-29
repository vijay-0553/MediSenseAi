"""
Phase 3 Complete Verification Script
Tests all 5 modules through the job flow, verifies PDF text with pypdf,
and renders page 1 to PNG with PyMuPDF to visually confirm all layout elements.
"""

import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from services.model_manager import model_manager
import pypdf
import fitz  # PyMuPDF

def run_verification():
    print("=" * 70)
    print("STARTING PHASE 3 VERIFICATION")
    print("=" * 70)

    # 1. Warm up models
    print("[1/4] Warming up models via model_manager...")
    model_manager.load_all()
    print("Models loaded successfully.")

    client = TestClient(app)

    samples = [
        ("fracture", backend_dir / "samples" / "fracture" / "fractured_01.png"),
        ("tumor", backend_dir / "samples" / "tumor" / "tumor_benign.jpeg"),
        ("spine", backend_dir / "samples" / "spine" / "spine_abnormal.dicom"),
        ("knee", backend_dir / "samples" / "knee" / "knee_KL0.png"),
        ("chest", backend_dir / "samples" / "chest" / "chest_cardiomegaly.png"),
    ]

    all_passed = True
    output_images = []

    for module, sample_path in samples:
        print(f"\n--- Testing Module: {module.upper()} ({sample_path.name}) ---")
        if not sample_path.exists():
            print(f"FAILED: Sample file does not exist: {sample_path}")
            all_passed = False
            continue

        with open(sample_path, "rb") as f:
            file_bytes = f.read()

        # Step A: POST /api/jobs
        print(f"Posting job to /api/jobs...")
        resp = client.post(
            "/api/jobs",
            data={"module": module},
            files={"file": (sample_path.name, file_bytes, "application/octet-stream")}
        )
        if resp.status_code != 202:
            print(f"FAILED: Expected 202 Accepted, got {resp.status_code}: {resp.text}")
            all_passed = False
            continue

        job_data = resp.json()
        job_id = job_data["job_id"]
        print(f"Job created: {job_id}, status={job_data['status']}")

        # Step B: Poll until done
        status_stages_seen = [job_data["status"]]
        max_polls = 40
        done = False
        final_job = None

        for poll_idx in range(max_polls):
            time.sleep(0.5)
            poll_resp = client.get(f"/api/jobs/{job_id}")
            if poll_resp.status_code != 200:
                print(f"Polling failed: {poll_resp.status_code}")
                break
            final_job = poll_resp.json()
            st = final_job["status"]
            if st not in status_stages_seen:
                status_stages_seen.append(st)
            if st in ("done", "failed"):
                done = True
                break

        print(f"Job progress stages observed: {' -> '.join(status_stages_seen)}")
        if not done or final_job["status"] != "done":
            print(f"FAILED: Job did not complete successfully: {final_job}")
            all_passed = False
            continue

        result = final_job["result"]
        report_id = result["report_id"]
        print(f"Inference output: prediction='{result.get('prediction', result.get('primary_finding'))}', time={result.get('inference_time_ms')}ms")
        print(f"Notices returned: {result.get('notices', [])}")

        # Step C: GET /api/report/{report_id}/image
        img_resp = client.get(f"/api/report/{report_id}/image")
        if img_resp.status_code != 200 or len(img_resp.content) < 100:
            print(f"FAILED: /api/report/{report_id}/image returned {img_resp.status_code}, length={len(img_resp.content)}")
            all_passed = False
            continue
        print(f"Preview image retrieved: {len(img_resp.content)} bytes, Content-Type={img_resp.headers.get('content-type')}")

        # Step D: GET /api/report/{report_id}/pdf
        pdf_resp = client.get(f"/api/report/{report_id}/pdf")
        if pdf_resp.status_code != 200 or not pdf_resp.content.startswith(b"%PDF"):
            print(f"FAILED: /api/report/{report_id}/pdf failed or invalid PDF header. Status: {pdf_resp.status_code}")
            all_passed = False
            continue
        print(f"PDF report retrieved: {len(pdf_resp.content)} bytes, Content-Type={pdf_resp.headers.get('content-type')}")

        # Step E: Extract text with pypdf and verify all mandatory content elements
        pdf_reader = pypdf.PdfReader(io.BytesIO(pdf_resp.content))
        num_pages = len(pdf_reader.pages)
        page1_text = pdf_reader.pages[0].extract_text()

        page1_lower = page1_text.lower()

        # Checks
        assert "medisense ai" in page1_lower, "Missing MediSense AI header"
        assert "ai-assisted x-ray analysis report" in page1_lower, "Missing subtitle"
        assert "patient information" in page1_lower, "Missing patient info block"
        assert "examination & scan details" in page1_lower, "Missing scan details block"
        assert "acquired radiograph" in page1_lower, "Missing radiograph section"
        assert "model probability distribution" in page1_lower, "Missing probability chart"
        assert "this result is generated by an ai model and is intended for research/decision-support purposes only" in page1_lower, "Missing footer disclaimer"
        assert "page 1 of" in page1_lower, "Missing page number"

        # Module-specific checks
        if module == "tumor":
            assert "model was trained on roi-cropped tumor regions" in page1_lower, "Missing tumor whole-image notice in PDF"
        elif module == "chest":
            assert "labels use an uncalibrated 0.5 threshold" in page1_lower, "Missing chest threshold notice in PDF"
        elif module == "knee":
            assert "standard kl grade description (reference, not a model output)" in page1_lower, "Missing knee KL reference in PDF"
        elif module == "spine":
            assert "abnormal probability" in page1_lower or "decision threshold" in page1_lower, "Missing spine abnormal probability"

        print(f"Text validation passed: Header, Patient, Scan, Prediction, Chart, Notices, Footer verified ({num_pages} page(s)).")

        # Step F: Render page 1 to PNG with PyMuPDF
        render_path = backend_dir / "storage" / f"verify_render_{module}.png"
        doc = fitz.open(stream=pdf_resp.content, filetype="pdf")
        page = doc.load_page(0)
        pix = page.get_pixmap(dpi=150)
        pix.save(str(render_path))
        print(f"Rendered Page 1 saved to: {render_path} ({pix.width}x{pix.height})")
        output_images.append(str(render_path))

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL 5 MODULES PASSED PHASE 3 VERIFICATION")
    else:
        print("PHASE 3 VERIFICATION FAILED")
    print("=" * 70)
    return all_passed

if __name__ == "__main__":
    import io
    success = run_verification()
    sys.exit(0 if success else 1)
