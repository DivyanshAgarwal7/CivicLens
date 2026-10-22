# CivicLens Implementation Plan

Lifecycle model: Spiral Model  
Current cycle: Cycle 4 — integration, deployment readiness, and final qualification  
Current phase: Phase 5 — final release validation, defect closure, and acceptance evidence

## Cycle 1 / Phase 1 checklist

- [x] Audit repository and trace core user journeys.
- [x] Document verified defects and assumptions in `docs/ENGINEERING_AUDIT.md`.
- [x] Force public registration to create Citizens only.
- [x] Upgrade password hashing and migrate legacy hashes on successful login.
- [x] Harden JWT required claims and role checks.
- [x] Restrict CORS by configured origins.
- [x] Authenticate and validate image uploads.
- [x] Prevent production fallback to JSON persistence.
- [x] Add safe MongoDB indexes and collision-safe issue identifiers.
- [x] Close engineer object-level authorization gaps and validate status transitions.
- [x] Add regression tests and run available frontend/backend checks.
- [x] Review final diff and record unresolved risks.

## Cycle 2 / Phase 2 checklist

- [x] Verify Phase 1 implementation and run the existing checks.
- [x] Document the issue lifecycle and scoring assumptions in `docs/ISSUE_WORKFLOW.md`.
- [x] Enforce unique issue/verification references in MongoDB and the JSON adapter.
- [x] Recalculate verification-derived values from authoritative records.
- [x] Separate AI priority recommendation from officer-approved priority.
- [x] Validate departments, engineer roles, department relationships, and resolution evidence.
- [x] Enforce backend status transitions and engineer ownership.
- [x] Make notifications idempotent and nonessential to core transaction success.
- [x] Restrict notification email logs and notification mutations to authorized owners.
- [x] Add/complete Phase 2 regression tests and run the full available suite.
- [x] Review final diff, package changed files, and record remaining risks.

### Phase 2 acceptance criteria

- Duplicate citizen verification requests produce one authoritative verification and one count increment.
- Credibility is deterministic for a given base score and authoritative verification count.
- Assignment is rejected until an authorized officer approves a priority.
- Invalid departments, cross-department engineers, and unauthorized resolution updates are rejected.
- Only `Assigned -> In Progress -> Resolved` engineer transitions are accepted, with resolution evidence required.
- Repeated notification events do not create duplicate in-app notifications.
- Citizens cannot read or mutate another user’s notifications; email logs are administrator-only.

## Acceptance criteria

- A public registration request containing any privileged role results in a Citizen account.
- Legacy SHA-256 accounts can log in once and are upgraded to the configured modern hash format.
- Invalid, expired, or missing JWTs are rejected; insufficient roles receive 403.
- Production startup fails clearly without MongoDB; JSON persistence is limited to explicit development/test mode.
- Uploads require an authenticated user, obey a size limit, and contain a decodable supported image.
- A field engineer cannot update another engineer's task or make an invalid transition.
- New issue identifiers remain unique without using a collection count.
- Regression tests cover the role-escalation, authentication, authorization, upload, and database-mode boundaries.

## Later Spiral cycles

- Cycle 2: correct reporting, verification, assignment, resolution, notification atomicity, and status workflow.
- Cycle 3: AI/ML reliability and evaluation — implemented in this phase.
- Cycle 4: analytics privacy, reliability, performance evidence, Docker/CI/deployment, and final polish.

## Cycle 3 / Phase 3 checklist

- [x] Audit actual AI algorithms, dependencies, claims, and limitations.
- [x] Add lazy cached sentence-transformers integration with safe local-only loading.
- [x] Add deterministic TF-IDF/lexical fallback with explicit method labeling.
- [x] Bound candidates, filter geography, exclude current records, and sanitize matches.
- [x] Keep priority recommendation separate from officer approval and record method/version.
- [x] Add synthetic, clearly labeled duplicate-pair evaluation and reproducible metrics.
- [x] Add AI, fallback, priority, and workflow regression tests.
- [ ] Provision a local sentence-transformers model and run a real semantic smoke test.
- [x] Review final diff and record remaining Phase 3 limitations.

