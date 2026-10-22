from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

def validate_password_strength(value: str) -> str:
    """Validate new-password policy without ever logging or returning the value."""
    if not value or not value.strip():
        raise ValueError("Password must not be empty or whitespace-only.")
    if len(value) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(char.islower() for char in value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one digit.")
    if not any(not char.isalnum() for char in value):
        raise ValueError("Password must contain at least one special character.")
    return value

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=72)
    password_confirmation: Optional[str] = Field(default=None, max_length=72)
    full_name: str
    phone: Optional[str] = ""

    _validate_password = field_validator("password")(validate_password_strength)

    @model_validator(mode="after")
    def validate_confirmation(self):
        if self.password_confirmation is not None and self.password != self.password_confirmation:
            raise ValueError("Password confirmation does not match password.")
        return self

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = ""
    role: str
    department: Optional[str] = None
    trust_score: int = 100
    created_at: str

class LocationInput(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    address: str = Field(min_length=2, max_length=300)
    ward: Optional[str] = Field(default="Kothrud Ward", max_length=100)

class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=1, max_length=80)
    location: LocationInput
    image_urls: List[str] = Field(default_factory=list, max_length=5)
    # Advisory result from the authenticated duplicate pre-check. The backend
    # uses it only to avoid repeating the same expensive analysis immediately.
    duplicate_analysis: Optional[Dict[str, Any]] = None

class DuplicateCheckRequest(BaseModel):
    title: str
    description: str
    category: str
    latitude: float
    longitude: float

class VerificationCreate(BaseModel):
    comment: Optional[str] = Field(default="", max_length=500)

class OfficerPriorityReviewRequest(BaseModel):
    priority: str = Field(pattern="^(Low|Medium|High|Urgent)$")
    review_notes: str = Field(default="", max_length=1000)

class OfficerAssignRequest(BaseModel):
    department: str = Field(min_length=1, max_length=120)
    field_engineer_id: Optional[str] = None
    priority: Optional[str] = None
    officer_notes: Optional[str] = Field(default="", max_length=1000)

class EngineerResolutionRequest(BaseModel):
    status: str = Field(default="Resolved", pattern="^(In Progress|Resolved)$")
    completion_notes: str = Field(min_length=1, max_length=2000)
    evidence_image_url: Optional[str] = ""

class NotificationResponse(BaseModel):
    id: str
    recipient_id: str
    title: str
    message: str
    type: str
    read: bool
    created_at: str
    link: Optional[str] = None

class AuditLogEntry(BaseModel):
    action: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    details: Dict[str, Any] = {}
