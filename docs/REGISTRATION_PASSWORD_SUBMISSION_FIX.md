# Registration, password, and submission performance fix

Date: 2026-10-16

## Root causes

- Registration and login inputs had no stable `id`/`name`/`autocomplete` metadata. The browser therefore used heuristics across nearby email, phone, and password controls. The backend contract itself expects `email` and `password` for login, while registration stores distinct `email`, `phone`, `full_name`, and `password_hash` fields.
- Registration accepted an eight-character password and had no confirmation field. The backend and frontend now share the 12-character mixed-class policy; existing password hashes remain valid for login.
- Issue creation ran duplicate analysis once in the frontend pre-check and again in the backend create route. After persistence, synchronous in-app/email notification work could add more delay. Missing optional AI dependencies could also delay the first request during heavyweight import.

## Changes

- Added stable auth field names, IDs, appropriate input types, and `autocomplete` values.
- Added full-name and password-confirmation controls; frontend validation now blocks weak/mismatched values.
- Added backend password validation with useful Pydantic messages and optional confirmation compatibility for API clients.
- Added insert-result normalization for both JSON and PyMongo adapters in registration and issue creation.
- Reused the authenticated duplicate pre-check result for the immediate create request; the server still performs its own check when no pre-check result is supplied.
- Deferred optional issue notifications with FastAPI `BackgroundTasks` after issue persistence and response preparation.
- Added safe timing logs for duplicate analysis, priority analysis, persistence, and total issue creation. Logs contain no password, token, title, email, or phone.
- Added bounded frontend request timeouts, duplicate-submit protection, and visible submission stages/errors.
- Added a local-model cache check before importing sentence-transformers, preserving the lexical fallback when weights are unavailable.

## Manual verification

1. Start the backend and frontend using the existing setup instructions.
2. Register with `Aarav Sharma`, `aarav.sharma@example.com`, `+919823011223`, and a disposable password such as `CivicLens-demo1!`; confirm the password-manager identifies email/phone/password separately.
3. Try a short, whitespace-only, class-missing, and mismatched-confirmation password; each should be rejected before submission. Repeat against `/api/auth/register` to verify backend enforcement.
4. Sign in with the registered email and password; confirm the request body uses `{ email, password }` and no password is displayed or logged.
5. Submit a valid issue. Observe “Checking nearby reports…” then “Saving your report…”, the duplicate decision if applicable, and success only after the create response. Repeat-clicking the button must not create two reports.
6. Temporarily make the duplicate/AI path unavailable; the issue should still persist with an explicit unavailable/fallback AI method. Notification delivery may complete after the response.

## Evidence

- Backend: 22 tests passed; compileall passed.
- Frontend: lint exits 0 with pre-existing warnings; production build passed.
- Performance smoke: 20 samples completed with p50 3.203 ms, p95 5241.021 ms, mean 264.734 ms. This is an in-process duplicate-detection smoke test, not an API/Mongo/concurrency benchmark; the p95 includes one-time dependency initialization.

Remaining risks are the existing frontend lint warnings, deprecation warnings, and unavailable Docker/Mongo/external dependency-scan/live-browser gates.
