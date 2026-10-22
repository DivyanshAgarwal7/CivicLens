import os
import sys

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "phase4-test-secret-value-123456789012")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluation.evaluate_ai import compute_binary_metrics
from models import EngineerResolutionRequest, IssueCreate, LocationInput, OfficerAssignRequest, OfficerPriorityReviewRequest
from routers import engineer_routes, issue_routes, officer_routes
from routers.issue_routes import _public_issue
from routers.verification_routes import _public_verification

from test_phase2_workflows import FakeCollection

class FakeBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, function, *args, **kwargs):
        self.tasks.append((function, args, kwargs))


def test_evaluation_metrics_cover_confusion_matrix_and_zero_denominators():
    result = compute_binary_metrics([True, False, True, False], [True, True, False, False])
    assert result == {
        "tp": 1, "fp": 1, "fn": 1, "tn": 1,
        "precision": 0.5, "recall": 0.5, "f1": 0.5,
        "false_positive_rate": 0.5,
    }
    assert compute_binary_metrics([False], [True])["precision"] == 0.0


def test_public_issue_serializer_removes_reporter_identity():
    public = _public_issue({
        "_id": "internal-id", "issue_id": "CL-1", "title": "Pothole",
        "reporter_id": "citizen-1", "reporter_email": "citizen@example.com",
        "password_hash": "must-never-appear", "status": "Reported",
    })
    assert public["issue_id"] == "CL-1"
    assert "reporter_id" not in public
    assert "reporter_email" not in public
    assert "password_hash" not in public


def test_public_verification_serializer_removes_verifier_identity_and_trust_score():
    public = _public_verification({
        "_id": "verification-1", "issue_id": "issue-1", "citizen_id": "citizen-1",
        "citizen_name": "", "citizen_trust_score": 100, "comment": "Seen", "verified_at": "now",
    }, {"_id": "citizen-1"})
    assert public["verified_by_current_user"] is True
    assert public["comment"] == "Seen"
    assert "citizen_id" not in public
    assert "citizen_trust_score" not in public


def test_issue_creation_reuses_duplicate_precheck_and_defers_notifications(monkeypatch):
    issues = FakeCollection()
    users = FakeCollection()
    monkeypatch.setattr(issue_routes, "get_collection", lambda name: {"issues": issues, "users": users}[name])
    monkeypatch.setattr(issue_routes, "log_audit_event", lambda **kwargs: None)
    monkeypatch.setattr(issue_routes, "predict_issue_priority", lambda **kwargs: {
        "priority": "Medium", "priority_score": 5.0,
        "recommended_department": "Roads & Infrastructure",
        "ai_rationale": "test", "method": "test", "model_version": "test",
    })
    monkeypatch.setattr(issue_routes, "check_duplicate_issues", lambda **kwargs: (_ for _ in ()).throw(AssertionError("duplicate check repeated")))

    tasks = FakeBackgroundTasks()
    created = issue_routes.create_issue(
        IssueCreate(
            title="Broken curb near school", description="A damaged curb is blocking the footpath near school gate",
            category="Pothole", location=LocationInput(latitude=18.6, longitude=73.8, address="School Road"),
            duplicate_analysis={"is_duplicate": False, "confidence": 0.0, "method": "tfidf-lexical-baseline"},
        ),
        {"_id": "citizen-1", "email": "citizen@example.test", "role": "Citizen", "trust_score": 100},
        tasks,
    )
    assert created["status"] == "Reported"
    assert len(tasks.tasks) == 1


def test_connected_issue_journey_submission_review_assignment_resolution(monkeypatch):
    issues = FakeCollection()
    users = FakeCollection([
        {"_id": "engineer-1", "role": "Field Engineer", "department": "Roads & Infrastructure", "email": "engineer@example.com", "full_name": "Engineer"},
        {"_id": "officer-1", "role": "Municipal Officer", "email": "officer@example.com"},
    ])
    departments = FakeCollection([{ "_id": "dept-1", "name": "Roads & Infrastructure" }])
    collections = {"issues": issues, "users": users, "departments": departments}
    for module in (issue_routes, officer_routes, engineer_routes):
        monkeypatch.setattr(module, "get_collection", lambda name, values=collections: values[name])
        monkeypatch.setattr(module, "send_notification", lambda **kwargs: {"created": True})
        monkeypatch.setattr(module, "log_audit_event", lambda **kwargs: None)
    monkeypatch.setattr(issue_routes, "check_duplicate_issues", lambda **kwargs: {"is_duplicate": False, "confidence": 0.0, "method": "test"})
    monkeypatch.setattr(issue_routes, "predict_issue_priority", lambda **kwargs: {
        "priority": "High", "priority_score": 7.0, "recommended_department": "Roads & Infrastructure",
        "ai_rationale": "test", "method": "test", "model_version": "test",
    })

    citizen = {"_id": "citizen-1", "email": "citizen@example.com", "role": "Citizen", "trust_score": 100}
    created = issue_routes.create_issue(IssueCreate(
        title="Large pothole on Main Road", description="Deep road damage near the bus stop",
        category="Roads & Infrastructure", location=LocationInput(latitude=28.6, longitude=77.2, address="Main Road"),
    ), citizen)
    assert created["status"] == "Reported"
    issue_id = created["_id"]

    officer = users.find_one({"_id": "officer-1"})
    officer_routes.review_issue_priority(issue_id, OfficerPriorityReviewRequest(priority="Urgent"), officer)
    officer_routes.assign_issue(issue_id, OfficerAssignRequest(department="Roads & Infrastructure", field_engineer_id="engineer-1", priority="Urgent"), officer)
    engineer = users.find_one({"_id": "engineer-1"})
    engineer_routes.update_task_status(issue_id, EngineerResolutionRequest(status="In Progress", completion_notes="Inspection started"), engineer)
    engineer_routes.update_task_status(issue_id, EngineerResolutionRequest(status="Resolved", completion_notes="Repaired and verified", evidence_image_url="/uploads/proof.jpg"), engineer)

    final_issue = issues.find_one({"_id": issue_id})
    assert final_issue["status"] == "Resolved"
    assert final_issue["approved_priority"] == "Urgent"
    assert final_issue["assigned_engineer_id"] == "engineer-1"
    assert final_issue["resolution"]["evidence_image_url"] == "/uploads/proof.jpg"
