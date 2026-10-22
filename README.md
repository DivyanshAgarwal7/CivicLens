# CivicLens

AI-assisted civic issue reporting, prioritization, and resolution tracking for communities and municipal operations.

CivicLens supports the workflow from citizen report submission through duplicate detection, priority review, departmental assignment, field resolution, community verification, notifications, and audit history.

> Deployment status: the repository includes reproducible local development and Docker Compose deployment paths. Public production use still requires environment-specific security review, secret management, monitoring, backups, and operational approval.

## Contents

- Capabilities
- Architecture
- Prerequisites
- Quick start
- Configuration
- Production deployment
- Testing
- Authentication and roles
- AI and integrations
- Repository structure
- Troubleshooting
- Security
- Documentation
- Contributing

## Capabilities

- Citizen registration, JWT sign-in, issue reporting, image evidence, maps, status tracking, and community verification.
- AI-assisted duplicate detection and priority recommendation with safe fallback behavior.
- Officer priority review, department routing, assignment, and workflow status controls.
- Field-engineer work queues, resolution notes, and evidence-image support.
- Administrator analytics, issue mapping, role management, and audit logs.
- In-app notifications and simulated email-log visibility for local demonstrations.

## Architecture

    Browser: React 19 + TypeScript + Vite + Tailwind CSS + Leaflet
             | /api and /uploads
             v
    FastAPI + Uvicorn: JWT, RBAC, issue workflow, AI, notifications
             |
             +--> MongoDB / MongoDB Atlas for staging and production
             +--> Explicit JSON store for local development/test only
             +--> Optional Gemini, Cloudinary, SMTP, and sentence-transformers

The Vite development server proxies /api and /uploads to http://127.0.0.1:8000. Production serves the compiled frontend through Nginx and runs the backend separately.

## Prerequisites

- Python 3.13+
- Node.js 22+
- npm 11+
- Git
- Docker Engine/Desktop with Compose v2 for container deployment

## Quick start

### Clone

    git clone https://github.com/DivyanshAgarwal7/CivicLens.git
    cd CivicLens

### Start the backend

    cd backend
    if (!(Test-Path .env)) { Copy-Item .env.example .env }

Edit backend/.env and set a unique local-only JWT_SECRET, then install and run:

    python -m venv .venv
    .\\.venv\\Scripts\\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r ..\\requirements.txt
    python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

Backend URLs:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

### Start the frontend

Open a second terminal from the repository root:

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173.

The backend seeds local demo data only when the development users collection is empty. Seeded accounts are for disposable local testing; inspect backend/seed_data.py locally when credentials are required. Never use them in production.

## Configuration

Copy backend/.env.example to backend/.env. Important variables are:

| Variable | Purpose | Local | Production |
|---|---|---|---|
| APP_ENV | Runtime mode | development | production |
| ALLOW_JSON_DB | Embedded JSON database | true | false |
| MONGODB_URI | MongoDB connection | Optional | Required |
| DB_NAME | Database name | civiclens | Dedicated database |
| JWT_SECRET | Signs access tokens | Required | High-entropy secret manager value |
| JWT_ALGORITHM | JWT algorithm | HS256 | Review with security policy |
| JWT_EXPIRATION_MINUTES | Token lifetime | 1440 | Short, policy-approved lifetime |
| CORS_ORIGINS | Allowed browser origins | Localhost origins | Explicit HTTPS origins |
| MAX_UPLOAD_BYTES | Upload limit | 5242880 | Match infrastructure policy |
| AI_USE_GEMINI | Enable Gemini | false | Only with approved credentials |
| GEMINI_API_KEY | Gemini credential | Empty | Secret-managed only |
| CLOUDINARY_URL | Optional image storage | Empty | Secret-managed only |
| SMTP_* | Optional email integration | Empty/simulated logs | Managed SMTP provider |

Never commit .env, API keys, passwords, JWTs, database credentials, uploads, or local user data.

## Production deployment

docker-compose.yml runs MongoDB, FastAPI, and the Nginx-served frontend. Set deployment secrets outside the repository:

    $env:MONGO_ROOT_PASSWORD = "use-a-secret-manager-value"
    $env:JWT_SECRET = "use-a-long-random-secret"
    $env:CORS_ORIGINS = "https://civiclens.example.com"
    docker compose up --build -d
    docker compose ps

The application is exposed on http://localhost:8080 by default. Stop it with:

    docker compose down

Use docker compose down -v only after confirming that the MongoDB data is disposable.

Before public deployment:

