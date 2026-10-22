import os
import sys
from datetime import timedelta

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "test-only-secret")

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import hashlib
import secrets

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from auth import create_access_token, decode_access_token, hash_password, verify_password
from models import EngineerResolutionRequest, UserLogin, UserRegister
from routers import auth_routes, engineer_routes


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = docs or []
        self.updated = []

    def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items() if k != "$or"):
                return doc
            if "$or" in query and any(all(doc.get(k) == v for k, v in branch.items()) for branch in query["$or"]):
                return doc
        return None

    def insert_one(self, doc):
        doc = dict(doc)
        doc.setdefault("_id", "new-user")
        self.docs.append(doc)
        return doc

    def update_one(self, query, update):
        target = self.find_one(query)
        if target and "$set" in update:
            target.update(update["$set"])
        self.updated.append((query, update))
        return bool(target)

    def find(self, *args, **kwargs):
        return self.docs


def test_public_registration_always_creates_citizen(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_routes, "get_collection", lambda name: users)
    monkeypatch.setattr(auth_routes, "log_audit_event", lambda **kwargs: None)

    request = UserRegister(
        email="new@example.com",
        password="Secure-password1!",
        full_name="New User",
    )
    result = auth_routes.register(request)

    assert result["user"]["role"] == "Citizen"
    assert users.docs[0]["role"] == "Citizen"
    assert users.docs[0]["department"] is None


def test_modern_registration_and_login_contract(monkeypatch):
    users = FakeCollection()
    monkeypatch.setattr(auth_routes, "get_collection", lambda name: users)
    monkeypatch.setattr(auth_routes, "log_audit_event", lambda **kwargs: None)
    request = UserRegister(
        email="aarav.sharma@example.com",
        password="CivicLens-demo1!",
        password_confirmation="CivicLens-demo1!",
        full_name="Aarav Sharma",
        phone="+919823011223",
    )
    registered = auth_routes.register(request)
    logged_in = auth_routes.login(UserLogin(email=request.email, password=request.password))
    assert registered["user"]["email"] == logged_in["user"]["email"] == request.email
    assert registered["user"]["phone"] == "+919823011223"
    assert "password" not in registered["user"]
    assert "password" not in logged_in["user"]


def test_registration_password_policy_and_confirmation():
    valid = UserRegister(
        email="valid@example.com",
        password="Strong-password1!",
        password_confirmation="Strong-password1!",
        full_name="Valid User",
    )
    assert valid.password == "Strong-password1!"

    invalid_values = [
        "Short1!",
        "all-lowercase-password1!",
        "ALL-UPPERCASE-PASSWORD1!",
        "NoDigits-password!",
        "NoSpecialPassword1",
        "            ",
    ]
    for password in invalid_values:
        with pytest.raises(ValidationError):
            UserRegister(email="invalid@example.com", password=password, full_name="Invalid User")

    with pytest.raises(ValidationError):
        UserRegister(
            email="mismatch@example.com",
            password="Strong-password1!",
            password_confirmation="Different-password1!",
            full_name="Mismatch User",
        )


def test_password_hashing_and_legacy_migration(monkeypatch):
    modern = hash_password("secure-password")
    assert modern.startswith("$2")
    assert verify_password("secure-password", modern)
    assert not verify_password("wrong-password", modern)

    salt = secrets.token_hex(16)
    legacy = f"{salt}:{hashlib.sha256((salt + 'legacy-pass').encode()).hexdigest()}"
    users = FakeCollection([{
        "_id": "legacy-user",
        "email": "legacy@example.com",
        "password_hash": legacy,
        "role": "Citizen",
        "full_name": "Legacy User",
    }])
    monkeypatch.setattr(auth_routes, "get_collection", lambda name: users)
    monkeypatch.setattr(auth_routes, "log_audit_event", lambda **kwargs: None)

    result = auth_routes.login(UserLogin(email="legacy@example.com", password="legacy-pass"))
    assert result["user"]["id"] == "legacy-user"
    assert users.docs[0]["password_hash"].startswith("$2")


def test_jwt_requires_valid_claims_and_expiry():
    token = create_access_token({"sub": "user-1"})
    assert decode_access_token(token)["sub"] == "user-1"
    expired = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=-1))
    assert decode_access_token(expired) is None


def test_engineer_cannot_update_unassigned_issue(monkeypatch):
    issues = FakeCollection([{
        "_id": "issue-1",
        "issue_id": "CL-1",
        "status": "Assigned",
        "assigned_engineer_id": "engineer-a",
    }])
    monkeypatch.setattr(engineer_routes, "get_collection", lambda name: issues)

    with pytest.raises(HTTPException) as error:
        engineer_routes.update_task_status(
            "issue-1",
            EngineerResolutionRequest(status="In Progress", completion_notes="On site"),
            {"_id": "engineer-b", "role": "Field Engineer", "email": "b@example.com"},
        )
    assert error.value.status_code == 403


def test_engineer_status_transitions_are_validated(monkeypatch):
    issues = FakeCollection([{
        "_id": "issue-1",
        "issue_id": "CL-1",
        "status": "Assigned",
        "assigned_engineer_id": "engineer-a",
        "reporter_id": None,
    }])
    monkeypatch.setattr(engineer_routes, "get_collection", lambda name: issues)
    monkeypatch.setattr(engineer_routes, "log_audit_event", lambda **kwargs: None)
    monkeypatch.setattr(engineer_routes, "send_notification", lambda **kwargs: None)

    with pytest.raises(HTTPException) as error:
        engineer_routes.update_task_status(
            "issue-1",
            EngineerResolutionRequest(status="Resolved", completion_notes="Skipped inspection"),
            {"_id": "engineer-a", "role": "Field Engineer", "email": "a@example.com"},
        )
    assert error.value.status_code == 409

