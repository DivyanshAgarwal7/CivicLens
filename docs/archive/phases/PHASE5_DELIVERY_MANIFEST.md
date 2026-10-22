# Phase 5 Delivery Manifest

The workspace has no Git metadata, so this is the truthful changed-file manifest for the Phase 5 validation turn. No files were deleted.

## Modified files

- `backend/config.py` — added `AI_LEXICAL_DUPLICATE_THRESHOLD` configuration.
- `backend/.env.example` — documented the lexical fallback threshold.
- `backend/services/ai_service.py` — separated semantic and lexical thresholds; explicit caller thresholds remain honored.
- `backend/tests/test_ai_service.py` — added regression coverage proving the fallback detects the labeled pothole pair.
- `docs/AI_IMPLEMENTATION_AUDIT.md` — documented threshold semantics and provisional calibration status.
- `docs/PHASE4_BASELINE.md` — recorded the pre-Phase-5 threshold defect accurately.
- `frontend/src/components/LeafletMap.tsx` — cancelled Leaflet transitions and cleaned layers before route teardown.
- `docs/DEPLOYMENT_GUIDE.md` — added safe staging backup/restore procedure.
- `docs/IMPLEMENTATION_PLAN.md` — recorded Phase 5 completion and open release gates.

## Created files

- `docs/RELEASE_ACCEPTANCE.md` — final 15-gate checklist, evidence, exact commands, and acceptance decision.
- `docs/PHASE5_DELIVERY_MANIFEST.md` — this manifest.

## Before/after evidence

- Before: synthetic fallback evaluation TP=0, FP=0, FN=3, TN=2, F1=0.0 because the semantic `0.72` threshold was reused by TF-IDF.
- After: synthetic fallback evaluation TP=3, FP=0, FN=0, TN=2, F1=1.0 with a separately configured provisional `0.38` lexical threshold.
- The after-result remains synthetic and is not production AI accuracy evidence.
- Final backend tests: 18 passed.
- Final frontend lint/build: exit 0; lint warnings remain.
- Live local browser/API workflows: Citizen login, issue submission, detail, verification, officer review, assignment, engineer progress, and evidence-backed resolution exercised successfully.
- First browser session exposed a Leaflet `_leaflet_pos` teardown error; cleanup was patched and route teardown was re-exercised with no new Leaflet error.
- Docker, MongoDB, semantic model, dependency audit, accessibility certification, backup restore, and production-scale performance remain blocked or incomplete as recorded in `docs/RELEASE_ACCEPTANCE.md`.
