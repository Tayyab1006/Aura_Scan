# AURA Global: Multinational AI Health Intelligence

AURA Global is a research and validation platform for non-contact vital sign telemetry. It uses a camera-based rPPG pipeline, a real-time React command center, a FastAPI processing service, and a Django admin panel for operational records.

The platform is not a life-support system, certified medical device, emergency monitor, diagnostic tool, or treatment/triage system. If someone may be in danger, use an approved medical device and contact emergency services immediately.

Current status: prototype and validation build. Do not use for patient diagnosis, triage, treatment, or monitoring until the product has passed clinical validation, risk management, cybersecurity review, quality-system controls, and the applicable regulatory pathway for the target market.

## Global Platform

- **Command Center**: React, Tailwind CSS, Chart.js, and WebSocket telemetry.
- **AI Processing API**: FastAPI, OpenCV, MediaPipe, SciPy, and NumPy.
- **Operations Admin**: Django, Django REST Framework, and SQLite/PostgreSQL-ready persistence.
- **Security Posture**: JWT-secured control endpoints and environment-based secrets.
- **Safety Posture**: Fail closed by default with `CLINICAL_USE_ENABLED=false`.

## Installation & Setup

### 1. Backend API

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m backend.main
```

The backend runs on `http://localhost:8001` when `BACKEND_PORT=8001` is set in the root `.env`.

Clinical-use mode is disabled by default:

```powershell
CLINICAL_USE_ENABLED=false
```

Do not set this to `true` unless the intended use, validation evidence, regulatory pathway, cybersecurity controls, and clinical governance have all been completed.

### 2. Frontend Command Center

```powershell
cd frontend
npm install
npm run dev
```

The frontend expects the backend API and WebSocket server on port `8001`.

### 3. Admin Panel

```powershell
cd admin_panel
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py createsuperuser
..\.venv\Scripts\python.exe manage.py runserver
```

If you use the admin panel's own virtual environment, replace `..\.venv\Scripts\python.exe` with `.\venv\Scripts\python.exe`.

## API Documentation

- `POST /start-stream`: Initiates the rPPG analysis window and returns safety metadata.
- `POST /stop-stream`: Terminates active analysis.
- `GET /vitals`: Returns the latest BPM/RR telemetry state plus safety metadata.
- `WS /ws`: Streams camera frames from the client and sends processed telemetry back.
- `GET /`: Returns service status and platform version metadata.

## Signal Pipeline

1. **Capture**: Camera frames stream to the backend through WebSocket.
2. **Vision**: MediaPipe Face Mesh identifies facial regions of interest.
3. **Extraction**: The pipeline samples the mean green channel from ROI masks.
4. **DSP**: Detrending, Butterworth filtering, and FFT isolate signal frequency.
5. **Output**: Dominant frequencies are converted into BPM and respiration rate.

## Enterprise Notes

- Use the root `.env` for secrets and runtime configuration.
- Validate camera permissions before demos or deployments.
- Treat displayed vitals as prototype telemetry unless clinically validated and legally cleared.
- Do not use the app for life-and-death decisions, emergency response, patient deterioration detection, diagnosis, treatment, or triage.
- Keep backend, frontend, and admin checks green before calling a rollout complete.
- Review the real-world launch checklist in `docs/CLINICAL_READINESS.md`.
