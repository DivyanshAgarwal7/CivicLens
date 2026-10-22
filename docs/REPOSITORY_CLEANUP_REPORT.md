# CivicLens Repository Cleanup Report

Date: 2026-10-18  
Status: demonstration-ready; not production-certified

## Scope and safety checkpoint

The cleanup was performed in the existing repository; no rebuild or unrelated dependency upgrade was performed. Git metadata is absent, so no Git diff is claimed.

Before changes, the repository contained five top-level directories (`.github`, `.pytest_cache`, `backend`, `docs`, `frontend`) plus the root runtime/configuration files and six release archives. The sanitized baseline manifest and external checkpoint are stored outside the repository at:

`C:\Users\Divyansh Agarwal\.codex\visualizations\2026\10\16\01a144e0-b4b6-7e62-b5c8-68142d10b8a7\civiclens-cleanup-baseline-2026-10-18\baseline-manifest.json`

The sanitized backup is:

`C:\Users\Divyansh Agarwal\.codex\visualizations\2026\10\16\01a144e0-b4b6-7e62-b5c8-68142d10b8a7\CivicLens-cleanup-backup-2026-10-18.zip`

Backup SHA-256: `D949A446E91C6DC7856FFEF3AF0D99901BF33CF8EA50EBD9AAEAFF2589D8329F`. It contains source/configuration/docs but intentionally excludes the real `.env`, local database data, uploads, dependencies, caches, and build output.

## Baseline evidence

Before cleanup:

- `python -m pytest -q`: 22 passed, 32 warnings.
- `python -m compileall -q backend`: passed.
- `python backend/evaluation/evaluate_ai.py`: passed; synthetic fixture precision/recall/F1 were 1.0, with the documented non-benchmark warning.
- `frontend`: `npm run lint` exited 0 with existing warnings; `npm run build` passed.
- Git: unavailable; the directory is not a Git repository.
- Existing `CivicLens-demo-release-v1.0.0-phase8.zip` SHA-256: `A08A27CC87F62EACE0C0F01C95A2E01230B47E6CA70DDC3260D589E333881C20`.

## Final structure

```text
CivicLens/
├── backend/                 application, tests, evaluation, local runtime data
├── frontend/                React/Vite source, lockfile, local dependencies
├── docs/                    current setup, testing, security, release guidance
│   └── archive/phases/      retained Phase 4–8 historical records
├── .github/workflows/       CI
├── .dockerignore            safe Docker build-context exclusions
├── .gitignore
├── docker-compose.yml
├── requirements.txt
├── README.md
└── CivicLens-*.zip          retained release artifacts
```

## Changes made

### Created

- `.dockerignore`: excludes secrets, local data/uploads, dependencies, caches, build output, metadata, and release archives from the root Docker context while retaining `backend/.env.example`.
- `docs/archive/README.md`: explains the historical archive and current-status source of truth.
- `docs/REPOSITORY_CLEANUP_REPORT.md`: this report.
- External sanitized baseline manifest and backup listed above.

### Modified

- `.gitignore`: added pytest/tool caches, logs, and local release ZIP exclusions.
- `README.md`: updated the Phase 4 baseline link to its historical archive location.
- `docs/IMPLEMENTATION_PLAN.md`: updated historical Phase 4/6 paths.
- `docs/TESTING_GUIDE.md`: updated the historical baseline path.
- `docs/RELEASE_ACCEPTANCE.md`: updated the Phase 6 validation path.

### Moved, not deleted

The following historical records moved from `docs/` to `docs/archive/phases/`:

- `PHASE4_BASELINE.md`
- `PHASE4_DELIVERY_MANIFEST.md`
- `PHASE5_DELIVERY_MANIFEST.md`
- `PHASE6_VALIDATION.md`
- `PHASE6_PATCH.txt`
- `PHASE6_DELIVERY_MANIFEST.md`
- `PHASE7_PATCH.txt`
- `PHASE7_DELIVERY_MANIFEST.md`
- `PHASE8_PATCH.txt`

These records were retained for traceability. Current operational documentation remains at the `docs/` root.

### Removed

Only reproducible generated artifacts were removed:

- root `.pytest_cache/`
- `backend/__pycache__/`
- `backend/evaluation/__pycache__/`
- `backend/routers/__pycache__/`
- `backend/services/__pycache__/`
- `backend/tests/__pycache__/`
- `frontend/dist/`

The final validation regenerated some of these artifacts temporarily; they are removed again before the final archive is built.

## Deliberately retained

- `backend/.env`: preserved because it contains local configuration; it is never packaged.
- `backend/data/` and `backend/uploads/`: preserved because they may contain user-created or demonstration state; no deletion was authorized.
- `frontend/node_modules/`: preserved because it supports offline manual testing and is reproducible from the lockfile.
- All tests, fixtures, evaluation scripts, Dockerfiles, Compose, CI, lockfiles, environment examples, and source files.
- All previous release archives, including `CivicLens-demo-release-v1.0.0-phase8.zip`.

## Needs human approval

No uncertain file was deleted. A future maintainer may separately decide whether to remove `frontend/node_modules/`, local JSON data/uploads, the real `.env`, or superseded release archives after confirming they are no longer needed and retaining an external backup. Those actions were intentionally out of scope for this cleanup.

## Post-cleanup validation

- `python -m pytest -q`: 22 passed, 32 warnings.
- `python -m compileall -q backend`: passed.
- `python backend/evaluation/evaluate_ai.py`: passed with the same synthetic-fixture limitation.
- `frontend/npm run lint`: exited 0 with existing non-blocking warnings.
- `frontend/npm run build`: passed; Vite transformed 1936 modules.
- Docker/Mongo live checks: not run because the tools/services are unavailable locally.
- Dependency audits: not rerun; network/tooling prerequisites remain unavailable.
- Browser/manual workflow: not rerun as part of repository cleanup.

## Release archive integrity

The current Phase 8 demo archive was not modified. Its final hash must remain `A08A27CC87F62EACE0C0F01C95A2E01230B47E6CA70DDC3260D589E333881C20`. The cleanup archive is separate and must contain the complete runnable source/configuration/docs while excluding `.env`, local data/uploads, dependency directories, caches, build output, logs, and ZIP files.

## Rollback

1. Restore the sanitized source/configuration/docs backup from the external ZIP into a new disposable checkout; do not overwrite the active `.env`, data, or uploads without explicit approval.
2. Move the nine files from `docs/archive/phases/` back to `docs/` if the previous flat documentation layout is required.
3. Recreate generated output with `python -m pytest -q`, `python -m compileall -q backend`, and `frontend\npm ci; frontend\npm run build`.
4. Leave the current release archives untouched; the baseline manifest records their sizes and hashes for comparison.
