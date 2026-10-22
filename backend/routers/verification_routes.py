import uuid
from pymongo.errors import DuplicateKeyError as MongoDuplicateKeyError
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from auth import get_optional_current_user, require_roles
from db import DuplicateKeyError, get_collection
from models import VerificationCreate
from services.audit_service import log_audit_event
from services.notification_service import send_notification

router = APIRouter(prefix="/api/issues", tags=["Community Verification"])

def _public_verification(entry: dict, viewer: dict | None = None) -> dict:
    """Expose community confirmation content without verifier identity or trust data."""
    return {
        "_id": entry.get("_id"),
        "issue_id": entry.get("issue_id"),
        "citizen_name": entry.get("citizen_name", ""),
        "comment": entry.get("comment"),
        "verified_at": entry.get("verified_at"),
        "verified_by_current_user": bool(viewer and entry.get("citizen_id") == viewer.get("_id")),
    }

@router.post("/{issue_id}/verify")
def verify_issue(issue_id: str, req: VerificationCreate, user: dict = Depends(require_roles(["Citizen"]))):
    issues_col = get_collection("issues")
    verifications_col = get_collection("verifications")

    issue = issues_col.find_one({"$or": [{"_id": issue_id}, {"issue_id": issue_id}]})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    target_id = issue["_id"]

    # Check if this user already verified this issue (SRS FR-016)
    existing = verifications_col.find_one({"issue_id": target_id, "citizen_id": user["_id"]})
    if existing:
        raise HTTPException(status_code=409, detail="You have already verified this civic issue.")

    now_iso = datetime.utcnow().isoformat()
    verification_entry = {
        "_id": str(uuid.uuid4()),
        "issue_id": target_id,
        "citizen_id": user["_id"],
        "citizen_name": "",
        "citizen_trust_score": user.get("trust_score", 100),
        "comment": req.comment or "Community verification confirmed.",
        "verified_at": now_iso
    }
    try:
        verifications_col.insert_one(verification_entry)
    except (MongoDuplicateKeyError, DuplicateKeyError) as error:
        raise HTTPException(status_code=409, detail="You have already verified this civic issue.") from error

    # Calculate updated verification count and credibility score (FR-017, FR-018)
    all_vers = verifications_col.find({"issue_id": target_id})
    v_count = len(all_vers)

    # Configurable assumption: credibility is the reporter's initial trust plus
    # four points per unique verification, capped at 100.
    base_credibility = float(issue.get("credibility_base", issue.get("credibility_score", 80.0)))
    new_credibility = min(100.0, max(0.0, base_credibility + (v_count * 4.0)))

    # Boost AI priority score if verifications exceed thresholds
    ai_analysis = issue.get("ai_analysis", {})
    ai_analysis["verification_count"] = v_count

    updated = issues_col.update_one(
        {"_id": target_id},
        {
            "$set": {
                "verification_count": v_count,
                "credibility_score": round(new_credibility, 1),
                "ai_analysis": ai_analysis
            },
            "$push": {
                "status_history": {
                    "status": issue.get("status"),
                    "updated_by": "Community member",
                    "timestamp": now_iso,
                    "comment": req.comment or "Community citizen confirmed existence of this issue."
                }
            }
        }
    )
    if not updated:
        verifications_col.delete_one({"_id": verification_entry["_id"]})
        raise HTTPException(status_code=409, detail="Verification could not be applied consistently. Please retry.")

    # Notification delivery is nonessential; persistence above remains authoritative.
    if issue.get("reporter_id") != user["_id"]:
        try:
            send_notification(
                recipient_id=issue["reporter_id"],
                recipient_email=issue.get("reporter_email", ""),
                title="Community Verified Your Issue",
                message=f"A community member verified your report {issue.get('issue_id')}.",
                notification_type="verification",
                link=f"/issues/{target_id}"
            )
        except Exception as error:
            print(f"[Notification] Verification notification failed: {type(error).__name__}")

    log_audit_event(
        action="ISSUE_VERIFIED",
        user_id=user["_id"],
        user_email=user["email"],
        user_role=user["role"],
        details={"issue_id": issue.get("issue_id"), "verification_count": v_count}
    )

    return {
        "success": True,
        "verification_count": v_count,
        "credibility_score": round(new_credibility, 1),
        "message": "Thank you! Your verification has been recorded."
    }

@router.get("/{issue_id}/verifications")
def get_issue_verifications(issue_id: str, viewer: dict | None = Depends(get_optional_current_user)):
    issues_col = get_collection("issues")
    verifications_col = get_collection("verifications")

    issue = issues_col.find_one({"$or": [{"_id": issue_id}, {"issue_id": issue_id}]})
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found.")

    entries = verifications_col.find({"issue_id": issue["_id"]}, sort=[("verified_at", -1)])
    return [_public_verification(entry, viewer) for entry in entries]
