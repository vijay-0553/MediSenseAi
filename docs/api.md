# MediSense AI - REST API Documentation

This document describes all endpoints provided by the MediSense AI FastAPI backend service.

---

## Base URL
Default local backend server: `http://localhost:8000`

---

## Authentication
Protected endpoints require an HTTP Bearer JWT token in the `Authorization` header:
```http
Authorization: Bearer <access_token>
```

Tokens are issued via `POST /api/auth/login` or `POST /api/auth/register` and expire according to `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 1440 minutes / 24 hours).

---

## 1. System Health & Environment

### `GET /api/health`
Checks runtime health, compute device, and individual model loading states.

**Response `200 OK`**:
```json
{
  "status": "healthy",
  "timestamp": "2026-10-23T01:30:00.000000+00:00",
  "device": "cpu",
  "modules": {
    "fracture": { "loaded": true, "error": null },
    "spine": { "loaded": true, "error": null },
    "knee": { "loaded": true, "error": null },
    "chest": { "loaded": true, "error": null },
    "tumor": { "loaded": true, "error": null }
  }
}
```

---

## 2. Authentication & User Profile

### `POST /api/auth/register`
Creates a new patient account and returns an access token.

**Request Body (`application/json`)**:
```json
{
  "name": "Dr. Clara Oswald",
  "age": 32,
  "sex": "Female",
  "contact": "+1 555 999 1234",
  "email": "clara.oswald@hospital.org",
  "password": "SecurePassword123!"
}
```

**Response `201 Created`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "user": {
    "id": "e480ba56-ea6e-4009-aea4-78e65d3658a6",
    "name": "Dr. Clara Oswald",
    "age": 32,
    "sex": "Female",
    "contact": "+1 555 999 1234",
    "email": "clara.oswald@hospital.org",
    "avatar_url": null,
    "created_at": "2026-10-23T01:25:00.000000+00:00"
  }
}
```

---

### `POST /api/auth/login`
Authenticates user credentials. Subject to rate limiting (5 failed attempts per 5 minutes per email).

**Request Body (`application/json`)**:
```json
{
  "email": "clara.oswald@hospital.org",
  "password": "SecurePassword123!"
}
```

**Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "user": { ... }
}
```

---

### `GET /api/me` *(Protected)*
Returns the currently authenticated user's profile.

---

### `PUT /api/me` *(Protected)*
Updates profile fields.

**Request Body (`application/json`)**:
```json
{
  "contact": "+1 555 777 8888",
  "age": 33
}
```

---

### `PUT /api/me/password` *(Protected)*
Updates the account password. Requires valid current password.

**Request Body (`application/json`)**:
```json
{
  "current_password": "SecurePassword123!",
  "new_password": "NewSecurePassword456!"
}
```

---

### `POST /api/me/avatar` *(Protected)*
Uploads or updates user avatar (JPG, PNG, WebP up to 5 MB).

---

### `GET /api/me/avatar` *(Protected)*
Retrieves the user's avatar image.

---

## 3. Asynchronous Analysis Job Flow

### `POST /api/jobs`
Initiates an asynchronous deep learning inference job. Returns immediately with `202 Accepted` and a `job_id`.

**Request (`multipart/form-data`)**:
- `module`: `"fracture"` | `"tumor"` | `"spine"` | `"knee"` | `"chest"`
- `file`: Raw image/DICOM binary

**Response `202 Accepted`**:
```json
{
  "job_id": "JOB-ADC0521B861F",
  "status": "received"
}
```

---

### `GET /api/jobs/{job_id}`
Polls job execution state.

**Response `200 OK`**:
```json
{
  "job_id": "JOB-ADC0521B861F",
  "status": "done",
  "progress_stage": 5,
  "result": {
    "module": "fracture",
    "module_name": "Bone Fracture (Upper Limb)",
    "model_architecture": "DenseNet201 + CBAM",
    "report_id": "RPT-8D8D0A50",
    "timestamp": "2026-10-23T01:25:30.123456+00:00",
    "filename": "fractured_01.png",
    "inference_time_ms": 404.72,
    "prediction": "fractured",
    "confidence": 0.998,
    "low_confidence": false,
    "decision_threshold": 0.5,
    "probabilities": {
      "not fractured": 0.002,
      "fractured": 0.998
    },
    "raw_fracture_probability": 0.998014,
    "notices": [],
    "interpretation_note": "AI prediction: fractured. Model fracture probability (99.8%) exceeds the 50.0% decision threshold."
  },
  "error": null
}
```

**Status Stages**:
- `1`: Upload in progress (frontend client)
- `2`: `status: "received"`
- `3`: `status: "analyzing"`
- `4`: `status: "generating_report"`
- `5`: `status: "done"` (or `status: "failed"` with friendly error)

---

## 4. Reports & Visualizations

### `GET /api/report/{report_id}/image`
Returns rendered preview PNG of the analyzed radiograph (DICOM files are converted via the notebook's `dicom_to_uint8` pipeline). Protected by user ownership when created by an authenticated user.

---

### `GET /api/report/{report_id}/pdf`
Returns the generated ReportLab PDF evaluation report.
- Header: `Content-Disposition: attachment; filename="MediSense_Report_<report_id>.pdf"`
- Protected by user ownership.

---

## 5. Direct Synchronous Prediction

### `POST /api/predict/{module}`
Synchronous inference endpoint primarily used by automated integration test suites. Runs model evaluation, saves report artifacts, and returns full prediction JSON immediately.
