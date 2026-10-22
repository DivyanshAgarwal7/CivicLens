# Requirements Traceability

| Requirement area | Implementation evidence | Verification | Status |
|---|---|---|---|
| Citizen-only public registration | `backend/routers/auth_routes.py`, `backend/models.py` | `test_security_foundation.py` | Verified |
| Authenticated issue/image submission | `backend/routers/issue_routes.py`, `backend/auth.py` | Security tests and integration checklist | Partially verified; HTTP/browser gate pending |
| Duplicate decision support | `backend/services/ai_service.py`, `backend/evaluation/evaluate_ai.py` | Synthetic fixture and AI tests | Fallback only; semantic quality gate open |
| Priority recommendation and officer approval | `backend/routers/officer_routes.py`, `backend/routers/issue_routes.py` | `test_phase2_workflows.py` | Verified at route/unit level |
| Department/engineer assignment | `backend/routers/officer_routes.py` | `test_phase2_workflows.py` | Verified at route/unit level |
| Engineer status workflow and evidence | `backend/routers/engineer_routes.py` | `test_phase2_workflows.py`, security tests | Verified at route/unit level |
| Verification uniqueness and credibility | `backend/routers/verification_routes.py`, `backend/db.py` | Phase 2 regression tests | Verified at adapter/unit level |
| Notifications and email log restrictions | `backend/services/notification_service.py`, `backend/routers/notification_routes.py` | Phase 2 tests and integration checklist | Partially verified; live HTTP gate pending |
| Public response privacy | `backend/routers/issue_routes.py` | `test_phase4_integration.py` | Verified serializer boundary |
| Persistence readiness | `backend/db.py`, `backend/main.py` | `/api/health`, Compose health checks | Code verified; Mongo execution pending |
| Frontend build and static deployment | `frontend/Dockerfile`, `frontend/nginx.conf` | `npm run build` | Build verified; container pending |
| CI repeatability | `.github/workflows/ci.yml` | Workflow definition | Not executed locally |
| Accessibility and responsive UI | Frontend screens and testing guide | Browser audit checklist | Open |
| Operational deployment | `docker-compose.yml`, deployment guide | Docker/Mongo staging run | Open |
