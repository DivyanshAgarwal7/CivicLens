# CivicLens Phase 4 Security Review

## Verified controls

- Public registration cannot create privileged accounts.
- Passwords use bcrypt, with one-time legacy SHA-256 migration.
- JWT expiry, issuer/type claims, role checks, and object-level engineer ownership are enforced.
- Production refuses JSON persistence and requires MongoDB; Mongo indexes protect users, issues, and verifications.
- Uploads require authentication, allow only supported image types, enforce a byte limit, and verify image content.
- Public issue responses now omit reporter IDs, reporter email, and unrelated internal fields.
- Notification reads/mutations and email logs are access-controlled; audit/analytics routes are restricted.
- Production wildcard CORS is rejected; configured origins remain explicit.

## Residual risks and release actions

- Mongo authentication, backup/restore, TLS, and network policy require staging verification.
- Uploaded media is served through a static path; review whether issue evidence is public or should use signed, authorized URLs for the deployment's privacy policy.
- Rate limiting, abuse detection, and account lockout are not demonstrated in the local baseline.
- Dependency, container, and secret scanning must run in CI; local pattern scanning is not a substitute.
- The AI fallback has no semantic guarantee and the current synthetic fixture produces zero recall; provision and evaluate a reviewed model/dataset before enabling a strict AI quality claim.
- Browser accessibility and security headers require a deployed environment check.

No production security approval is granted by this document; it is a review record and release checklist.
