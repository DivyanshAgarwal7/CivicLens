# CivicLens AI Implementation Audit

Date: 2026-10-16  
Scope: Phase 3 inspection and implementation

## Actual implementation

### Duplicate detection

`backend/services/ai_service.py::check_duplicate_issues` now follows this path:

1. Validate and normalize title/description input.
2. Exclude resolved/closed records, malformed records, and an optional current issue identifier.
3. Apply geographic candidate filtering when both reports have valid coordinates. Missing coordinates do not crash the request; those records are compared without geographic evidence.
4. Bound candidates by `AI_DUPLICATE_MAX_CANDIDATES`.
5. Prefer a lazily loaded, cached `sentence-transformers` model using normalized embedding cosine similarity. Model loading is local-only and never occurs during application startup.
6. Fall back to scikit-learn TF-IDF cosine similarity, or token Jaccard only if scikit-learn is unavailable. This fallback is labeled `tfidf-lexical-baseline`, not semantic AI.
7. Combine similarity with supporting category and distance signals. The result is a candidate recommendation, not proof of duplication.

Matching responses expose only a bounded issue identifier, title, category, status, coarse location fields, distance, and scores. Reporter email and other private fields are not returned.

Current environment result: `sentence_transformers` is not installed and no local model artifact is available. The executed tests therefore exercised the deterministic fallback. Installing the declared dependency and provisioning `AI_EMBEDDING_MODEL` locally enables semantic inference without changing startup behavior.

### Priority recommendation

`predict_issue_priority` uses `deterministic-baseline-v1` unless `AI_USE_GEMINI=true` and a Gemini response passes strict validation. The baseline uses category severity, configured hazard terms, verification count, and duplicate-candidate count. It returns a 1–10 score, Low/Medium/High/Urgent label, department recommendation, rationale, method, and version.

This is an engineering baseline, not a trained model. The repository contains no approved labeled dataset, training pipeline, or prior evaluation evidence. AI recommendations remain separate from `approved_priority` and cannot authorize assignment.

### Optional external services

Gemini is opt-in, response-validated, and failure-safe. Vision analysis is also optional. No external model call is required for issue persistence. SMTP and AI failures do not replace the persisted business record.

## Configuration

- `AI_EMBEDDING_MODEL`: local sentence-transformers model name/path; default `all-MiniLM-L6-v2`.
- `AI_DUPLICATE_THRESHOLD`: semantic-model combined duplicate-candidate threshold; default `0.72`.
- `AI_LEXICAL_DUPLICATE_THRESHOLD`: provisional TF-IDF fallback threshold; default `0.38`. This is calibrated only against the synthetic fixture until a representative labeled dataset is approved.
- `AI_DUPLICATE_MAX_DISTANCE_METERS`: geographic candidate radius; default `400`.
- `AI_DUPLICATE_MAX_CANDIDATES`: maximum candidates scored; default `50`.
- `AI_USE_GEMINI`: opt-in external priority/vision calls; default `false`.

## README claim review

- Supported: AI-assisted duplicate warnings, priority recommendations, department suggestions, and optional image analysis interfaces.
- Not supported by evidence: trained ML accuracy, semantic inference in the current environment, Gemini availability, or production-grade model performance.
- The README should describe these as decision-support recommendations and should not imply that every local installation has a loaded semantic model.
