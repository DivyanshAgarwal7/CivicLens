# Final demonstration archive manifest

Archive: `CivicLens-demo-release-v1.0.0-phase8.zip`

Included roots:

- `backend/` source, tests, evaluation fixtures/scripts, Dockerfile, and `.env.example`
- `frontend/` source, public assets, configuration, Dockerfile, nginx config, `package.json`, and `package-lock.json`
- `docs/` phase records, final audit, final demo guide, and this manifest
- `.github/` CI workflow
- `README.md`, `requirements.txt`, `docker-compose.yml`, `.gitignore`

Explicitly excluded:

- `.env` and all populated secret/config files
- `backend/data/`, `backend/uploads/`, and any local/private records
- `node_modules/`, `dist/`, `.vite/`, `.pytest_cache/`, `__pycache__/`, `.pyc`
- logs, temporary files, previous ZIP archives, and Git metadata

The archive is intended to unpack into a new directory and follow `docs/FINAL_DEMO_RELEASE.md`. The source checkout remains unchanged apart from the documented Phase 8 source/docs edits.
