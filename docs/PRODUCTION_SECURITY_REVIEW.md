# CivicLens Phase 9 — Production Security Review

## Review result

The release is suitable for controlled demonstration with the existing deployment configuration, but it is not a claim of a fully hardened public internet deployment. Existing authentication, role checks, password hashing, JWT validation, upload validation, CORS allow-listing, database production guard, and secret exclusion from release archives were retained.

## Addressed in this phase

- Issue and resolution image URLs are now allow-listed to owned local upload basenames before public API exposure.
- Officer and engineer issue list responses now use the public issue serializer, removing reporter identity, email, password-related fields, and unsafe image sources from those responses.
- Nginx adds `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: strict-origin-when-cross-origin`, and a restrictive geolocation `Permissions-Policy`.
- Seed data no longer introduces third-party stock-image dependencies or misleading evidence.
- Release packaging excludes the real backend `.env`, databases, uploads, dependency directories, build output, caches, and logs.

## Existing controls verified by source inspection

- Public registration cannot select a privileged role.
- Passwords are hashed and never returned; legacy hashes are migrated on successful login.
- JWTs require valid claims and expiration.
- Role-protected officer, engineer, admin, audit, analytics, and issue operations remain enforced.
- Uploads require authenticated access, an allowed MIME type, a UUID filename, a size limit, and Pillow verification.
- Production configuration rejects unsafe JSON fallback and wildcard CORS.
- Docker Compose does not publish the MongoDB port; the backend image runs as a non-root user.

## Remaining risks and blocked checks

These are documented rather than hidden behind a false PASS:

- Authentication tokens remain in browser local storage under the existing architecture; an XSS compromise could expose a session. Moving to secure, same-site cookies needs an explicit authentication-design decision.
- `/uploads` remains intentionally reachable through the web tier for public civic evidence. API responses no longer expose arbitrary external paths, but direct access control and retention policy for uploaded evidence should be decided before a privacy-sensitive public deployment.
- There is no application-wide rate limiter in the current dependency set. Add infrastructure/API-gateway throttling before public launch.
- HTTPS termination, HSTS, CSP compatibility, reverse-proxy request limits, and production MongoDB authorization/TLS require deployment-environment validation.
- Dependency vulnerability scans (`pip-audit`, `npm audit`) and live service scans were not asserted because the required scanners/networked service were not available in the validation environment.
- Browser viewport and assistive-technology validation were not run in this pass.

## Logging and privacy

Timing and operational logs must contain durations, status, and safe identifiers only. Passwords, JWTs, upload contents, and unnecessary personal data must not be logged. Existing warning output includes deprecation warnings but no secret values were emitted by validation.
