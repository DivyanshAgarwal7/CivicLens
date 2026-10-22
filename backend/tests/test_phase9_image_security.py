import os
import sys

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "phase9-test-secret-value-123456789012")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from routers.issue_routes import _public_issue, _safe_image_url


def test_image_url_allowlist_accepts_owned_upload_basename_only():
    assert _safe_image_url("/uploads/4e3b7b7b-95c9-412e-91ab-4f2e8d0688c2.png") == "/uploads/4e3b7b7b-95c9-412e-91ab-4f2e8d0688c2.png"
    assert _safe_image_url("/uploads/proof.jpg") == "/uploads/proof.jpg"


def test_image_url_allowlist_rejects_external_and_traversal_sources():
    assert _safe_image_url("https://images.unsplash.com/photo.jpg") is None
    assert _safe_image_url("/uploads/../secrets.txt") is None
    assert _safe_image_url("/uploads/subdir/proof.jpg") is None
    assert _safe_image_url("/uploads/proof.jpg?token=secret") is None


def test_public_issue_removes_bad_images_preserves_valid_association_and_sanitizes_resolution():
    public = _public_issue({
        "_id": "internal-1",
        "issue_id": "CL-9",
        "title": "Pothole",
        "category": "Road Damage",
        "image_urls": ["https://unrelated.example/photo.jpg", "/uploads/issue-9.png"],
        "resolution": {
            "completion_notes": "Filled",
            "resolved_by": "Engineer",
            "evidence_image_url": "https://unrelated.example/after.jpg",
        },
        "reporter_email": "private@example.com",
    })
    assert public["image_urls"] == ["/uploads/issue-9.png"]
    assert public["resolution"]["evidence_image_url"] is None
    assert "reporter_email" not in public


def test_public_issue_with_missing_images_returns_empty_list():
    assert _public_issue({"issue_id": "CL-10", "image_urls": None})["image_urls"] == []
