# CivicLens Phase 4 Baseline

Date: 2026-10-16

## Scope

This baseline records the verification state before Phase 4 integration, deployment, and release-readiness work. Results are local to the available Windows development environment and are not a production certification.

## Automated checks

| Check | Result | Evidence / limitation |
|---|---|---|
| Backend tests | PASS | `python -m pytest -q`: 14 passed, 17 deprecation warnings in existing modules. |
| Backend bytecode compilation | PASS | `python -m compileall -q backend`. |
| Frontend build | PASS | `npm run build`; Vite 8.3.4, 1,936 modules transformed. |
| Frontend lint | PASS WITH WARNINGS | `npm run lint` exits 0; existing unused imports, hook dependency, and React effect warnings remain. |
| AI fixture evaluation | FAILING BASELINE | Before Phase 5 correction: 5 synthetic samples; TP=0, FP=0, FN=3, TN=2, precision=0, recall=0, F1=0, mean latency about 1,176.595 ms. The semantic threshold was incorrectly reused by the lexical fallback. |
| Secret-pattern scan | PASS | No populated JWT, Mongo, SMTP, Gemini, or Cloudinary secrets found; only source reads and `.env.example` placeholders. |
| Docker availability | NOT AVAILABLE | `docker` and `docker compose` are not installed in this environment. |
| Semantic model availability | NOT AVAILABLE | `sentence_transformers` is not installed and no local model artifact was provisioned. |
| HTTP integration client | NOT AVAILABLE | `httpx` is not installed, so FastAPI `TestClient` smoke tests were not run. |
| MongoDB availability | NOT VERIFIED AS RUNNING | The test suite used the JSON adapter; Mongo-backed integration remains an environment-dependent gate. |

## Interpretation

The application has a passing unit/regression baseline and a passing frontend production build, but it is not yet production-ready based on this baseline. The AI score is a conservative lexical-fallback result on a small synthetic fixture, not a representative model benchmark. The missing semantic model is material because the fixture includes paraphrase pairs. Docker and Mongo deployment verification must be rerun in an environment that provides those services.

## Phase 4 release gates

Before a production sign-off, rerun this baseline with:

1. a provisioned local embedding model and a reviewed, representative labeled evaluation set;
2. MongoDB with authentication, indexes, backups, and health checks enabled;
3. Docker Compose or the target orchestration platform;
4. HTTP-level integration tests against the running API and frontend;
5. accessibility and browser smoke tests against the built frontend;
6. dependency, secret, and image scans in CI.
