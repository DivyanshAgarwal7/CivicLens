import json
import hashlib
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Optional
from config import DATA_DIR, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL
from db import get_collection
from db import DuplicateKeyError
from pymongo.errors import DuplicateKeyError as MongoDuplicateKeyError

EMAIL_LOG_FILE = DATA_DIR / "emails.json"

def _append_email_log(email_record: dict):
    try:
        if EMAIL_LOG_FILE.exists():
            with open(EMAIL_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []
        logs.insert(0, email_record)
        with open(EMAIL_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs[:100], f, indent=2)
    except Exception as e:
        print(f"[Notification] Failed to log simulated email: {e}")

def send_notification(
    recipient_id: str,
    recipient_email: str,
    title: str,
    message: str,
    notification_type: str = "status_change",
    link: Optional[str] = None
):
    try:
        notifications_col = get_collection("notifications")
        notifications_col.create_index("notification_key", unique=True)
    except Exception as error:
        print(f"[Notification] Persistence unavailable: {type(error).__name__}")
        return {"created": False, "reason": "persistence_failed"}
    # 1. In-App Notification (Database)
    now_iso = datetime.utcnow().isoformat()
    notification_key = hashlib.sha256(
        f"{recipient_id}|{notification_type}|{title}|{link or ''}".encode("utf-8")
    ).hexdigest()
    doc = {
        "notification_key": notification_key,
        "recipient_id": recipient_id,
        "recipient_email": recipient_email,
        "title": title,
        "message": message,
        "type": notification_type,
        "read": False,
        "created_at": now_iso,
        "link": link
    }
    try:
        notifications_col.insert_one(doc)
    except (DuplicateKeyError, MongoDuplicateKeyError):
        return {"created": False, "reason": "duplicate"}
    except Exception as error:
        print(f"[Notification] In-app persistence failed: {type(error).__name__}")
        return {"created": False, "reason": "persistence_failed"}

    # 2. Email Notification (Simulated + real SMTP if configured)
    email_entry = {
        "to": recipient_email,
        "from": SMTP_FROM_EMAIL,
        "subject": f"[CivicLens Alert] {title}",
        "body": message,
        "timestamp": now_iso,
        "status": "Delivered (Simulated)"
    }

    if SMTP_SERVER and SMTP_USERNAME and SMTP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg["From"] = SMTP_FROM_EMAIL
            msg["To"] = recipient_email
            msg["Subject"] = f"[CivicLens Alert] {title}"
            msg.attach(MIMEText(message, "plain"))
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=5) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            email_entry["status"] = "Sent via SMTP"
        except Exception:
            email_entry["status"] = "SMTP delivery failed; retained in in-app log"

    _append_email_log(email_entry)
    print(f"[Notification] Sent '{title}' to {recipient_email}")
    return {"created": True, "email_status": email_entry["status"]}

def get_recent_emails():
    if not EMAIL_LOG_FILE.exists():
        return []
    try:
        with open(EMAIL_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
