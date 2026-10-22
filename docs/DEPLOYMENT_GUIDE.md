# CivicLens Deployment Guide

## Required production settings

Use a secret manager or protected deployment environment for `JWT_SECRET`, `MONGO_ROOT_PASSWORD`, and any optional SMTP/Gemini/Cloudinary credentials. Set `APP_ENV=production`, `ALLOW_JSON_DB=false`, a finite `CORS_ORIGINS` list, and a MongoDB URI with authentication. Never commit `.env` files.

## Compose deployment

From the repository root:

```powershell
$env:MONGO_ROOT_PASSWORD = "generate-a-secret-outside-source-control"
$env:JWT_SECRET = "generate-a-long-random-secret"
docker compose up --build -d
docker compose ps
```

The stack starts MongoDB first, waits for its ping health check, starts FastAPI, waits for `/api/health`, and then starts the Nginx frontend on `http://localhost:8080`. Persist MongoDB data using the named volume or an external managed database. Back up MongoDB and uploaded evidence separately.

## Operational requirements

- Terminate TLS at a trusted reverse proxy or load balancer.
- Restrict network access to MongoDB; do not publish its port publicly.
- Configure log collection, alerting on health failures, backup restore drills, and resource limits.
- Provision and verify the local embedding model artifact before relying on semantic duplicate detection.
- Scan Python/npm dependencies and container images in CI and before release.
- Rotate JWT and database credentials using the deployment platform's secret manager.

## Backup and restore

Use a disposable or explicitly approved staging database for restore drills. Keep dumps outside source control and treat them as sensitive:

```powershell
mongodump --uri "$env:MONGODB_URI" --out .\backup\civiclens-$(Get-Date -Format yyyyMMddHHmmss)
mongorestore --uri "$env:RESTORE_MONGODB_URI" --drop .\backup\civiclens-<timestamp>
```

After restoration, verify `/api/health`, expected record counts, unique indexes, and read-only issue retrieval. Do not use `--drop` against production data.

Docker was unavailable during the local Phase 4 baseline, so the Compose stack remains an unexecuted deployment artifact until validated in CI/staging.
