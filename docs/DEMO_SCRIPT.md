# CivicLens Demonstration Script

This script targets the disposable development profile only. It does not use MongoDB, Docker, external Gemini, SMTP, or Cloudinary. Do not run it against production data.

## Demo setup

1. Follow the local setup in `README.md` and `docs/PORTABILITY_CHECKLIST.md`.
2. Start the backend on `http://127.0.0.1:8000` and frontend on `http://localhost:5173`.
3. Confirm `GET http://127.0.0.1:8000/api/health` returns `status: healthy` and `database: ready` for the JSON development store.
4. Use a newly registered Citizen for the demo. The local seed also provides one account per staff role; credentials are intentionally not repeated here. For a disposable run, inspect `backend/seed_data.py` locally or provision staff through the Administrator UI/API.

## Workflow

### 1. Citizen registration and authentication

- Role: Citizen.
- Preconditions: Backend and frontend are running; JSON development mode is enabled.
- Action: Open Register, enter a disposable email and an 8–72 character password, and submit. Log out and sign back in.
- Expected result: Registration and login succeed; the account is shown as `Citizen`. A submitted privileged role cannot escalate the account.
- Evidence: `POST /api/auth/register`, `POST /api/auth/login`, and `GET /api/auth/me`; audit log entries are created.
- Limitation: This is local authentication with the configured development secret, not a production identity provider.

### 2. Report an issue

- Role: Citizen.
- Preconditions: Authenticated Citizen; report form available.
- Action: Select a category, enter a title and detailed description, choose a map location, enter address/ward, and optionally upload a JPEG, PNG, or WebP image.
- Expected result: The form validates required fields, uploads are authenticated and content-checked, and the issue detail page opens after submission.
- Evidence: `POST /api/issues/check-duplicate`, `POST /api/issues`, and `GET /api/issues/{id}`. The public response omits reporter identity fields.
- Limitation: Vision analysis is optional and only enabled with `AI_USE_GEMINI=true`; local default is deterministic priority support.

### 3. Duplicate decision support

- Role: Citizen.
- Preconditions: At least one nearby open issue exists.
- Action: Submit a description similar to an existing issue, then inspect the duplicate decision-support result.
- Expected result: The UI explains whether a likely duplicate was found and offers support-existing or proceed-anyway behavior when a match is returned.
- Evidence: Result fields include `method`, `semantic_model_available`, `threshold`, `confidence`, `rationale`, and sanitized potential matches.
- Limitation: Without a locally cached sentence-transformers model, the active method is TF-IDF lexical fallback. A synthetic F1 of 1.0 is not real-world model accuracy.

### 4. Issue tracking and community verification

- Role: Citizen.
- Preconditions: An issue exists and is visible on the dashboard.
- Action: Open issue details and select `Verify This Issue`; attempt the same verification again.
- Expected result: The first action increments the verification count and credibility score; the second is rejected as a duplicate.
- Evidence: `POST /api/issues/{id}/verify`, verification history, notification/audit records.
- Limitation: The JSON store is disposable and local.

### 5. Officer priority review and assignment

- Role: Municipal Officer.
- Preconditions: Staff account is provisioned; a reported issue exists.
- Action: Open the Officer Dashboard, review the AI recommendation, approve or adjust priority, select a matching department and engineer, and assign.
- Expected result: Assignment is rejected until priority review is complete; matching department/engineer validation succeeds; Citizen and Engineer notifications are created.
- Evidence: `POST /api/officer/issues/{id}/priority-review`, `GET /api/officer/engineers`, `POST /api/officer/issues/{id}/assign`, audit logs.
- Limitation: The officer-approved priority is authoritative for workflow routing; AI remains advisory.

### 6. Engineer progress and resolution

- Role: Field Engineer.
- Preconditions: The issue is assigned to the logged-in engineer.
- Action: Open Engineer Portal, move the issue from `Assigned` to `In Progress`, then resolve it with completion notes and evidence image URL.
- Expected result: Ownership and transition checks pass; resolution without evidence is rejected; successful resolution records evidence and notifies the Citizen.
- Evidence: `POST /api/engineer/tasks/{id}/status`, issue status history, resolution object, notification and audit records.
- Limitation: Evidence upload requires a real supported image before its URL is used in a production-like demo.

### 7. Citizen notification and final status

- Role: Citizen.
- Preconditions: Officer/Engineer workflow has changed the issue.
- Action: Return to Citizen Dashboard and open the notification bell and issue detail.
- Expected result: Status changes and final resolution are visible; notification unread count updates.
- Evidence: `GET /api/notifications`, `GET /api/issues/{id}`.
- Limitation: Email delivery is simulated/logged locally unless SMTP is explicitly configured.

### 8. Analytics and administration

- Role: Municipal Officer or Administrator.
- Preconditions: Authenticated role with the corresponding permission.
- Action: Open Analytics/Admin Dashboard; review summary, heatmap, departments, users, and audit logs. As Administrator, inspect email logs and role management.
- Expected result: Analytics is restricted to authorized staff; email logs and user-role changes are Administrator-only; audit entries are visible.
- Evidence: `/api/analytics/*`, `/api/admin/*`, and `/api/notifications/emails`.
- Limitation: This is a local seeded dataset; Mongo persistence, backup/restore, accessibility certification, and load behavior are not demonstrated by this script.

## Cleanup

Stop both servers. If the data is disposable JSON data, first copy `backend/data` to an external temporary backup if needed, then remove only the generated JSON files in that disposable workspace and restart the backend to reseed. Never run cleanup against a production directory or a configured MongoDB database.
