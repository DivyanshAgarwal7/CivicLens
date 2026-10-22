# CivicLens Phase 6 Validation

Validation date: 2026-10-16  
Environment: Windows development host, Python 3.13, Node/Vite 8.3.4. No Docker daemon, MongoDB server, local sentence-transformers artifact, or pip-audit executable is installed.

## Baseline confirmation

| Check | Status | Command and result |
|---|---|---|
| Backend regression suite | PASS | `python -m pytest -q` → 18 passed, 24 deprecation warnings. |
| Python compilation | PASS | `python -m compileall -q backend`. |
| Frontend lint/build | PASS | `npm run lint; npm run build` → exit 0; lint warnings remain; Vite build passed with 1,936 modules. |
| AI evaluation | PASS | `python backend/evaluation/evaluate_ai.py` → synthetic TP=3, FP=0, FN=0, TN=2, F1=1.0; methods are TF-IDF fallback/unavailable, not semantic inference. |
| Performance smoke | PASS | `python backend/evaluation/performance_smoke.py` → local duplicate-function p50 3.486 ms, p95 4,000.666 ms, 20 samples; not an API/load test. |

## Remaining blocker matrix

| Blocker | Status | Prerequisites | Exact validation commands | Actual result / unresolved risk |
|---|---|---|---|---|
| MongoDB integration | BLOCKED | Docker or disposable authenticated MongoDB | `mongod --version; mongosh --version`; then `docker compose up -d mongo`, API tests, stop/restart checks | Both Mongo executables and Docker are unavailable. JSON adapter evidence is not Mongo evidence. |
| Docker deployment | BLOCKED | Docker Engine and Compose | `docker compose build`; `docker compose up -d`; `docker compose ps`; `docker compose logs`; health/API/browser checks | `docker` is not installed. Container startup, image permissions, persistence, and failure behavior remain unverified. The Phase 7 review corrected a clean-checkout dependency-path defect in the Dockerfile/CI references. |
| Semantic model runtime | BLOCKED | `sentence_transformers` and locally cached `AI_EMBEDDING_MODEL` artifact | `python -c "from sentence_transformers import SentenceTransformer; ..."`; run representative smoke/evaluation | `sentence_transformers` is unavailable. No semantic dimensions, inference latency, or model reuse were measured. |
| Approved AI quality | BLOCKED | Privacy-reviewed representative labeled duplicate dataset | `python backend/evaluation/evaluate_ai.py --fixture <approved-fixture>` after fixture support is provisioned | Synthetic fixture is internally consistent and now detects its three positives, but F1=1.0 is not real-world accuracy. |
| Dependency vulnerability scan | BLOCKED | Network/package-index access and scanner tooling | `pip-audit -r requirements.txt`; `cd frontend; npm audit --audit-level=high` | `pip-audit` missing; npm audit failed with registry DNS `ENOTFOUND`. No vulnerability conclusion is made. |
| Secret scan | PASS | None | `rg` secret-pattern scan over source excluding generated data | No populated runtime secrets found; only environment reads/placeholders. |
| Full browser workflow/accessibility | BLOCKED | Stable backend, browser automation, accessibility scanner | Run Citizen, officer, engineer, admin journeys; axe/keyboard/screen-reader checks | Citizen login/submission/detail/verification passed in-browser. Full role coverage and automated accessibility scan remain undone. |
| Backup/restore execution | BLOCKED | Disposable authenticated MongoDB and separate restore target | `mongodump`; `mongorestore` into separate DB; record/index checks | Procedure is documented, but no safe Mongo environment exists. No restore was attempted. |
| Production performance | BLOCKED | Running Mongo-backed API and load runner | API latency/throughput test with stated concurrency and dataset size | Only 20 local duplicate-function calls were measured; no scalability claim is supported. |

## Defects closed in Phase 6

No new backend or deployment defect was found in the available environment. Existing Phase 5 fixes were revalidated:

- The separate lexical duplicate threshold remains active and the regression suite passes.
- The Leaflet teardown cleanup remains in the source and the post-patch route teardown produced no new `_leaflet_pos` error.
- CI now includes reproducible dependency audit commands for a network-enabled runner.

## Reproducible unblock procedure

On a Docker-enabled staging runner with network access:

```powershell
$env:MONGO_ROOT_PASSWORD = "use-a-secret-manager-value"
$env:JWT_SECRET = "use-a-secret-manager-value"
docker compose build
docker compose up -d
docker compose ps
docker compose logs --no-color backend mongo
Invoke-WebRequest http://localhost:8080/api/health
pip-audit -r requirements.txt
cd frontend
npm audit --audit-level=high
```

Then provision the model named by `AI_EMBEDDING_MODEL` into the runtime's local cache, run the semantic smoke test and approved dataset evaluation, execute a disposable `mongodump`/`mongorestore`, and run browser/accessibility/load tests against the running stack. Do not mark a gate passed from configuration presence alone.

## Decision

Phase 6 closes no infrastructure blocker because the required services are absent. The evidence supports “Demonstration-ready” only. Production acceptance remains blocked by Mongo/Docker execution, semantic runtime, approved AI data, dependency scanning, full accessibility, backup/restore, and production-scale performance evidence.
