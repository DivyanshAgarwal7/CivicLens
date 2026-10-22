import os
import sys

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("ALLOW_JSON_DB", "true")
os.environ.setdefault("JWT_SECRET", "test-only-secret-value-123456789012345")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import ai_service


class FakeEmbeddingModel:
    def encode(self, texts, **kwargs):
        vectors = []
        for text in texts:
            text = text.lower()
            if "lamp" in text or "illumination" in text or "light" in text:
                vectors.append([1.0, 0.0])
            elif "pothole" in text or "road hole" in text:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([0.0, 0.0])
        return vectors


def test_semantic_candidate_supports_different_wording(monkeypatch):
    monkeypatch.setattr(ai_service, "_get_embedding_model", lambda: FakeEmbeddingModel())
    result = ai_service.check_duplicate_issues(
        "Street lamp not working", "The road is dark", "Damaged Streetlight", 18.5, 73.8,
        [{"issue_id": "I-1", "title": "Broken illumination", "description": "The clinic light is off", "category": "Damaged Streetlight", "location": {"latitude": 18.5001, "longitude": 73.8001}, "status": "Reported"}],
    )
    assert result["is_duplicate"] is True
    assert result["semantic_model_available"] is True
    assert result["matched_issue"]["issue_id"] == "I-1"
    assert "description" not in result["matched_issue"]


def test_distance_filter_and_current_issue_exclusion(monkeypatch):
    monkeypatch.setattr(ai_service, "_get_embedding_model", lambda: FakeEmbeddingModel())
    issue = {"issue_id": "I-1", "title": "Street lamp", "description": "Light is off", "category": "Damaged Streetlight", "location": {"latitude": 19.5, "longitude": 74.8}, "status": "Reported"}
    result = ai_service.check_duplicate_issues("Street lamp", "Light is off", "Damaged Streetlight", 18.5, 73.8, [issue])
    assert result["is_duplicate"] is False
    result = ai_service.check_duplicate_issues("Street lamp", "Light is off", "Damaged Streetlight", 18.5, 73.8, [issue], current_issue_id="I-1")
    assert result["reason"] == "no-candidates"


def test_unavailable_model_uses_labeled_fallback(monkeypatch):
    monkeypatch.setattr(ai_service, "_get_embedding_model", lambda: None)
    result = ai_service.check_duplicate_issues("Pothole", "Deep pothole near road", "Pothole", None, None, [])
    assert result["method"] == "unavailable"
    result = ai_service.check_duplicate_issues("Pothole", "Deep pothole near road", "Pothole", None, None, [{"issue_id": "I-2", "title": "Road hole", "description": "Deep pothole", "category": "Pothole", "status": "Reported"}])
    assert result["semantic_model_available"] is False
    assert result["method"] == "tfidf-lexical-baseline"


def test_lexical_fallback_uses_its_own_calibrated_threshold(monkeypatch):
    monkeypatch.setattr(ai_service, "_get_embedding_model", lambda: None)
    result = ai_service.check_duplicate_issues(
        "Deep pothole near the bus stop", "Road damage at the bus stop", "Pothole", 18.5175, 73.8152,
        [{"issue_id": "I-3", "title": "Large pothole by Kothrud bus stop", "description": "Road damage near the bus stop", "category": "Pothole", "location": {"latitude": 18.5176, "longitude": 73.8153}, "status": "Reported"}],
    )
    assert result["method"] == "tfidf-lexical-baseline"
    assert result["threshold"] == 0.38
    assert result["is_duplicate"] is True


def test_priority_baseline_is_deterministic_and_explainable():
    first = ai_service.predict_issue_priority("Broken signal", "Danger at school crossing", "Traffic Signal Failure", 2, 1)
    second = ai_service.predict_issue_priority("Broken signal", "Danger at school crossing", "Traffic Signal Failure", 2, 1)
    assert first == second
    assert first["method"] == "deterministic-baseline"
    assert first["model_version"] == "priority-baseline-v1"
    assert "hazard indicators" in first["ai_rationale"]
    assert ai_service.predict_issue_priority("", "", "Unsupported") ["priority"] in {"Low", "Medium", "High", "Urgent"}
