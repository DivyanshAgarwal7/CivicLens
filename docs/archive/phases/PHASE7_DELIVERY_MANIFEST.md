# Phase 7 Delivery Manifest

The workspace has no Git metadata. No files were deleted and no previous release ZIP was overwritten.

## Modified files

- `backend/Dockerfile` — corrected clean-checkout dependency installation to use root `requirements.txt`.
- `.github/workflows/ci.yml` — corrected backend install/audit paths for the `backend` working directory.
- `README.md` — added reproducible setup/handover guidance and removed seeded passwords from the role table.
- `docs/PHASE6_VALIDATION.md` — corrected dependency-scan commands to the actual root requirements path.
- `docs/IMPLEMENTATION_PLAN.md` — added Phase 7 checklist.

## Created files

- `docs/DEMO_SCRIPT.md` — verified role-aware demonstration workflow.
- `docs/PORTABILITY_CHECKLIST.md` — portability, setup, troubleshooting, and recovery checklist.
- `docs/PHASE7_PATCH.txt` — focused patch excerpt.
- `docs/PHASE7_DELIVERY_MANIFEST.md` — this manifest.

## Verification

- Backend: 18 passed, 24 warnings.
- Python compilation: passed.
- Frontend lint/build: passed with existing warnings.
- AI evaluation: synthetic fallback F1=1.0; semantic inference not executed.
- Docker, MongoDB, semantic runtime, dependency scanning, accessibility, backup/restore, and load testing remain blocked as documented.