## Cycle 4 / Phase 4 checklist

- [x] Record the baseline test/build/lint/compile/evaluation environment in `docs/archive/phases/PHASE4_BASELINE.md`.
- [x] Add connected integration coverage for evaluation metrics and public response privacy boundaries.
- [x] Remove reporter identity from public issue list/detail responses.
- [x] Make the health endpoint report persistence readiness and reject production wildcard CORS.
- [x] Add backend/frontend container definitions and Mongo-backed Compose health dependencies.
- [x] Add CI configuration for backend regression/evaluation and frontend lint/build.
- [x] Add a bounded local performance smoke script with explicit scope limitations.
- [x] Add testing, deployment, security, and requirements traceability documentation.
- [ ] Run Docker/Mongo/browser/accessibility checks in an environment that provides those services.
- [ ] Provision and evaluate the semantic model on a reviewed representative dataset.
- [ ] Complete dependency/image scanning and obtain an operational production approval.

## Cycle 4 / Phase 5 checklist

- [x] Re-run the complete available backend/frontend/evaluation baseline before changes.
- [x] Execute live local HTTP and browser checks for Citizen submission, detail, verification, and workflow transitions.
- [x] Diagnose and correct the lexical fallback threshold defect without changing fixture labels.
- [x] Add a release-gate checklist with exact commands, evidence, dates, prerequisites, and limitations.
- [x] Document backup/restore, secret rotation, health diagnosis, and recovery procedures.
- [x] Package the release-validation files separately from the Phase 4 archive.
- [ ] Run MongoDB persistence/index/concurrency checks on a disposable Mongo instance.
- [ ] Build/start containers and verify frontend/backend/Mongo communication.
- [ ] Provision the semantic model and run runtime/dimension/latency checks.
- [ ] Run dependency/image scans, approved-data AI evaluation, automated accessibility, and staging backup restore.

## Cycle 4 / Phase 6 checklist

- [x] Reconfirm the Phase 5 baseline and rerun all locally available checks.
- [x] Create `docs/archive/phases/PHASE6_VALIDATION.md` with blocker prerequisites, exact commands, results, and risks.
- [x] Verify the lexical fallback correction and synthetic metric behavior remain stable.
- [x] Recheck the Leaflet teardown correction and record the browser limitation honestly.
- [x] Add dependency audit commands to CI without claiming local scan completion.
- [ ] Execute disposable MongoDB integration and backup/restore validation.
- [ ] Build and run Docker Compose with MongoDB and verify service failure/recovery behavior.
- [ ] Provision and execute the configured semantic embedding model.
- [ ] Run approved-data AI evaluation, automated accessibility, and API/load performance validation.

## Cycle 4 / Phase 7 checklist

- [x] Re-run the available baseline checks before handover changes.
- [x] Correct the clean-checkout Docker/CI dependency path to the actual root `requirements.txt`.
- [x] Document verified Python/Node versions, environment variables, ports, startup commands, JSON demo mode, reset precautions, and troubleshooting.
- [x] Create the role-aware `docs/DEMO_SCRIPT.md` with evidence and limitations.
- [x] Create `docs/PORTABILITY_CHECKLIST.md` and remove seeded passwords from README documentation.
- [x] Package the Phase 7 handover files without overwriting earlier release archives.
- [ ] Re-run Docker/Mongo/semantic/dependency/accessibility/backup/load gates on provisioned infrastructure.

## Cycle 4 / Phase 8 checklist

- [x] Re-run backend tests, compile checks, AI evaluation, frontend lint/build, and performance smoke.
- [x] Independently review security boundaries, lifecycle invariants, Docker/CI paths, AI claims, and archive exclusions.
- [x] Close public verification identity/trust-score exposure and add regression coverage.
- [x] Produce final demo release and audit reports with explicit PASS/BLOCKED/NOT RUN results.
- [x] Produce a new versioned demonstration archive without overwriting earlier phase archives.