1. Use authenticated MongoDB with backups, network restrictions, and least-privilege credentials.
2. Set APP_ENV=production and ALLOW_JSON_DB=false.
3. Put HTTPS at the ingress or reverse proxy.
4. Use explicit HTTPS CORS origins; do not use * with credentials.
5. Store all secrets in a secret manager.
6. Configure logs, alerts, health checks, backups, and restoration drills.
7. Review upload validation, rate limits, retention, privacy, and incident procedures.

## Testing

From the repository root:

    python -m pytest -q
    python -m compileall -q backend
    python backend/evaluation/evaluate_ai.py
    python backend/evaluation/performance_smoke.py

Frontend checks:

    cd frontend
    npm ci
    npm run lint
    npm run build

With backend and frontend running, execute the browser suite:

    cd ..
    python -m pytest -v -rs test_civiclens_selenium.py --junitxml=selenium-results.xml

The Selenium suite covers login loading, invalid login, weak-password registration, valid Citizen login, required issue fields, issue submission/detail navigation, duplicate handling, and missing-image fallback.

Continuous integration is defined in .github/workflows/ci.yml and runs backend tests/compilation, AI evaluation, dependency auditing, frontend lint/build, and npm audit.

## Authentication and roles

- Citizen: submit, track, and verify civic issues.
- Municipal Officer: review, prioritize, route, and assign issues.
- Field Engineer: update assigned work and record resolutions.
- Administrator: manage roles, analytics, and audit visibility.

Authentication uses JWT access tokens. New passwords are validated by the frontend and backend. Existing accounts are not silently forced through migration. Backend role checks are the security boundary; hiding a frontend control is not authorization.

## AI and integrations

- Duplicate detection can use embeddings and a lexical fallback.
- Gemini is optional and disabled by default in local development.
- Images can use local static storage or Cloudinary when configured.
- Email can remain observable through the simulated in-app log when SMTP is not configured.

AI output is advisory. Issue persistence and workflow integrity must not depend on an optional AI provider. The synthetic AI evaluation fixture must not be interpreted as production model accuracy.

## Repository structure

    backend/                 FastAPI application, auth, models, routes, services, tests
    backend/routers/         Auth, issue, verification, officer, engineer, admin, analytics
    backend/evaluation/      AI evaluation and performance checks
    backend/seed_data.py     Local-only development seed data
    frontend/src/            React application source
    docs/                    Deployment, testing, security, workflow, and release records
    .github/workflows/ci.yml CI checks
    test_civiclens_selenium.py Browser-level workflow tests
    docker-compose.yml       MongoDB, backend, and frontend deployment stack

## Troubleshooting

### Frontend cannot reach the API

Confirm both services are running and open http://localhost:5173, not a static file URL:

    Invoke-WebRequest http://127.0.0.1:8000/api/health

### Backend refuses to start

For local mode, check backend/.env has APP_ENV=development, ALLOW_JSON_DB=true, and a non-empty JWT_SECRET. Production requires MongoDB and MONGODB_URI.

### Database appears empty

Local JSON data is stored under backend/data. Startup seeds only when the users collection is empty. Do not delete production data to solve a configuration issue.

### Uploads, maps, or AI are unavailable

Check /uploads, the Vite proxy, upload-directory permissions, map/network permissions, model initialization, and optional provider credentials. Review logs without exposing tokens or personal data.

## Security

- Treat seeded accounts and JSON data as disposable.
- Do not commit secrets or generated user data.
- Do not expose Swagger or database administration interfaces publicly without access controls.
- Use HTTPS, secret storage, restrictive CORS, authenticated databases, backups, monitoring, and incident procedures in production.
- Review docs/PRODUCTION_SECURITY_REVIEW.md, docs/SECURITY_REVIEW.md, and docs/DEPLOYMENT_GUIDE.md before release.
- Report suspected vulnerabilities privately to the repository owner.

## Documentation

- docs/DEMO_SCRIPT.md — Citizen to Officer to Engineer demonstration flow.
- docs/TESTING_GUIDE.md — test strategy and release checks.
- docs/DEPLOYMENT_GUIDE.md — deployment and environment guidance.
- docs/PORTABILITY_CHECKLIST.md — reproducible setup.
- docs/ISSUE_WORKFLOW.md — business workflow and status rules.
- docs/PRODUCTION_SECURITY_REVIEW.md — production security review.
- docs/RELEASE_ACCEPTANCE.md — release acceptance criteria.

## Contributing

1. Create a feature branch from the default branch.
2. Keep changes focused and preserve security controls.
3. Add or update tests for behavior changes.
4. Run backend tests, frontend lint/build, and relevant Selenium checks.
5. Do not commit secrets, local databases, uploads, release ZIPs, or generated logs.
6. Open a pull request with implementation and verification evidence.

## License

No open-source license is currently declared in this repository. Contact the repository owner before redistributing or using CivicLens outside its intended context.

