# CivicLens Engineering Audit

Date: 2026-10-16  
Scope: repository inspection before Cycle 1 / Phase 1 implementation  
Lifecycle model: Spiral Model

## Repository inventory

- Backend: `backend/main.py`, `backend/config.py`, `backend/db.py`, `backend/auth.py`, `backend/models.py`
- API routers: authentication, issues, verification, officer, engineer, administrator, analytics, notifications
- Services: AI analysis, audit logging, notification/email logging
- Frontend: React 19 + TypeScript + Vite 8, Leaflet, API client in `frontend/src/services/api.ts`
- Persistence: PyMongo when configured, otherwise an embedded JSON adapter
- Tests: no repository test files or test configuration were found during the initial inventory
- Deployment: no Docker or CI configuration was found during the initial inventory

## Verified findings

| Severity | Finding and evidence | Affected paths | Proposed Phase 1 fix |
| --- | --- | --- | --- |
| Critical | Public `POST /api/auth/register` persists `req.role` and `req.department`; the frontend also submits a role selector. | `backend/models.py:7-13`, `backend/routers/auth_routes.py:10-35`, `frontend/src/screens/RegisterScreen.tsx` | Remove public role assignment from the request contract and force `Citizen` on the server. Add regression tests. |
| High | Passwords use salted SHA-256, a fast password hash not suitable for password storage. | `backend/auth.py:1-25`, `backend/seed_data.py:3,81-114` | Use bcrypt through the installed `passlib` dependency; verify legacy SHA-256 hashes and migrate them after successful login. |
| High | MongoDB connection failure or missing URI silently selects the JSON store regardless of environment. | `backend/config.py:14`, `backend/db.py:132-159` | Add explicit `APP_ENV`; permit JSON only in development/test and fail startup in production. |
| High | CORS allows every origin while credentials are enabled. | `backend/main.py:33-40` | Parse explicitly configured frontend origins and reject wildcard production configuration. |
| High | Image upload is public, checks only the filename extension, has no size/content validation, and leaves partial files on failures. | `backend/routers/issue_routes.py:17-39`, `backend/main.py:42` | Require authentication, enforce byte limits, verify decoded image content with Pillow, use generated safe names, and clean up invalid/failed uploads. |
| High | Field engineers can update any issue because task update checks only role; department-wide task listing also exposes unrelated assignments. | `backend/routers/engineer_routes.py:12-23,26-87` | Restrict task visibility and updates by assignment/department, validate allowed transitions, and add tests. |
| High | Issue numbers are generated from `count_documents()+1`, which can collide under concurrent requests. | `backend/routers/issue_routes.py:97-101` | Use a UUID-backed public identifier for new reports while preserving existing seeded identifiers. |
| Medium | Analytics summary/heatmaps and department listing have no authorization dependency. | `backend/routers/analytics_routes.py:7-80`, `backend/routers/admin_routes.py:59-62` | Restrict administrative/operational data to authorized roles. |
| Medium | JWT validation checks signature/expiry through PyJWT but does not require a consistent issuer/type claim set. | `backend/auth.py:28-37` | Add explicit token type and issuer claims and validate required claims. |
| Medium | Verification count is recomputed safely after duplicate checking, but credibility adds `v_count` to the prior score on every vote, causing repeated inflation. | `backend/routers/verification_routes.py:40-60` | Recalculate from a stable base/report trust signal in the workflow cycle; retain as a Cycle 2 item unless required by tests. |
| Medium | No automated tests were present, so authentication, authorization, upload, and persistence behavior are currently unverified. | repository-wide | Add focused backend regression tests in Phase 1. |

## Potential risks and assumptions

- `bcrypt` is available in the current Python environment; it is now declared explicitly so clean environments install the same implementation.
- Existing JSON data may contain legacy `salt:sha256` hashes. Successful login migration is safe; users with malformed hashes require password reset.
- The current seeded staff accounts are development/demo data. Production seeding must be disabled.
- Cloudinary is configured but the current implementation stores local upload paths; Phase 1 secures the existing local path without changing the storage architecture.
- Public issue listing and issue details appear intentionally community-visible; personal reporter fields must not be exposed in a later privacy pass.

## User journey trace

1. React login/register calls `frontend/src/services/api.ts` -> `/api/auth/*` -> `backend/routers/auth_routes.py` -> `users` collection -> JWT.
2. Report form optionally uploads to `/api/issues/upload-image`, then duplicate-checks, then creates an issue at `/api/issues`.
3. Issue creation reads `issues`, calls `backend/services/ai_service.py`, persists the issue, then sends notifications and an audit record.
4. Community verification writes `verifications`, updates the issue, then notifies the reporter.
5. Officer assignment updates an issue; engineer status updates then persist resolution and notify the reporter.

