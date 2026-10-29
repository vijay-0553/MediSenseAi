# MediSense AI - Multi-Module Medical Radiograph Analysis Platform

MediSense AI is an end-to-end, deep learning-assisted medical imaging platform for evaluating radiographs across five clinical domains: **Bone Fracture (Upper Limb)**, **Bone Tumor (BTXRD)**, **Spine**, **Knee Osteoarthritis**, and **Chest (Thoracic Pathologies)**.

The system connects a modern React 19 + TypeScript + Vite + Tailwind CSS v4 frontend (green `#00c853` / mint `#e8f8ee` / white) with a high-performance FastAPI backend executing 9 real deep learning checkpoints (TensorFlow/Keras and PyTorch) without mock predictions or synthetic fallbacks.

---

## Architecture Overview

```
MediSenseAi/
├── backend/
│   ├── architectures/         # Custom neural network definitions (CBAM, MediSenseDenseNet, EfficientNet)
│   ├── config.py              # Environment settings, secret validation, storage paths
│   ├── db.py                  # SQLAlchemy engine, session factory, table initialization
│   ├── db_models.py           # SQLite User model
│   ├── inference/             # Domain inference modules (fracture, tumor, spine, knee, chest)
│   ├── main.py                # FastAPI app, endpoints, CORS, job worker dispatch
│   ├── models/models/         # Pre-trained deep learning checkpoints (9 files)
│   ├── preprocessing/         # Exact bit-level image/DICOM preprocessing
│   ├── reports/               # ReportLab PDF report builder (pristine Blue & White clinical theme)
│   ├── requirements.txt       # Python dependency specifications
│   ├── samples/               # Validated real radiograph samples for testing
│   ├── schemas.py             # Pydantic v2 schemas for requests and responses
│   ├── services/
│   │   ├── auth.py            # Bcrypt password hashing, JWT creation/verification, rate limiting
│   │   ├── job_manager.py     # Multi-threaded job queue for real-event progress tracking
│   │   ├── model_manager.py   # Model loading, startup warmups, per-model thread locks
│   │   └── storage.py         # Report artifact persistence, DICOM-to-PNG preview, TTL cleanup
│   └── tests/                 # Automated PyTest test suite
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.ts      # Axios client with upload progress and JWT interceptors
│   │   │   └── types.ts       # TypeScript API and model response interfaces
│   │   ├── App.tsx            # Main router, Landing, Auth, Home, and optional ROI selector
│   │   ├── ResultsPage.tsx    # Interactive analysis results page with zoomable X-ray and metrics
│   │   ├── index.css          # Design tokens, mint/green theme (#00c853, #e8f8ee)
│   │   └── main.tsx           # React DOM root entrypoint
│   ├── package.json           # Frontend dependencies (React 19, Vite, Tailwind v4, Axios)
│   ├── tsconfig.json          # TypeScript configuration
│   └── vite.config.ts         # Vite build configuration
├── docs/
│   ├── api.md                 # Complete REST API reference with JSON payloads
│   ├── model-inference.md     # Preprocessing pipelines, class orders, parity, limitations
│   └── screenshots/           # Verification screenshots and rendered PDF outputs
└── README.md
```

---

## Prerequisites

- **Python**: `3.11.x` (64-bit recommended)
- **Node.js**: `v20.x` or `v22.x` (with `npm` or `pnpm`)
- **OS**: Windows, Linux, or macOS

---

## Getting Started

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate a Python 3.11 virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env

# Start FastAPI server
uvicorn main:app --reload --port 8000
```
The backend server runs at `http://localhost:8000`. API documentation is available at `http://localhost:8000/docs`.

---

### 2. Frontend Setup

```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Configure environment variables
copy .env.example .env

# Start the Vite development server
npm run dev
```
The frontend runs at `http://localhost:5173` (or the port indicated by Vite in console).

---

