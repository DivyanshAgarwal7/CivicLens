from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, require_roles
from db import get_collection
from models import OfficerAssignRequest
from models import OfficerPriorityReviewRequest
from services.audit_service import log_audit_event
from services.notification_service import send_notification
from routers.issue_routes import _public_issue

router = APIRouter(prefix="/api/officer", tags=["Municipal Officer"])

VALID_PRIORITIES = {"Low", "Medium", "High", "Urgent"}

def _find_issue(issues_col, issue_id: str):
    return issues_col.find_one({"$or": [{"_id": issue_id}, {"issue_id": issue_id}]})

def _validate_department_and_engineer(departments_col, users_col, department: str, engineer_id: Optional[str]):
    department_doc = departments_col.find_one({"name": department})
    if not department_doc:
        raise HTTPException(status_code=400, detail="Unknown municipal department.")
    if engineer_id:
        engineer = users_col.find_one({"_id": engineer_id})
        if not engineer or engineer.get("role") != "Field Engineer":
            raise HTTPException(status_code=400, detail="Selected user is not a valid field engineer.")
        if engineer.get("department") != department:
            raise HTTPException(status_code=400, detail="Field engineer is not assigned to this department.")
        return engineer
    return None

@router.get("/issues")
def get_officer_issues(
    status: Optional[str] = None,
    department: Optional[str] = None,
    priority: Optional[str] = None,
    user: dict = Depends(require_roles(["Municipal Officer", "Administrator"]))
):
    issues_col = get_collection("issues")
    filter_doc = {}
    if status and status != "All":
        filter_doc["status"] = status
    if department and department != "All":
        filter_doc["assigned_department"] = department
    if priority and priority != "All":
        filter_doc["priority"] = priority

    issues = issues_col.find(filter_doc, sort=[("created_at", -1)])
    return [_public_issue(issue) for issue in issues]

@router.get("/engineers")
def get_engineers(user: dict = Depends(require_roles(["Municipal Officer", "Administrator"]))):
    users_col = get_collection("users")
    engineers = users_col.find({"role": "Field Engineer"})
    return [
        {
            "id": e["_id"],
            "full_name": e["full_name"],
            "email": e["email"],
            "phone": e.get("phone", ""),
            "department": e.get("department")
        }
        for e in engineers
    ]

@router.post("/issues/{issue_id}/assign")
def assign_issue(
    issue_id: str,
    req: OfficerAssignRequest,
    user: dict = Depends(require_roles(["Municipal Officer", "Administrator"]))
):
    issues_col = get_collection("issues")
    users_col = get_collection("users")
    departments_col = get_collection("departments")

    issue = _find_issue(issues_col, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    if issue.get("status") not in {"Reported", "Assigned"}:
        raise HTTPException(status_code=409, detail="Only reported or already assigned issues can be assigned.")
    if not issue.get("priority_reviewed") or not issue.get("approved_priority"):
        raise HTTPException(status_code=409, detail="Officer priority review is required before assignment.")

    target_id = issue["_id"]
    eng = _validate_department_and_engineer(departments_col, users_col, req.department, req.field_engineer_id)
    engineer_name = eng.get("full_name") if eng else None
    engineer_email = eng.get("email") if eng else None

    now_iso = datetime.utcnow().isoformat()
    if req.priority and req.priority != issue.get("approved_priority"):
        raise HTTPException(status_code=409, detail="Assignment priority must match the officer-approved priority.")
    new_priority = issue["approved_priority"]

    update_payload = {
        "status": "Assigned",
        "assigned_department": req.department,
        "assigned_engineer_id": req.field_engineer_id,
        "assigned_engineer_name": engineer_name,
            "priority": new_priority,
        "updated_at": now_iso
    }

    status_comment = f"Assigned to {req.department}"
    if req.field_engineer_id:
        status_comment += " (Field Engineer assigned)"
    if req.officer_notes:
        status_comment += f". Notes: {req.officer_notes}"
    if req.priority and req.priority != issue.get("priority"):
        status_comment += f" [Priority updated from {issue.get('priority')} to {new_priority}]"

    issues_col.update_one(
        {"_id": target_id},
        {
            "$set": update_payload,
            "$push": {
                "status_history": {
                    "status": "Assigned",
                    "updated_by": "Municipal Officer",
                    "timestamp": now_iso,
                    "comment": status_comment
                }
            }
        }
    )

    # 1. Notify reporting citizen (FR-025, FR-032)
    if issue.get("reporter_id"):
        send_notification(
            recipient_id=issue["reporter_id"],
            recipient_email=issue.get("reporter_email", ""),
            title="Issue Status Updated: Assigned",
            message=f"Your complaint {issue.get('issue_id')} has been assigned to {req.department}. A field engineer will handle the work.",
            notification_type="status_change",
            link=f"/issues/{target_id}"
        )

    # 2. Notify assigned engineer if selected
    if req.field_engineer_id and engineer_email:
        send_notification(
            recipient_id=req.field_engineer_id,
            recipient_email=engineer_email,
            title="New Field Task Assigned",
            message=f"You have been assigned issue {issue.get('issue_id')} ({issue.get('category')}) at {issue.get('location', {}).get('address')}.",
            notification_type="task_assignment",
            link=f"/issues/{target_id}"
        )

    log_audit_event(
        action="ISSUE_ASSIGNED",
        user_id=user["_id"],
        user_email=user["email"],
        user_role=user["role"],
        details={
            "issue_id": issue.get("issue_id"),
            "department": req.department,
            "engineer": engineer_name,
            "priority": new_priority
        }
    )

    return {"success": True, "message": "Issue assigned successfully."}

@router.post("/issues/{issue_id}/priority-review")
def review_issue_priority(
    issue_id: str,
    req: OfficerPriorityReviewRequest,
    user: dict = Depends(require_roles(["Municipal Officer", "Administrator"])),
):
    issues_col = get_collection("issues")
    issue = _find_issue(issues_col, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")
    if issue.get("status") not in {"Reported", "Assigned"}:
        raise HTTPException(status_code=409, detail="Priority can only be reviewed before resolution.")

    now_iso = datetime.utcnow().isoformat()
    updated = issues_col.update_one(
        {"_id": issue["_id"], "status": issue.get("status")},
        {"$set": {
            "priority": req.priority,
            "approved_priority": req.priority,
            "priority_reviewed": True,
            "priority_approved_by": user["_id"],
            "priority_reviewed_at": now_iso,
            "priority_review_notes": req.review_notes,
        }, "$push": {
            "status_history": {
                "status": issue.get("status"),
                "updated_by": user.get("role", "Municipal Officer"),
                "timestamp": now_iso,
                "comment": f"Priority reviewed and approved as {req.priority}. {req.review_notes}".strip(),
            }
        }}
    )
    if not updated:
        raise HTTPException(status_code=409, detail="Issue changed before priority review could be applied.")
    log_audit_event(
        action="ISSUE_PRIORITY_REVIEWED",
        user_id=user["_id"], user_email=user["email"], user_role=user["role"],
        details={"issue_id": issue.get("issue_id"), "approved_priority": req.priority},
    )
    return {"success": True, "approved_priority": req.priority}
