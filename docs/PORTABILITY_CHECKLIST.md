# CivicLens Portability Checklist

## Runtime and dependencies

- Python 3.13 is the verified local runtime; Python 3.11+ is expected to work but is not separately validated here.
- Node.js 22.16.0 and npm 11.7.0 are the verified local runtimes.
- Install backend packages from the repository-root `requirements.txt`; there is intentionally no `backend/requirements.txt`.
- Install frontend packages with `npm ci` from `frontend`; use the committed `frontend/package-lock.json`.

## Local environment

1. From the repository root, copy `backend/.env.example` to `backend/.env`.
2. Set a unique development `JWT_SECRET`; do not copy it into documentation or source control.
3. Keep `APP_ENV=development` and `ALLOW_JSON_DB=true` only for disposable local demos.
4. Use `MONGODB_URI` and `ALLOW_JSON_DB=false` for staging/production; production refuses silent JSON fallback.
5. Keep `CORS_ORIGINS` limited to the actual frontend origin. Production rejects `*`.

Important variables include `MONGODB_URI`, `DB_NAME`, `APP_ENV`, `ALLOW_JSON_DB`, `JWT_SECRET`, `CORS_ORIGINS`, `MAX_UPLOAD_BYTES`, `AI_EMBEDDING_MODEL`, `AI_DUPLICATE_THRESHOLD`, `AI_LEXICAL_DUPLICATE_THRESHOLD`, `AI_USE_GEMINI`, optional `GEMINI_API_KEY`, optional `CLOUDINARY_URL`, and optional SMTP variables.

## Start commands and URLs

Backend:

```powershell
cd backend
python -m pip install -r ../requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend, in a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

URLs:

- Frontend: `http://localhost:5173`
- API documentation: `http://127.0.0.1:8000/docs`
- Readiness: `http://127.0.0.1:8000/api/health`
- Frontend `/api` and `/uploads` requests proxy to `127.0.0.1:8000` in Vite development mode.

## Data and model portability

- Development JSON data lives in `backend/data`; it is ignored by source control and is not production persistence.
- The backend seeds local departments, issues, and role accounts only when the users collection is empty.
- Reset only disposable JSON demo data: stop the backend, make an optional copy of `backend/data`, remove the JSON files in that disposable workspace, and restart. Do not run this procedure against MongoDB or real user data.
- Semantic embeddings require the configured model to be locally cached because model loading uses `local_files_only=True`. If unavailable, the service reports TF-IDF lexical fallback; it does not download a model at startup.
- Cloudinary is optional; local uploads are used when configured by the current implementation.
- SMTP is optional; without it, email activity is simulated/logged locally.

## Verification commands

```powershell
python -m pytest -q
python -m compileall -q backend
python backend/evaluation/evaluate_ai.py
python backend/evaluation/performance_smoke.py
cd frontend
npm run lint
npm run build
```

## Common failures

- Missing `JWT_SECRET`: set it in `backend/.env` before importing the backend.
- Production startup without Mongo: set a reachable authenticated `MONGODB_URI`; do not enable JSON fallback.
- Port 8000 or 5173 in use: stop the conflicting process or change both the command and Vite proxy consistently.
- Frontend API 502/connection refused: start the backend first and verify `/api/health`.
- Missing model: expect explicit lexical fallback; provision a local artifact and set `AI_EMBEDDING_MODEL` to enable semantic runtime testing.
- Docker build dependency error: build from the repository root because `backend/Dockerfile` copies the root `requirements.txt`.
