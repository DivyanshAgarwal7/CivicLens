import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("DB_NAME", "civiclens")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
ALLOW_JSON_DB = os.getenv("ALLOW_JSON_DB", "true" if APP_ENV in {"development", "test"} else "false").strip().lower() == "true"

def _csv_env(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]

CORS_ORIGINS = _csv_env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
if APP_ENV == "production" and "*" in CORS_ORIGINS:
    raise RuntimeError("Wildcard CORS origins are not permitted in production.")
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
AI_EMBEDDING_MODEL = os.getenv("AI_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
AI_DUPLICATE_THRESHOLD = float(os.getenv("AI_DUPLICATE_THRESHOLD", "0.72"))
AI_LEXICAL_DUPLICATE_THRESHOLD = float(os.getenv("AI_LEXICAL_DUPLICATE_THRESHOLD", "0.38"))
AI_DUPLICATE_MAX_DISTANCE_METERS = float(os.getenv("AI_DUPLICATE_MAX_DISTANCE_METERS", "400"))
AI_DUPLICATE_MAX_CANDIDATES = int(os.getenv("AI_DUPLICATE_MAX_CANDIDATES", "50"))
AI_USE_GEMINI = os.getenv("AI_USE_GEMINI", "false").strip().lower() == "true"

JWT_SECRET = os.getenv("JWT_SECRET", "")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is required. Set it in backend/.env before starting the API.")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CLOUDINARY_URL = os.getenv("CLOUDINARY_URL", "")

SMTP_SERVER = os.getenv("SMTP_SERVER", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@civiclens.gov")
