from datetime import datetime, timedelta
from typing import Optional
import secrets
import jwt
import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from config import JWT_ALGORITHM, JWT_EXPIRATION_MINUTES, JWT_SECRET
from db import get_collection

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")

def _verify_legacy_sha256(password: str, stored_hash: str) -> bool:
    import hashlib
    if not stored_hash or ":" not in stored_hash:
        return False
    salt, hashed = stored_hash.split(":", 1)
    check = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(check, hashed)

def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            return False
    return _verify_legacy_sha256(password, stored_hash)

def is_legacy_password_hash(stored_hash: str) -> bool:
    return bool(stored_hash and ":" in stored_hash and not stored_hash.startswith("$2"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "iss": "civiclens", "typ": "access"})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer="civiclens",
            options={"require": ["exp", "iat", "iss", "sub", "typ"]},
        )
        if payload.get("typ") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    users_col = get_collection("users")
    user = users_col.find_one({"_id": payload["sub"]})
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    """Return the authenticated user when present, without making public reads private."""
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    return get_collection("users").find_one({"_id": payload["sub"]})

def require_roles(allowed_roles: list[str]):
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail=f"Access denied: required role in {allowed_roles}, current role is {user.get('role')}"
            )
        return user
    return role_checker
