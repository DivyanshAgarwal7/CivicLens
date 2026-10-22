"""CivicLens AI decision-support services.

Duplicate detection prefers sentence-transformers when the configured model is
available locally. It never downloads a model during application startup. The
fallback is deterministic TF-IDF cosine similarity (or token Jaccard if
scikit-learn is unavailable), and is explicitly labeled as a lexical baseline.
Priority recommendations are a deterministic, configurable engineering
baseline, not a trained model.
"""

import json
import logging
import math
import os
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from config import (
    AI_DUPLICATE_MAX_CANDIDATES,
    AI_DUPLICATE_MAX_DISTANCE_METERS,
    AI_DUPLICATE_THRESHOLD,
    AI_LEXICAL_DUPLICATE_THRESHOLD,
    AI_EMBEDDING_MODEL,
    AI_USE_GEMINI,
    GEMINI_API_KEY,
)

logger = logging.getLogger(__name__)
_MODEL_LOCK = threading.Lock()
_EMBEDDING_MODEL = None
_MODEL_LOAD_ATTEMPTED = False

PRIORITY_BASELINE_VERSION = "priority-baseline-v1"
DUPLICATE_DETECTOR_VERSION = "duplicate-detector-v1"
CATEGORIES = {
    "Pothole": "Roads & Infrastructure",
    "Damaged Streetlight": "Electrical & Lighting",
    "Garbage Accumulation": "Solid Waste & Sanitation",
    "Water Leakage": "Water Supply & Sewage",
    "Drainage Problem": "Storm Water & Drainage",
    "Traffic Signal Failure": "Traffic & Transportation",
    "Other": "General Administration",
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _issue_text(title: Any, description: Any) -> str:
    return _clean_text(f"{_clean_text(title)} {_clean_text(description)}")


def _get_embedding_model():
    """Load sentence-transformers once, lazily, without network-dependent startup."""
    global _EMBEDDING_MODEL, _MODEL_LOAD_ATTEMPTED
    if _MODEL_LOAD_ATTEMPTED:
        return _EMBEDDING_MODEL
    with _MODEL_LOCK:
        if _MODEL_LOAD_ATTEMPTED:
            return _EMBEDDING_MODEL
        _MODEL_LOAD_ATTEMPTED = True
        configured_path = Path(AI_EMBEDDING_MODEL)
        cache_root = Path(os.getenv("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
        model_cache = cache_root / f"models--{AI_EMBEDDING_MODEL.replace('/', '--')}"
        if not configured_path.exists() and not model_cache.exists():
            logger.info("Semantic embedding model is not locally cached; using lexical fallback.")
            return None
        try:
            from sentence_transformers import SentenceTransformer
            _EMBEDDING_MODEL = SentenceTransformer(AI_EMBEDDING_MODEL, local_files_only=True)
        except Exception as error:
            logger.info("Semantic embedding model unavailable: %s", type(error).__name__)
            _EMBEDDING_MODEL = None
    return _EMBEDDING_MODEL


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, min(1.0, numerator / (left_norm * right_norm)))


def _lexical_similarities(query: str, candidates: List[str]) -> List[float]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        matrix = TfidfVectorizer(lowercase=True, ngram_range=(1, 2)).fit_transform([query, *candidates])
        return [float(max(0.0, min(1.0, value))) for value in cosine_similarity(matrix[0:1], matrix[1:]).ravel()]
    except Exception as error:
        logger.info("TF-IDF fallback unavailable: %s", type(error).__name__)
        query_words = set(re.findall(r"\w+", query.lower()))
        scores = []
        for candidate in candidates:
            words = set(re.findall(r"\w+", candidate.lower()))
            union = query_words | words
            scores.append(len(query_words & words) / len(union) if union else 0.0)
        return scores


def _semantic_or_lexical_scores(query: str, candidates: List[str]) -> tuple[List[float], str, bool]:
    model = _get_embedding_model()
    if model is not None:
        try:
            embeddings = model.encode([query, *candidates], normalize_embeddings=True, show_progress_bar=False)
            return [round(_cosine_similarity(embeddings[0], vector), 4) for vector in embeddings[1:]], "sentence-transformers", True
        except Exception as error:
            logger.warning("Embedding inference failed; using lexical fallback: %s", type(error).__name__)
    return [round(score, 4) for score in _lexical_similarities(query, candidates)], "tfidf-lexical-baseline", False


def _safe_match(issue: Dict[str, Any], distance: Optional[float], similarity: float, category_match: bool) -> Dict[str, Any]:
    location = issue.get("location") if isinstance(issue.get("location"), dict) else {}
    return {
        "_id": issue.get("_id"),
        "issue_id": issue.get("issue_id") or issue.get("_id"),
        "title": _clean_text(issue.get("title"))[:160],
        "category": _clean_text(issue.get("category"))[:80],
        "status": _clean_text(issue.get("status"))[:40],
        "distance_meters": round(distance, 1) if distance is not None else None,
        "semantic_similarity": round(similarity, 4),
        "category_match": category_match,
        "location": {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "ward": _clean_text(location.get("ward"))[:100],
        },
    }


def check_duplicate_issues(
    title: str,
    description: str,
    category: str,
    lat: Optional[float],
    lon: Optional[float],
    existing_issues: List[Dict[str, Any]],
    max_distance_meters: float = AI_DUPLICATE_MAX_DISTANCE_METERS,
    similarity_threshold: Optional[float] = None,
    current_issue_id: Optional[str] = None,
) -> Dict[str, Any]:
    max_distance_meters = max(1.0, float(max_distance_meters or AI_DUPLICATE_MAX_DISTANCE_METERS))
    requested_threshold = similarity_threshold
    query_text = _issue_text(title, description)
    if len(query_text) < 5:
        return _empty_duplicate_result("A meaningful title or description is required for duplicate analysis.", "insufficient-input")

    candidates = []
    for issue in existing_issues or []:
        if not isinstance(issue, dict):
            continue
        issue_identifier = issue.get("issue_id") or issue.get("_id")
        if current_issue_id and current_issue_id in {issue_identifier, issue.get("_id")}:
            continue
        if issue.get("status") in {"Resolved", "Closed"}:
            continue
        issue_text = _issue_text(issue.get("title"), issue.get("description"))
        if len(issue_text) < 5:
            continue
        location = issue.get("location") if isinstance(issue.get("location"), dict) else {}
        issue_lat, issue_lon = location.get("latitude"), location.get("longitude")
        distance = None
        if lat is not None and lon is not None and isinstance(issue_lat, (int, float)) and isinstance(issue_lon, (int, float)):
            try:
                distance = haversine_distance_meters(float(lat), float(lon), float(issue_lat), float(issue_lon))
            except (TypeError, ValueError):
                distance = None
            if distance > max_distance_meters:
                continue
        category_match = _clean_text(issue.get("category")).casefold() == _clean_text(category).casefold()
        candidates.append((issue, issue_text, distance, category_match))

    candidates.sort(key=lambda item: item[2] if item[2] is not None else float("inf"))
    candidates = candidates[:max(1, AI_DUPLICATE_MAX_CANDIDATES)]
    if not candidates:
        return _empty_duplicate_result("No eligible open reports were found for comparison.", "no-candidates")

    similarities, method, semantic = _semantic_or_lexical_scores(query_text, [item[1] for item in candidates])
    if requested_threshold is None:
        similarity_threshold = AI_DUPLICATE_THRESHOLD if semantic else AI_LEXICAL_DUPLICATE_THRESHOLD
    else:
        similarity_threshold = requested_threshold
    similarity_threshold = max(0.0, min(1.0, float(similarity_threshold)))
    scored = []
    for item, similarity in zip(candidates, similarities):
        issue, _text, distance, category_match = item
        geo_score = 0.0 if distance is None else max(0.0, 1.0 - (distance / max_distance_meters))
        combined = (similarity * 0.75) + (0.15 if category_match else 0.0) + (geo_score * 0.10 if distance is not None else 0.0)
        scored.append((combined, similarity, item))
    scored.sort(key=lambda value: value[0], reverse=True)

    matches = [
        _safe_match(item[0], item[2], similarity, item[3]) | {"decision_score": round(score, 4)}
        for score, similarity, item in scored
    ]
    best_score, best_similarity, best_item = scored[0]
    likely_duplicate = best_score >= similarity_threshold
    best_match = matches[0] if likely_duplicate else None
    evidence = [f"{method} similarity {best_similarity:.2f}"]
    if best_item[3]:
        evidence.append("same category")
    if best_item[2] is not None:
        evidence.append(f"{best_item[2]:.0f}m away")
    rationale = ("Potential duplicate candidate: " if likely_duplicate else "No likely duplicate: ") + ", ".join(evidence) + ". Human/officer review remains authoritative."
    return {
        "is_duplicate": likely_duplicate,
        "confidence": round(best_score, 2),
        "matched_issue": best_match,
        "potential_matches": matches[:5],
        "rationale": rationale,
        "method": method,
        "semantic_model_available": semantic,
        "threshold": similarity_threshold,
        "model_version": DUPLICATE_DETECTOR_VERSION,
    }


def _empty_duplicate_result(rationale: str, reason: str) -> Dict[str, Any]:
    return {
        "is_duplicate": False, "confidence": 0.0, "matched_issue": None,
        "potential_matches": [], "rationale": rationale, "method": "unavailable",
        "semantic_model_available": False, "reason": reason,
        "threshold": AI_DUPLICATE_THRESHOLD, "model_version": DUPLICATE_DETECTOR_VERSION,
    }


def _valid_gemini_priority(data: Any, category: str) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict) or data.get("priority") not in {"Low", "Medium", "High", "Urgent"}:
        return None
    try:
        score = float(data.get("priority_score"))
    except (TypeError, ValueError):
        return None
    if not 1.0 <= score <= 10.0 or not isinstance(data.get("rationale"), str):
        return None
    return {
        "priority": data["priority"], "priority_score": round(score, 1),
        "recommended_department": data.get("recommended_department") if data.get("recommended_department") in CATEGORIES.values() else CATEGORIES.get(category, CATEGORIES["Other"]),
        "ai_rationale": data["rationale"][:500], "method": "gemini-validated", "model_version": "gemini-configured",
    }


def _init_gemini_client():
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return genai.GenerativeModel("gemini-2.5-flash")
    except Exception:
        return None


def _gemini_priority(title: str, description: str, category: str, verification_count: int, duplicate_count: int) -> Optional[Dict[str, Any]]:
    if not AI_USE_GEMINI or not GEMINI_API_KEY:
        return None
    try:
        gemini = _init_gemini_client()
        if not gemini:
            return None
        prompt = f"Return only JSON with priority, priority_score (1-10), recommended_department, rationale. Category: {category}. Title: {title[:160]}. Description: {description[:1000]}. Verifications: {verification_count}. Duplicate candidates: {duplicate_count}."
        response = gemini.generate_content(prompt, request_options={"timeout": 5})
        match = re.search(r"\{.*\}", response.text.strip(), re.DOTALL)
        return _valid_gemini_priority(json.loads(match.group(0)), category) if match else None
    except Exception as error:
        logger.warning("External priority recommendation unavailable: %s", type(error).__name__)
        return None


def predict_issue_priority(title: str, description: str, category: str, verification_count: int = 0, duplicate_count: int = 0, image_path: Optional[str] = None) -> Dict[str, Any]:
    external = _gemini_priority(title, description, category, verification_count, duplicate_count)
    if external:
        return external
    category_key = category if category in CATEGORIES else "Other"
    base_scores = {"Traffic Signal Failure": 7.5, "Water Leakage": 6.5, "Drainage Problem": 7.0, "Pothole": 5.5, "Damaged Streetlight": 5.0, "Garbage Accumulation": 4.5, "Other": 4.0}
    score = base_scores[category_key]
    text = _issue_text(title, description).casefold()
    hazard_terms = ("accident", "danger", "burst", "overflow", "hazard", "blocked", "school", "hospital", "spark", "electric shock", "deep")
    matched_terms = [term for term in hazard_terms if term in text]
    score += min(2.0, len(matched_terms) * 0.8)
    score += min(2.0, max(0, int(verification_count or 0)) * 0.4)
    score += min(1.5, max(0, int(duplicate_count or 0)) * 0.5)
    score = round(max(1.0, min(10.0, score)), 1)
    priority = "Urgent" if score >= 8.5 else "High" if score >= 6.5 else "Medium" if score >= 4.5 else "Low"
    signals = [f"{category_key} baseline {base_scores[category_key]:.1f}"]
    if matched_terms:
        signals.append(f"hazard indicators: {', '.join(matched_terms)}")
    if verification_count:
        signals.append(f"{verification_count} community verification(s)")
    if duplicate_count:
        signals.append(f"{duplicate_count} duplicate candidate(s)")
    return {
        "priority": priority, "priority_score": score, "recommended_department": CATEGORIES[category_key],
        "ai_rationale": "Deterministic engineering baseline using " + "; ".join(signals) + ". This is a recommendation, not an approved priority.",
        "method": "deterministic-baseline", "model_version": PRIORITY_BASELINE_VERSION,
    }


def analyze_issue_image(image_file_path: str) -> Dict[str, Any]:
    gemini = _init_gemini_client() if AI_USE_GEMINI else None
    if not gemini or not os.path.exists(image_file_path):
        return {"success": False, "message": "Optional vision model is unavailable."}
    try:
        from PIL import Image
        image = Image.open(image_file_path)
        response = gemini.generate_content(["Return JSON with detected_category, damage_severity, and visual_summary for this civic issue image.", image], request_options={"timeout": 5})
        match = re.search(r"\{.*\}", response.text.strip(), re.DOTALL)
        return json.loads(match.group(0)) if match else {"success": False, "message": "Vision response was not valid JSON."}
    except Exception as error:
        logger.warning("Vision analysis unavailable: %s", type(error).__name__)
        return {"success": False, "message": "Vision analysis failed safely."}
