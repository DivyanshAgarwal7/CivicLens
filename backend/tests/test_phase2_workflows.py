import hashlib
import os
import sys
from pathlib import Path

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "test-only-secret-value-123456789012345")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi import HTTPException

from models import EngineerResolutionRequest, OfficerAssignRequest, OfficerPriorityReviewRequest, VerificationCreate
from routers import engineer_routes, officer_routes, verification_routes
from services import notification_service


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = [dict(doc) for doc in (docs or [])]
        self.unique_indexes = []

    def create_index(self, keys, unique=False, **kwargs):
        if unique:
            self.unique_indexes.append((keys,) if isinstance(keys, str) else tuple(field for field, _ in keys))

    def _match(self, doc, query):
        for key, value in query.items():
            if key == "$or":
                if not any(self._match(doc, branch) for branch in value):
                    return False
            elif isinstance(value, dict) and "$in" in value:
                if doc.get(key) not in value["$in"]:
                    return False
            elif doc.get(key) != value:
                return False
        return True

    def find_one(self, query):
        return next((doc for doc in self.docs if self._match(doc, query)), None)

    def find(self, query=None, **kwargs):
        return [doc for doc in self.docs if self._match(doc, query or {})]

    def insert_one(self, doc):
        item = dict(doc)
        item.setdefault("_id", f"id-{len(self.docs) + 1}")
        for index in [("_id",), *self.unique_indexes]:
            if any(all(existing.get(key) == item.get(key) for key in index) for existing in self.docs):
                from db import DuplicateKeyError
                raise DuplicateKeyError("duplicate")
        self.docs.append(item)
        return item

    def update_one(self, query, update):
        target = self.find_one(query)
        if not target:
            return False
        target.update(update.get("$set", {}))
        for key, value in update.get("$push", {}).items():
            target.setdefault(key, []).append(value)
        return True

    def delete_one(self, query):
        target = self.find_one(query)
        if target:
            self.docs.remove(target)
            return True
        return False


def test_verification_is_unique_and_score_is_recomputed(monkeypatch):
    issue = {
        "_id": "issue-1", "issue_id": "CL-1", "reporter_id": "reporter",
        "reporter_email": "reporter@example.com", "status": "Reported",
        "credibility_base": 80.0, "credibility_score": 80.0,
        "verification_count": 0, "ai_analysis": {"priority_score": 6.0},
        "status_history": [],
    }
    issues = FakeCollection([issue])
    verifications = FakeCollection()
    verifications.create_index([("issue_id", 1), ("citizen_id", 1)], unique=True)
    monkeypatch.setattr(verification_routes, "get_collection", lambda name: {"issues": issues, "verifications": verifications}[name])
    monkeypatch.setattr(verification_routes, "send_notification", lambda **kwargs: {"created": True})
    monkeypatch.setattr(verification_routes, "log_audit_event", lambda **kwargs: None)

    citizen = {"_id": "citizen-1", "email": "citizen@example.com", "role": "Citizen", "trust_score": 100}
    result = verification_routes.verify_issue("issue-1", VerificationCreate(comment="Seen"), citizen)
    assert result["verification_count"] == 1
    assert result["credibility_score"] == 84.0
    assert issue["ai_analysis"]["priority_score"] == 6.0

    with pytest.raises(HTTPException) as duplicate:
        verification_routes.verify_issue("issue-1", VerificationCreate(), citizen)
    assert duplicate.value.status_code == 409
    assert issues.docs[0]["verification_count"] == 1
    assert len(verifications.docs) == 1


def test_invalid_issue_and_non_citizen_verification_are_rejected(monkeypatch):
    issues = FakeCollection()
    verifications = FakeCollection()
    monkeypatch.setattr(verification_routes, "get_collection", lambda name: {"issues": issues, "verifications": verifications}[name])
    with pytest.raises(HTTPException) as missing:
        verification_routes.verify_issue("missing", VerificationCreate(), {"_id": "u", "role": "Citizen"})
    assert missing.value.status_code == 404

    # The dependency itself is the authorization boundary used by FastAPI.
    from auth import require_roles
    with pytest.raises(HTTPException) as forbidden:
        require_roles(["Citizen"])(user={"role": "Field Engineer"})
    assert forbidden.value.status_code == 403


