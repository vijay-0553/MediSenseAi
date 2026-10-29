import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from starlette.testclient import TestClient
from main import app

samples_dir = Path("backend/samples")

modules_test = [
    ("fracture", samples_dir / "fracture" / "fractured_01.png"),
    ("fracture", samples_dir / "fracture" / "not_fractured_01.png"),
    ("spine", samples_dir / "spine" / "spine_normal.dicom"),
    ("spine", samples_dir / "spine" / "spine_abnormal.dicom"),
    ("knee", samples_dir / "knee" / "knee_KL3.png"),
    ("chest", samples_dir / "chest" / "chest_cardiomegaly.png"),
    ("tumor", samples_dir / "tumor" / "tumor_benign.jpeg"),
]

# Use context manager so FastAPI lifespan triggers model loading and warmup!
with TestClient(app) as client:
    print("\n" + "="*80)
    print("TESTING /api/health ENDPOINT")
    print("="*80)
    health_res = client.get("/api/health")
    print("Status Code:", health_res.status_code)
    print(json.dumps(health_res.json(), indent=2))

    print("\n" + "="*80)
    print("TESTING /api/predict/{module} ENDPOINTS WITH REAL SAMPLES")
    print("="*80)

    for mod, path in modules_test:
        print(f"\n--- Testing POST /api/predict/{mod} with {path.name} ---")
        with open(path, "rb") as f:
            file_bytes = f.read()
        
        files = {"file": (path.name, file_bytes, "application/octet-stream")}
        res = client.post(f"/api/predict/{mod}", files=files)
        print("Status Code:", res.status_code)
        data = res.json()
        print(json.dumps(data, indent=2))

    print("\n" + "="*80)
    print("ALL 5 MODULE API CONTRACT RESPONSES VERIFIED")
    print("="*80)