## Environment Variables

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `PORT` | Backend server port | `8000` |
| `HOST` | Backend bind address | `0.0.0.0` |
| `CORS_ORIGINS` | Allowed origins (comma-separated) | `http://localhost:8443,http://localhost:5173` |
| `JWT_SECRET` | Secret key for JWT signing (**Refuses to start if default/empty**) | Secure random string |
| `JWT_ALGORITHM` | Algorithm for JWT tokens | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan in minutes | `1440` (24 hours) |
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./medisense.db` |
| `REPORT_TTL_HOURS` | Retention period for report artifacts before cleanup | `24` |
| `MAX_UPLOAD_SIZE_MB` | Maximum allowed file upload size | `25` |
| `VITE_API_URL` (Frontend) | URL of backend API | `http://localhost:8000` |

---

## Token Storage Choice & Security Note

Authentication tokens are stored in **memory** and synchronized with **`sessionStorage`**:
- **Why `sessionStorage`**: It automatically clears when the browser tab or session closes, preventing prolonged token persistence on shared hospital or clinical workstations.
- **XSS vs. CSRF Trade-off**: Storing in `sessionStorage` avoids CSRF vulnerabilities inherent in ambient cookies without requiring complex double-submit CSRF mechanisms. Strict JSX escaping, absence of `dangerouslySetInnerHTML`, and CSP headers protect against XSS.

---

## Supported File Formats

- **JPG / JPEG / PNG**: Supported across all modules.
- **DICOM (`.dcm`, `.dicom`)**: Natively supported for the **Spine** module via `pydicom`. The backend renders DICOM images to PNG using the exact `dicom_to_uint8` pipeline from the research notebooks for browser display and PDF report inclusion.

---

## Deep Learning Modules & Pipeline Summary

| Module | Backbone Architecture | Input Resolution & Preprocessing | Output Activation & Interpretation |
| :--- | :--- | :--- | :--- |
| **Fracture** | DenseNet-201 + CBAM (Keras) | $224 \times 224$, tf resize + `densenet.preprocess_input` | Sigmoid $P(\text{fracture})$: `0`: not fractured, `1`: fractured |
| **Tumor** | ResNet-50 5-Fold Baseline (PyTorch) | $384 \times 384$, ImageNet norm, optional ROI crop | Softmax 3-class: `Normal`, `Benign`, `Malignant` |
| **Spine** | DenseNet-201 + CBAM (PyTorch) | $224 \times 224$, DICOM Rescale/MONOCHROME1/min-max + ImageNet norm | Sigmoid $P(\text{abnormal})$. Threshold = `0.7574` |
| **Knee** | EfficientNet-B5 (PyTorch) | $224 \times 224$, plain resize + ImageNet norm | Softmax 5-class: `KL-0` to `KL-4` |
| **Chest** | DenseNet-121 (PyTorch) | $224 \times 224$, plain resize + ImageNet norm | 14 Independent Sigmoids. Threshold = `0.50` |

---

## Asynchronous Real-Event Progress Flow

Unlike mock applications that use fake timers, MediSense AI drives the 5-step analysis progress card via real server events:

```
[User Selects File] ──> [Upload with Axios Progress 0..100%] ──> Stage 1: X-ray uploaded
                                 │
                                 ▼
                     [Server Returns 202 Accepted & job_id] ────> Stage 2: X-ray fetched
                                 │
                                 ▼ (Worker thread starts inference)
                      [Poll GET /api/jobs/{id}: "analyzing"] ───> Stage 3: Model analyzing
                                 │
                                 ▼ (Inference done; building PDF)
               [Poll GET /api/jobs/{id}: "generating_report"] ──> Stage 4: Report generation
                                 │
                                 ▼ (PDF built & cached)
                         [Poll GET /api/jobs/{id}: "done"] ────> Stage 5: Report ready
```

---

## PDF Report Theming

The downloadable PDF report generated in `backend/reports/pdf_builder.py` uses a pristine **Blue & White** clinical styling (`#1565C0` Primary Blue, `#0D47A1` Dark Navy Title, `#E3F2FD` Light Blue box fills, `#BBDEFB` borders) with zero green, keeping amber `#F59E0B` exclusively for cautionary notices and whole-image caveats.

---

## Medical Disclaimer

> [!CAUTION]
> **MediSense AI is intended strictly for research and clinical decision-support purposes.**
> The predictions, probabilities, and reports generated by this software do not constitute a confirmed medical diagnosis and should never replace professional medical evaluation by a licensed physician or radiologist.
