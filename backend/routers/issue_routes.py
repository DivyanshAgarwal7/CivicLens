import os
import uuid
import logging
import re
from time import perf_counter
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from PIL import Image, UnidentifiedImageError
from auth import get_current_user
from config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from db import get_collection
from models import DuplicateCheckRequest, IssueCreate
from services.ai_service import CATEGORIES, analyze_issue_image, check_duplicate_issues, predict_issue_priority
from services.audit_service import log_audit_event
from services.notification_service import send_notification

router = APIRouter(prefix="/api/issues", tags=["Issues"])
logger = logging.getLogger(__name__)

_PUBLIC_ISSUE_FIELDS = {
    "_id", "issue_id", "title", "description", "category", "location", "image_urls",
    "status", "priority", "approved_priority", "priority_reviewed", "assigned_department",
    "assigned_engineer_id", "assigned_engineer_name", "verification_count",
    "credibility_score", "ai_analysis", "status_history", "created_at", "updated_at",
    "resolution",
}

_SAFE_UPLOAD_URL = re.compile(r"^/uploads/[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

def _safe_image_url(value: object) -> Optional[str]:
    """Only expose local, basename-only uploads that the app owns."""
    if not isinstance(value, str) or not _SAFE_UPLOAD_URL.fullmatch(value):
        return None
    return value

def _public_image_urls(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [safe for item in value if (safe := _safe_image_url(item))]

def _public_issue(issue: dict) -> dict:
    """Remove reporter identity and other internal fields from public issue responses."""
    public = {key: value for key, value in issue.items() if key in _PUBLIC_ISSUE_FIELDS}
    public["image_urls"] = _public_image_urls(issue.get("image_urls"))
    if isinstance(issue.get("resolution"), dict):
        resolution = dict(issue["resolution"])
        resolution["evidence_image_url"] = _safe_image_url(resolution.get("evidence_image_url"))
        public["resolution"] = resolution
    return public

def _fallback_duplicate(reason: str) -> dict:
    return {
        "is_duplicate": False,
        "confidence": 0.0,
        "matched_issue": None,
        "potential_matches": [],
        "rationale": "Duplicate analysis was unavailable; officer review remains authoritative.",
        "method": "unavailable",
        "semantic_model_available": False,
        "reason": reason,
        "threshold": None,
        "model_version": "duplicate-detector-v1",
    }

def _fallback_priority(category: str) -> dict:
    return {
        "priority": "Medium",
        "priority_score": 5.0,
        "recommended_department": CATEGORIES.get(category, CATEGORIES["Other"]),
        "ai_rationale": "Priority analysis was unavailable; municipal review is required.",
        "method": "unavailable",
        "model_version": "priority-baseline-v1",
    }

def _send_issue_notifications(issue: dict, req: IssueCreate, user: dict, priority: str) -> None:
    """Deliver optional notifications after the issue has been persisted and returned."""
    issue_number = issue["issue_id"]
    send_notification(
        recipient_id=user["_id"],
        recipient_email=user["email"],
        title="Civic Issue Submitted",
        message=f"Your report '{req.title}' has been registered as {issue_number}. AI assigned priority: {priority}.",
        notification_type="submission_confirmation",
        link=f"/issues/{issue['_id']}"
    )

    users_col = get_collection("users")
    officers = users_col.find({"role": "Municipal Officer"})
    for officer in officers:
        send_notification(
            recipient_id=officer["_id"],
            recipient_email=officer["email"],
            title="New Civic Issue Requiring Review",
            message=f"New report {issue_number} ({req.category}) in {req.location.ward}. AI Priority: {priority}.",
            notification_type="officer_alert",
            link=f"/issues/{issue['_id']}"
        )

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail="Invalid image format. Supported formats: JPEG, PNG, WebP.")

    suffix_by_type = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    filename = f"{uuid.uuid4()}{suffix_by_type[file.content_type]}"
    dest_path = UPLOAD_DIR / filename
    total = 0
    try:
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Image exceeds the configured size limit.")
                buffer.write(chunk)
        with Image.open(dest_path) as image:
            image.verify()
    except HTTPException:
        dest_path.unlink(missing_ok=True)
        raise
    except (UnidentifiedImageError, OSError):
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid supported image.")
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Image upload could not be completed.")

    image_url = f"/uploads/{filename}"

    # Optional vision analysis is enabled only when AI_USE_GEMINI=true.
    vision_assessment = analyze_issue_image(str(dest_path))

    return {
        "image_url": image_url,
        "filename": filename,
        "vision_assessment": vision_assessment
    }

@router.post("/check-duplicate")
def check_duplicate(req: DuplicateCheckRequest, user: dict = Depends(get_current_user)):
    issues_col = get_collection("issues")
    all_issues = issues_col.find()
    result = check_duplicate_issues(
        title=req.title,
        description=req.description,
        category=req.category,
        lat=req.latitude,
        lon=req.longitude,
        existing_issues=all_issues
    )
    return result

@router.get("")
def list_issues(
    category: Optional[str] = None,
    status: Optional[str] = None,
    ward: Optional[str] = None,
    search: Optional[str] = None,
    reporter_id: Optional[str] = None
):
    issues_col = get_collection("issues")
    filter_doc = {}
    if category and category != "All":
        filter_doc["category"] = category
    if status and status != "All":
        filter_doc["status"] = status
    if ward and ward != "All":
        filter_doc["location.ward"] = ward
    if reporter_id:
        filter_doc["reporter_id"] = reporter_id

    issues = issues_col.find(filter_doc, sort=[("created_at", -1)])

    if search:
        search_lower = search.lower()
        issues = [
            i for i in issues
            if search_lower in i.get("title", "").lower() 
            or search_lower in i.get("description", "").lower()
            or search_lower in i.get("issue_id", "").lower()
            or search_lower in i.get("location", {}).get("address", "").lower()
        ]

    return [_public_issue(issue) for issue in issues]

@router.get("/{issue_id}")
def get_issue(issue_id: str):
    issues_col = get_collection("issues")
    issue = issues_col.find_one({"$or": [{"_id": issue_id}, {"issue_id": issue_id}]})
    if not issue:
        raise HTTPException(status_code=404, detail="Civic issue report not found.")
    return _public_issue(issue)

@router.post("")
def create_issue(req: IssueCreate, user: dict = Depends(get_current_user), background_tasks: BackgroundTasks = None):
    issues_col = get_collection("issues")
    started_at = perf_counter()
    issue_number = f"CL-{datetime.utcnow().year}-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.utcnow().isoformat()

    # 1. AI Duplicate Check
    duplicate_started_at = perf_counter()
    if req.duplicate_analysis and isinstance(req.duplicate_analysis, dict):
        dup_check = req.duplicate_analysis
    else:
        all_issues = issues_col.find()
        try:
            dup_check = check_duplicate_issues(
                title=req.title,
                description=req.description,
                category=req.category,
                lat=req.location.latitude,
                lon=req.location.longitude,
                existing_issues=all_issues
            )
        except Exception as error:
            logger.warning("Duplicate analysis unavailable during issue creation: %s", type(error).__name__)
            dup_check = _fallback_duplicate(type(error).__name__)
    duplicate_ms = (perf_counter() - duplicate_started_at) * 1000

    # 2. AI Priority and Routing Prediction
    priority_started_at = perf_counter()
    try:
        ai_prediction = predict_issue_priority(
            title=req.title,
            description=req.description,
            category=req.category,
            verification_count=0,
            duplicate_count=1 if dup_check["is_duplicate"] else 0
        )
    except Exception as error:
        logger.warning("Priority analysis unavailable during issue creation: %s", type(error).__name__)
        ai_prediction = _fallback_priority(req.category)
    priority_ms = (perf_counter() - priority_started_at) * 1000

    new_issue = {
        "issue_id": issue_number,
        "title": req.title,
        "description": req.description,
        "category": req.category,
        "location": req.location.dict(),
        "image_urls": req.image_urls,
        "reporter_id": user["_id"],
        "reporter_name": "",
        "reporter_email": user.get("email", ""),
        "status": "Reported",
        "priority": ai_prediction["priority"],
        "approved_priority": None,
        "priority_reviewed": False,
        "priority_approved_by": None,
        "assigned_department": ai_prediction.get("recommended_department"),
        "assigned_engineer_id": None,
        "assigned_engineer_name": None,
        "verification_count": 0,
        "credibility_base": float(user.get("trust_score", 100)),
        "credibility_score": float(user.get("trust_score", 100)),
        "ai_analysis": {
            "duplicate_checked": True,
            "suspected_duplicate": dup_check["is_duplicate"],
            "suspected_duplicate_of": dup_check.get("matched_issue", {}).get("issue_id") if dup_check.get("matched_issue") else None,
            "duplicate_confidence": dup_check["confidence"],
            "duplicate_method": dup_check.get("method"),
            "duplicate_model_version": dup_check.get("model_version"),
            "duplicate_semantic_model_available": dup_check.get("semantic_model_available", False),
            "predicted_priority": ai_prediction["priority"],
            "priority_recommendation": ai_prediction["priority"],
            "priority_score": ai_prediction["priority_score"],
            "recommended_department": ai_prediction["recommended_department"],
            "ai_rationale": ai_prediction["ai_rationale"],
            "priority_method": ai_prediction.get("method"),
            "priority_model_version": ai_prediction.get("model_version"),
        },
        "status_history": [
            {
                "status": "Reported",
                "updated_by": "Citizen",
                "timestamp": now_iso,
                "comment": "Issue submitted via CivicLens Citizen Portal."
            }
        ],
        "created_at": now_iso,
        "updated_at": now_iso
    }

    persistence_started_at = perf_counter()
    insert_result = issues_col.insert_one(new_issue)
    inserted = insert_result if isinstance(insert_result, dict) else {**new_issue, "_id": str(insert_result.inserted_id)}
    persistence_ms = (perf_counter() - persistence_started_at) * 1000

    if background_tasks is not None:
        background_tasks.add_task(_send_issue_notifications, inserted, req, user, ai_prediction["priority"])
    else:
        # Direct service-level calls and existing tests do not have FastAPI's task queue.
        _send_issue_notifications(inserted, req, user, ai_prediction["priority"])

    # Audit Log (OR-005)
    log_audit_event(
        action="ISSUE_CREATED",
        user_id=user["_id"],
        user_email=user["email"],
        user_role=user["role"],
        details={"issue_id": issue_number, "category": req.category, "priority": ai_prediction["priority"]}
    )

    logger.info(
        "Issue creation timings: duplicate_ms=%.1f priority_ms=%.1f persistence_ms=%.1f total_ms=%.1f notifications=deferred",
        duplicate_ms, priority_ms, persistence_ms, (perf_counter() - started_at) * 1000,
    )

    return inserted