def test_priority_review_then_assignment_validates_references(monkeypatch):
    issue = {"_id": "issue-1", "issue_id": "CL-1", "status": "Reported", "priority": "High", "status_history": []}
    issues = FakeCollection([issue])
    departments = FakeCollection([{"_id": "dept-1", "name": "Roads & Infrastructure"}])
    engineers = FakeCollection([{"_id": "eng-1", "role": "Field Engineer", "department": "Roads & Infrastructure", "email": "e@example.com", "full_name": "Engineer"}])
    collections = {"issues": issues, "departments": departments, "users": engineers}
    monkeypatch.setattr(officer_routes, "get_collection", lambda name: collections[name])
    monkeypatch.setattr(officer_routes, "send_notification", lambda **kwargs: {"created": True})
    monkeypatch.setattr(officer_routes, "log_audit_event", lambda **kwargs: None)
    officer = {"_id": "officer-1", "email": "o@example.com", "role": "Municipal Officer"}

    with pytest.raises(HTTPException) as before_review:
        officer_routes.assign_issue("issue-1", OfficerAssignRequest(department="Roads & Infrastructure", field_engineer_id="eng-1"), officer)
    assert before_review.value.status_code == 409

    officer_routes.review_issue_priority("issue-1", OfficerPriorityReviewRequest(priority="Urgent"), officer)
    result = officer_routes.assign_issue("issue-1", OfficerAssignRequest(department="Roads & Infrastructure", field_engineer_id="eng-1", priority="Urgent"), officer)
    assert result["success"] is True
    stored_issue = issues.docs[0]
    assert stored_issue["approved_priority"] == "Urgent"
    assert stored_issue["assigned_engineer_id"] == "eng-1"

    with pytest.raises(HTTPException) as cross_department:
        officer_routes.assign_issue("issue-1", OfficerAssignRequest(department="Water Supply & Sewage", field_engineer_id="eng-1", priority="Urgent"), officer)
    assert cross_department.value.status_code in {400, 409}


def test_resolution_requires_owner_and_evidence(monkeypatch):
    issue = {"_id": "issue-1", "issue_id": "CL-1", "status": "Assigned", "assigned_engineer_id": "eng-1", "reporter_id": None, "status_history": []}
    issues = FakeCollection([issue])
    monkeypatch.setattr(engineer_routes, "get_collection", lambda name: issues)
    monkeypatch.setattr(engineer_routes, "send_notification", lambda **kwargs: {"created": True})
    monkeypatch.setattr(engineer_routes, "log_audit_event", lambda **kwargs: None)
    engineer = {"_id": "eng-1", "email": "e@example.com", "role": "Field Engineer", "full_name": "Engineer"}

    engineer_routes.update_task_status("issue-1", EngineerResolutionRequest(status="In Progress", completion_notes="On site"), engineer)
    with pytest.raises(HTTPException) as no_evidence:
        engineer_routes.update_task_status("issue-1", EngineerResolutionRequest(status="Resolved", completion_notes="Done"), engineer)
    assert no_evidence.value.status_code == 422

    with pytest.raises(HTTPException) as wrong_owner:
        engineer_routes.update_task_status("issue-1", EngineerResolutionRequest(status="In Progress", completion_notes="On site"), {"_id": "eng-2", "role": "Field Engineer"})
    assert wrong_owner.value.status_code == 403


def test_notifications_are_idempotent(monkeypatch):
    notifications = FakeCollection()
    monkeypatch.setattr(notification_service, "get_collection", lambda name: notifications)
    email_log = Path(os.environ.get("TEMP", ".")) / "civiclens-phase2-test-emails.json"
    email_log.unlink(missing_ok=True)
    monkeypatch.setattr(notification_service, "EMAIL_LOG_FILE", email_log)

    first = notification_service.send_notification("u-1", "u@example.com", "Assigned", "Assigned", "status_change", "/issues/i-1")
    second = notification_service.send_notification("u-1", "u@example.com", "Assigned", "Assigned", "status_change", "/issues/i-1")
    assert first["created"] is True
    assert second["created"] is False
    assert len(notifications.docs) == 1
    email_log.unlink(missing_ok=True)
