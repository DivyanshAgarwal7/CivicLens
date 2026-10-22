# CivicLens Phase 5 Release Acceptance

Validation date: 2026-10-16  
Environment: Windows development host, Python 3.13, Node/Vite 8.3.4, JSON development persistence, no Docker daemon, no local MongoDB server, no sentence-transformers model artifact.

## Gate checklist

| # | Gate | Status | Evidence and exact command | Result / limitation |
|---:|---|---|---|---|
| 1 | Backend unit tests | PASS | `python -m pytest -q` | 18 passed, 24 deprecation warnings. |
| 2 | Backend integration tests | PASS | `python -m pytest -q`; disposable live API workflow using `Invoke-RestMethod` | Connected route journey passed in-process and live over HTTP using JSON development storage. Mongo-backed integration is separate and blocked. |
| 3 | Frontend lint and production build | PASS | `npm run lint; npm run build` | Exit 0; build passed. Existing unused-import, hook-dependency, and set-state-in-effect warnings remain. |
| 4 | Authentication and authorization regressions | PASS | `python -m pytest -q`; live seeded Citizen login and API officer/engineer tokens | Citizen registration/login, JWT flow, object ownership, officer review, assignment, and engineer transitions exercised. |
| 5 | MongoDB integration and persistence | BLOCKED | `mongod --version; mongosh --version` | Mongo executables are unavailable. JSON tests must not be treated as Mongo evidence. |
| 6 | Docker image build and startup | BLOCKED | `docker --version; docker compose version` | Docker is not installed. Use the commands in `docs/DEPLOYMENT_GUIDE.md` on a Docker-enabled host. |
| 7 | Health and readiness | PASS | `Invoke-WebRequest http://127.0.0.1:8000/api/health`; `python -c ... import main; ...` | HTTP 200 and `database: ready` confirmed in JSON development mode. Production Mongo failure behavior is code-reviewed but not runtime-executed. |
| 8 | Semantic-model runtime | BLOCKED | `python -c "import importlib.util; ..."` | `sentence_transformers` is unavailable and no local model artifact exists. Required model/configuration: `AI_EMBEDDING_MODEL` plus a locally cached model loadable with `local_files_only=True`. |
| 9 | AI evaluation quality | BLOCKED | `python backend/evaluation/evaluate_ai.py` | Synthetic fixture after fallback-threshold correction: TP=3, FP=0, FN=0, TN=2, F1=1.0. This is not approved real-world accuracy; semantic runtime and representative labeled data are missing. |
| 10 | Dependency and secret scanning | BLOCKED | `rg` secret-pattern scan; `pip-audit --version; npm audit --omit=dev --audit-level=high` | No populated secrets found. `pip-audit` is unavailable; npm audit cannot reach the registry (`ENOTFOUND`). |
| 11 | Browser workflow and accessibility | BLOCKED | In-app browser at `http://127.0.0.1:5173/` | Citizen login, issue submission, issue detail, AI rationale, and verification visibly passed. Full officer/engineer browser journey and automated accessibility scan were not completed; DOM inspection is not an accessibility certification. |
| 12 | Backup and restore | BLOCKED | No safe Mongo environment available | Procedures are documented below and in the deployment guide; no restore was run against any real database. |
| 13 | Performance testing | BLOCKED | `python backend/evaluation/performance_smoke.py` | Local duplicate-function smoke only; no API concurrency, throughput, Mongo, browser, or SRS-scale target was measured. |
| 14 | Configuration and deployment review | PASS | Static review of Dockerfiles, Compose, Nginx, `.env.example`, and CI workflow | No hard-coded runtime secrets or published Mongo port found. Runtime image/Compose validation is blocked by missing Docker. |
| 15 | Requirements traceability and documentation | PASS | Document existence check and review of required Phase 1–4 documents | Required documents exist; this acceptance report records remaining gates and evidence. |

## Live workflow evidence

The first browser session emitted a Leaflet `_leaflet_pos` teardown error during route/layer cleanup. `frontend/src/components/LeafletMap.tsx` was patched to stop transitions and clear layers before removal. A post-change route teardown produced no new Leaflet error; the full gate remains blocked only because officer/engineer browser coverage and automated accessibility scanning were not completed.

- Backend health returned HTTP 200.
- Public registration returned role `Citizen`.
- Frontend Citizen login succeeded with the documented local test account.
- Frontend issue submission created `CL-2026-50BCF59362` and navigated to its detail page.
- Public issue response did not contain `reporter_email`.
- Browser issue detail showed deterministic priority method/rationale and “Verified Unique”.
- Browser verification showed “Thank you! Your verification has been recorded”, `+1`, and duplicate-verification protection.
- Live API workflow completed officer priority approval, assignment using the authenticated engineer ID, `In Progress`, and evidence-backed `Resolved`.

## Backup and restore procedure for staging

Run only against a disposable or explicitly approved staging database:

```powershell
mongodump --uri "$env:MONGODB_URI" --out .\backup\civiclens-$(Get-Date -Format yyyyMMddHHmmss)
mongorestore --uri "$env:RESTORE_MONGODB_URI" --drop .\backup\civiclens-<timestamp>
```

After restore, verify `/api/health`, expected issue/user counts, unique indexes, and a read-only issue retrieval. Keep backup files outside source control and protect them as sensitive data.

## Acceptance decision

CivicLens is suitable for a controlled demonstration and continued staging validation. It is not accepted for production deployment from this environment because Mongo/Docker execution, semantic-model runtime, approved AI evaluation data, full accessibility validation, dependency scanning, backup/restore, and production-scale performance evidence are still open.

## Phase 6 update

The Phase 6 validation reran the available gates and recorded the blocker evidence in `docs/archive/phases/PHASE6_VALIDATION.md`. No infrastructure blocker was silently converted to a pass. CI now invokes `pip-audit` and `npm audit` on a network-enabled runner, but those scans remain unexecuted locally.
