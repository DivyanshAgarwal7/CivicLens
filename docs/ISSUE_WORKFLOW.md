# CivicLens Issue Workflow

This specification documents the Phase 2 workflow using the statuses already present in the repository. No new persisted status was introduced.

## Status transitions

| Current status | Next status | Authorized actor | Conditions |
| --- | --- | --- | --- |
| Reported | Assigned | Municipal Officer / Administrator | Priority review has set `approved_priority`; department exists; optional engineer exists and belongs to that department. |
| Assigned | Assigned | Municipal Officer / Administrator | Reassignment passes the same department, engineer, and approved-priority checks. |
| Assigned | In Progress | Assigned Field Engineer / Administrator | Engineer owns the assignment. |
| In Progress | Resolved | Assigned Field Engineer / Administrator | Engineer owns the assignment; non-empty completion notes and evidence image URL are required. |

No direct `Reported -> In Progress`, `Reported -> Resolved`, or `Resolved -> *` transition is allowed. Reopening is not supported in this cycle and requires a future documented workflow change.

## Priority review

AI produces `ai_analysis.priority_recommendation` and a rationale. This is decision support only. A Municipal Officer or Administrator must explicitly write `approved_priority`, actor, timestamp, and optional notes through the priority-review endpoint before assignment.

The legacy `priority` field is retained for frontend compatibility and is updated to the approved value only after review. New issues initially contain the AI recommendation in `priority` for display, but `priority_reviewed=false` prevents assignment until review.

## Community verification

The approved repository rule is one verification per Citizen per issue. MongoDB enforces this with a unique compound index on `(issue_id, citizen_id)`; the JSON test/development adapter enforces the same constraint under a process lock.

Credibility uses this documented configurable assumption because the available repository SRS does not specify a formula: `min(100, credibility_base + 4 * unique_verification_count)`. `credibility_base` is captured from the reporter trust score when the issue is created. Verification recalculates from authoritative verification records and never adds repeatedly to the previous score.

## Failure behavior

- Invalid issue, department, engineer, or transition returns a 4xx response with a meaningful detail message.
- Duplicate verification returns `409 Conflict`.
- Notification/email delivery is nonessential. The issue, verification, assignment, or resolution is persisted first; notification failures are logged without rolling back the core business transaction.
- Audit entries contain actor, action, target identifiers, timestamp, and non-sensitive metadata. Passwords, tokens, and secrets are excluded.
