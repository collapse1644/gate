# GATE CS 2027 PYQ Tutor — Documentation

Local-first study application for GATE CS 2027 previous-year questions. Content comes only from PDFs you upload; AI output is always labelled with its verification status.

## Architecture

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, Alembic, SQLite + FTS5 (`backend/`).
- **Frontend**: Next.js 16 (React 19, Tailwind 4, KaTeX, Recharts) (`frontend/`).
- **AI**: provider-independent router with Gemini (`google-genai`) and local llama.cpp; modes `auto` / `gemini` / `local` / `local_only`.

## Prerequisites

- Python 3.11+
- Node.js 20+ (tested on Node 24)
- (Optional) NVIDIA GPU + CUDA for local Qwen via llama.cpp
- (Optional) Gemini API key from Google AI Studio

## Starting and Stopping the Application

Two PowerShell scripts are provided at the project root (`G:\MINI-PROJ\gate`):

- **`start.ps1`** — Starts the FastAPI backend (port 8000), the local llama.cpp AI server (port 8080, managed via the backend), and the Next.js frontend (port 3000). Includes pre-flight port checks and health verification.
- **`stop.ps1`** — Stops only the application processes listening on those ports. It does **not** kill unrelated Python or Node.js processes.

### Quick start

```powershell
# From the project root (G:\MINI-PROJ\gate):
.\start.ps1

# Open the frontend:
#   http://localhost:3000
# Backend health:
#   http://127.0.0.1:8000/api/health
```

### Stop

```powershell
.\stop.ps1
```

### Custom ports

```powershell
.\start.ps1 -BackendPort 8001 -LlamaPort 8081 -FrontendPort 3001
.\stop.ps1 -BackendPort 8001 -LlamaPort 8081 -FrontendPort 3001
```

### Skip individual components

```powershell
.\start.ps1 -SkipLlama      # Backend + frontend only (no local AI)
.\stop.ps1 -SkipFrontend    # Backend + AI only (keep frontend running)
```

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
```

The database is created at `backend/data/gate.db` by default. Official 2027 syllabus PDFs are already stored under `backend/data/` and seeded on first startup.

Run the backend:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Health check: `http://127.0.0.1:8000/api/health`.

## Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend reads `NEXT_PUBLIC_API_URL` (default `http://127.0.0.1:8000/api`).

Typecheck / build:

```powershell
npm run typecheck
npm run build
```

## Tests

```powershell
cd backend
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m pytest -q
```

38 tests cover PDF parsing, figure extraction, no-OCR policy, answer keys, classification, verification sandbox/policy, progress/revision, analytics, AI routing (including local-only), API, ZIP ingestion, and unsafe ZIPs.

## Gemini setup

1. Create an API key in Google AI Studio.
2. Open **Settings** in the app, paste the key, and save. The key is stored encrypted locally (`backend/data/.secret.key`) and never returned in full.
3. Set `cloud_consent = true` before any Gemini call. Without consent the router refuses cloud calls.
4. Default model is `gemini-3.8-flash` (editable). Verify current free-tier eligibility and quotas in Google AI Studio.

## Local Qwen / llama.cpp setup

1. Download a GGUF model and (for vision) an mmproj file. Place them under `backend/data/models/` (or any path).
2. Install a CUDA build of `llama-server` (llama.cpp).
3. In **Settings**, set:
   - `local_base_url` (e.g. `http://127.0.0.1:8080`)
   - `local_model_path`, `local_mmproj_path`
   - `local_context`, `local_gpu_layers` (tune for your VRAM; RTX 5050 8 GB ≈ 30–35 layers for 7B Q4)
   - `local_auto_start` if you want the backend to launch it.
4. Start/stop from the **AI Tutor** page or Settings. The vision model is started only when figures are present.
5. Use `ai_mode = local_only` to guarantee no cloud traffic.

## ZIP ingestion

Prepare a ZIP containing GATE question-paper PDFs and matching answer-key PDFs. Filenames should encode year/session (the ingestion parser reads them). Text-layer PDFs only — scans are flagged for manual review (no OCR is performed).

Upload via **Data Management → Upload PYQ ZIP**. The job runs in the background; progress and per-file stats are polled automatically. Failed or needs-review files can be resumed.

Figures (raster and vector regions) are clipped from the original PDF pages at 2× resolution and stored under `backend/data/assets/`. They are never redrawn.

## Backups & data management

- **Backups** copy the SQLite database only; originals and figure assets live under `backend/data/`. Create/restore from Data Management.
- **Integrity check** runs `PRAGMA integrity_check` and reports issues.
- **Export** downloads a JSON dump of questions, progress, formulas, and settings metadata.

## Privacy notes

- Cloud AI is optional and requires explicit consent.
- Only minimal context (question text, options, selected taxonomy) is sent to the cloud.
- API keys are backend-only and encrypted at rest.
- `ai_logging = metadata` by default (no prompt bodies).
- `local_only` mode never contacts cloud providers and will not silently switch to cloud on failure.

## Verification policy

- AI-generated solutions start as `UNVERIFIED`.
- Structural checks (SymPy/numeric, in a restricted sandbox) are recorded as `PARTIALLY VERIFIED` evidence only.
- `VERIFIED` requires independent computation or a recorded expert review.
- Manual expert checks are appended to the audit trail and never erase earlier checks or versions.
- Prior verified solutions are preserved when regenerating.

## Classification policy

- Hybrid: rules + TF-IDF + optional LLM, with confidence scoring.
- Uncertain items go to the review queue; nothing is auto-accepted below threshold.
- Out-of-syllabus items are flagged, not forced into the taxonomy.
- A benchmark panel compares your saved expected labels against classifier output.

## Known limitations

- No OCR: scanned PDFs are flagged for manual review.
- Practice uses only uploaded, approved PYQs (no synthetic questions).
- Analytics are computed only from actually uploaded papers.
- Local models are loaded one at a time; vision model starts only when images are present.
- Free-tier Gemini quotas/availability change; verify in Google AI Studio.
- SQLite is default; PostgreSQL migration is supported by the SQLAlchemy layer but not the default.
