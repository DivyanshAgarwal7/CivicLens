# CivicLens Final Demonstration Release

Release: `v1.0.0-phase8-demo`  
Audit date: 2026-10-16  
Scope: independent final audit and demonstration freeze

## What is included

CivicLens is a role-based civic issue reporting workflow:

1. A Citizen registers, signs in, submits an issue with location and optional evidence, and can verify public issues.
2. AI-assisted duplicate and priority analysis is persisted with an explicit method and rationale; deterministic fallback behavior is available when local ML weights are absent.
3. A Municipal Officer reviews priority, assigns a department and Field Engineer, and sees protected analytics/audit surfaces.
4. The assigned Field Engineer progresses the issue through `Assigned` → `In Progress` → `Resolved`, with evidence required for resolution.
5. Notifications, audit events, community verification counts, and evidence-backed resolution are visible through protected workflow surfaces.

The release archive contains source, Docker/CI configuration, dependency manifests, environment examples, and relevant documentation. It excludes secrets, local databases, uploads, caches, build output, logs, and Git metadata.

## Verified local setup

Verified environment: Python 3.13.4, Node.js v22.16.0, npm 11.7.0, Windows PowerShell.

The local development path deliberately uses the JSON store only when explicitly enabled. Production configuration requires MongoDB and disallows the JSON fallback.

### Backend

From the repository root:

```powershell
Copy-Item backend/.env.example backend/.env
# Edit backend/.env: set a non-placeholder JWT_SECRET and keep APP_ENV=development,
# ALLOW_JSON_DB=true for a disposable local demonstration.
python -m pip install -r requirements.txt
Set-Location backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend endpoints: `http://127.0.0.1:8000`, OpenAPI at `/docs`, readiness at `/api/health`.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:5173`.

For a production-like run, use `docker compose up --build` from the repository root after setting `MONGO_ROOT_USERNAME`, `MONGO_ROOT_PASSWORD`, and `JWT_SECRET`. Docker and Mongo were not available in this audit environment, so that path is documented but not claimed as executed here.

## Demonstration workflow

Use [DEMO_SCRIPT.md](DEMO_SCRIPT.md) for the detailed script:

1. Register a disposable Citizen account and sign in.
2. Submit a report with title, description, category, address, coordinates, and optional image.
3. Show persisted AI method, rationale, priority, verification count, and status history.
4. As a Municipal Officer, review priority and assign a matching department and engineer.
5. As that Field Engineer, move the task to `In Progress`, then resolve it with notes and evidence.
6. Return to the Citizen view and show resolved status, notifications, public verification content, and evidence.

Seeded local accounts are for disposable demonstration data only; inspect `backend/seed_data.py` in the local checkout when credentials are needed. They are intentionally not repeated here.

## AI behavior and claims

Duplicate detection attempts a local sentence-transformers model with `local_files_only=True`. If weights are unavailable, it records a TF-IDF lexical fallback (or Jaccard fallback if needed). Priority prediction is deterministic and category/severity based, with optional Gemini integration guarded by configuration. Decisions store method/model metadata and rationale.

The bundled evaluation fixture is synthetic and demonstration-only: 5 samples, precision 1.0, recall 1.0, F1 1.0, false-positive rate 0.0; 4 lexical-fallback samples and 1 unavailable sample. These numbers are not a semantic-model benchmark.

## Final verification results

| Gate | Result | Evidence |
|---|---|---|
| Backend tests | PASS | `19 passed`, 24 warnings |
| Python compilation | PASS | `python -m compileall -q backend` |
| AI evaluation | PASS with limitation | Synthetic fixture; warning retained |
| Frontend lint | PASS with warnings | `npm run lint` exits 0; existing effect/dependency and unused-import warnings |
| Frontend build | PASS | TypeScript + Vite production build succeeds |
| Performance smoke | PASS with limitation | 20 local duplicate-detection samples; p50 1.317 ms, p95 2762.375 ms, mean 139.447 ms |
| Docker build/compose | BLOCKED | Docker unavailable in audit environment |
| Mongo production path | BLOCKED | `mongod`/`mongosh` unavailable; no external database supplied |
| Dependency audit | BLOCKED | `pip-audit` unavailable; npm registry resolution unavailable for `npm audit` |
| Browser/API rerun | NOT RUN in Phase 8 | Prior Phase 5 live validation remains documented separately |

## Security and privacy notes

- JWTs require expiry, issuer, subject, and access-token type claims.
- Passwords use bcrypt; the legacy hash path is migration-only.
- Public issue serializers remove reporter identity and internal password fields.
- Public verification responses now remove verifier identity and trust score while returning `verified_by_current_user` for an authenticated viewer.
- Officer, engineer, admin, notification, analytics, and audit surfaces are role protected.
- Uploads enforce allowed image types, size limits, and image verification.
- Production rejects wildcard CORS, requires JWT configuration, requires MongoDB, and disables JSON fallback.
- The release archive excludes `.env`, data, uploads, caches, logs, build output, and Git metadata.

## Known limitations and recovery

- Docker/Mongo and dependency scanners must be rerun in a networked CI or staging environment; resolve blocked gates before production deployment.
- Existing frontend lint warnings are non-fatal but should be cleaned in a maintenance pass.
- The JSON store is disposable development support, not a production datastore. Stop the backend and delete only disposable JSON files in a disposable checkout to reset it; never use that procedure against MongoDB or real data.
- Optional Cloudinary, SMTP, Gemini, and local model weights require their own environment configuration and were not included in the archive.

The versioned archive is additive and does not overwrite prior Phase 4–7 archives. To recover, unpack it into a new directory, copy `backend/.env.example` to `backend/.env`, install from the root `requirements.txt`, install frontend dependencies with `npm ci`, and follow the startup commands above.
