import sys
import os
import json
import time
import requests
import pymupdf  # PyMuPDF

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = os.path.abspath("docs/screenshots/pdf")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SAMPLES = [
    {
        "module": "fracture",
        "file_path": os.path.abspath("backend/samples/fracture/fractured_01.png"),
        "roi_box": None,
    },
    {
        "module": "spine",
        "file_path": os.path.abspath("backend/samples/spine/spine_abnormal.dicom"),
        "roi_box": None,
    },
    {
        "module": "knee",
        "file_path": os.path.abspath("backend/samples/knee/knee_KL3.png"),
        "roi_box": None,
    },
    {
        "module": "chest",
        "file_path": os.path.abspath("backend/samples/chest/chest_cardiomegaly.png"),
        "roi_box": None,
    },
    {
        "module": "tumor",
        "file_path": os.path.abspath("backend/samples/tumor/tumor_benign.jpeg"),
        "roi_box": json.dumps([0.34, 0.46, 0.62, 0.78]),
        "tag": "roi",
    },
    {
        "module": "tumor",
        "file_path": os.path.abspath("backend/samples/tumor/tumor_normal.jpeg"),
        "roi_box": None,
        "tag": "whole_image",
    },
]

def run():
    session = requests.Session()
    # 1. Register test user
    email = f"pdftest_{int(time.time())}@example.com"
    pwd = "TestPassword123!"
    reg_resp = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": email,
        "password": pwd,
        "name": "Dr. PDF Validator",
        "age": 35,
        "sex": "Female"
    })
    if reg_resp.status_code not in (200, 201):
        print(f"Registration failed: {reg_resp.text}")
        return
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Authenticated as {email}")

    rendered_pages = []

    for s in SAMPLES:
        mod = s["module"]
        path = s["file_path"]
        tag = s.get("tag", "")
        label = f"{mod}_{tag}" if tag else mod
        print(f"\n--- Testing Module: {label} ---")
        
        with open(path, "rb") as f:
            files = {"file": (os.path.basename(path), f, "application/octet-stream")}
            data = {"module": mod}
            if s["roi_box"]:
                data["roi_box"] = s["roi_box"]
            
            job_resp = session.post(f"{BASE_URL}/api/jobs", files=files, data=data, headers=headers)
        
        if job_resp.status_code != 202:
            print(f"Job creation failed for {label}: {job_resp.status_code} {job_resp.text}")
            continue
            
        job_id = job_resp.json()["job_id"]
        print(f"Job created: {job_id}. Polling status...")
        
        target_report_id = job_id
        for _ in range(60):
            st_resp = session.get(f"{BASE_URL}/api/jobs/{job_id}", headers=headers)
            st_data = st_resp.json()
            st = st_data.get("status")
            if st == "done":
                print(f"Job {job_id} done!")
                if st_data.get("result") and st_data["result"].get("report_id"):
                    target_report_id = st_data["result"]["report_id"]
                break
            elif st == "failed":
                print(f"Job {job_id} failed: {st_resp.json().get('error')}")
                break
            time.sleep(1)
        
        # Download PDF
        pdf_resp = session.get(f"{BASE_URL}/api/report/{target_report_id}/pdf", headers=headers)
        if pdf_resp.status_code != 200:
            print(f"PDF download failed: {pdf_resp.status_code} {pdf_resp.text}")
            continue
        
        pdf_bytes = pdf_resp.content
        if not pdf_bytes.startswith(b"%PDF"):
            print(f"Invalid PDF header: {pdf_bytes[:10]}")
            continue
            
        pdf_file = os.path.join(OUTPUT_DIR, f"{label}_report_{job_id}.pdf")
        with open(pdf_file, "wb") as pf:
            pf.write(pdf_bytes)
        print(f"Saved PDF ({len(pdf_bytes)} bytes) to {pdf_file}")
        
        # Render pages with PyMuPDF
        doc = pymupdf.open(pdf_file)
        page_count = len(doc)
        print(f"PDF Page count: {page_count}")
        
        for page_idx in range(page_count):
            page = doc[page_idx]
            pix = page.get_pixmap(dpi=150)
            png_path = os.path.join(OUTPUT_DIR, f"{label}_page_{page_idx+1}.png")
            pix.save(png_path)
            print(f"Rendered page {page_idx+1} to {png_path} ({pix.width}x{pix.height})")
            rendered_pages.append({
                "module": label,
                "job_id": job_id,
                "pdf_file": pdf_file,
                "page": page_idx + 1,
                "png_path": png_path,
                "width": pix.width,
                "height": pix.height
            })
        doc.close()

    print("\nSummary of Rendered PDF Pages:")
    for rp in rendered_pages:
        print(f"  {rp['module']} P{rp['page']}: {rp['png_path']} ({rp['width']}x{rp['height']})")

if __name__ == "__main__":
    run()
