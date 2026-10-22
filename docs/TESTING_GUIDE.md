# CivicLens Testing Guide

## Local checks

From the repository root:

```powershell
python -m pytest -q
python -m compileall -q backend
python backend/evaluation/evaluate_ai.py
python backend/evaluation/performance_smoke.py
cd frontend
npm ci
npm run lint
npm run build
```

The historical baseline is retained in `docs/archive/phases/PHASE4_BASELINE.md`. Lint warnings are currently non-blocking, but they should be reduced before a strict UI quality gate is enabled.

## Integration checks

With MongoDB and Docker available:

1. Set `MONGO_ROOT_PASSWORD` and `JWT_SECRET` in a local, uncommitted environment.
2. Run `docker compose up --build`.
3. Confirm `/api/health` returns HTTP 200 and `database: ready`.
4. Register as a Citizen and verify that a privileged role in the request is ignored.
5. Submit an issue, verify it appears without reporter email in public issue responses, then review priority as an officer.
6. Assign an engineer from the matching department, update through `In Progress`, and resolve only with evidence.
7. Confirm notification idempotency, ownership restrictions, audit entries, and the officer/admin dashboards.
8. Run keyboard-only navigation, visible-focus, heading/label, color-contrast, responsive-layout, and screen-reader smoke checks in the built frontend.

## AI evaluation

`backend/evaluation/duplicate_pairs.json` is a synthetic demonstration fixture. Review labels and expand it with representative, privacy-safe, human-reviewed pairs before using precision/recall as a release criterion. The evaluator reports its method mix so lexical fallback results cannot be confused with semantic-model results.

## Failure evidence

Do not convert unavailable infrastructure into a pass. If Docker, MongoDB, a browser automation runner, or the embedding model is unavailable, record the blocked gate and rerun it in CI or the target staging environment.
