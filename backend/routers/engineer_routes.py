from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_roles
from db import get_collection
from models import EngineerResolutionRequest
from services.audit_service import log_audit_event
from services.notification_service import send_notification
from routers.issue_routes import _public_issue

router = APIRouter(prefix="/api/engineer", tags=["Field Engineer"])

@router.get("/tasks")
def get_engineer_tasks(user: dict = Depends(require_roles(["Field Engineer", "Administrator"]))):
    issues_col = get_collection("issues")
    # Show issues assigned directly to this engineer, or open in engineer's department
    filter_doc = {} if user.get("role") == "Administrator" else {"assigned_engineer_id": user["_id"]}
    tasks = issues_col.find(filter_doc, sort=[("updated_at", -1)])
    return [_public_issue(issue) for issue in tasks]

@router.post("/tasks/{issue_id}/status")
def update_task_status(
    issue_id: str,
    req: EngineerResolutionRequest,
    user: dict = Depends(require_roles(["Field Engineer", "Administrator"]))
):
    issues_col = get_collection("issues")
    issue = issues_col.find_one({"$or": [{"_id": issue_id}, {"issue_id": issue_id}]})
    if not issue:
        raise HTTPException(status_code=404, detail="Task not found.")

    if user.get("role") != "Administrator" and issue.get("assigned_engineer_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="This issue is not assigned to you.")

    target_id = issue["_id"]
    now_iso = datetime.utcnow().isoformat()
    new_status = req.status  # "In Progress" or "Resolved"
    allowed_transitions = {
        "Assigned": {"In Progress"},
        "In Progress": {"Resolved"},
    }
    if new_status not in allowed_transitions.get(issue.get("status"), set()):
        raise HTTPException(status_code=409, detail=f"Cannot transition from {issue.get('status')} to {new_status}.")
    if new_status == "Resolved" and not req.evidence_image_url:
        raise HTTPException(status_code=422, detail="Resolution evidence image is required before marking an issue resolved.")

    update_payload = {
        "status": new_status,
        "updated_at": now_iso
    }

    if new_status == "Resolved":
        update_payload["resolution"] = {
            "resolved_at": now_iso,
            "completion_notes": req.completion_notes,
            "evidence_image_url": req.evidence_image_url,
            "resolved_by": user.get("full_name") or user.get("_id")
        }

    issues_col.update_one(
        {"_id": target_id},
        {
            "$set": update_payload,
            "$push": {
                "status_history": {
                    "status": new_status,
                    "updated_by": "Field Operations",
                    "timestamp": now_iso,
                    "comment": req.completion_notes
                }
            }
        }
    )

    # Notify reporting citizen (FR-025, FR-032)
    if issue.get("reporter_id"):
        send_notification(
            recipient_id=issue["reporter_id"],
            recipient_email=issue.get("reporter_email", ""),
            title=f"Civic Issue {new_status}",
            message=f"Update on your complaint {issue.get('issue_id')}: Marked as {new_status}. Engineer Note: {req.completion_notes}",
            notification_type="status_change",
            link=f"/issues/{target_id}"
        )

    log_audit_event(
        action=f"ISSUE_STATUS_CHANGED_{new_status.upper()}",
        user_id=user["_id"],
        user_email=user["email"],
        user_role=user["role"],
        details={"issue_id": issue.get("issue_id"), "status": new_status, "notes": req.completion_notes}
    )

    return {"success": True, "status": new_status, "message": f"Task marked as {new_status}."}
