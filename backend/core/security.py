"""
Security utilities for Ops Copilot.
Handles password hashing and JWT token management.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY and (os.getenv("CI") == "true" or os.getenv("ENV") == "test"):
    SECRET_KEY = "test-secret-key-for-ci-and-testing"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

if not SECRET_KEY:
    # Fail fast: the application cannot function securely without a secret key.
    raise RuntimeError("CRITICAL: SECRET_KEY environment variable is not set. The application cannot start without it.")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if the provided password matches the hash in the DB."""
    # bcrypt.checkpw expects bytes
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash for a new password."""
    # bcrypt.hashpw expects bytes
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a signed JWT token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded if decoded.get("sub") else None
    except JWTError:
        return None

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def get_current_user(request: Request, token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """JWT token verification and user retrieval from header or cookie."""
    # 1. Try token from header (OAuth2 scheme)
    # 2. Try token from cookie
    actual_token = token or request.cookies.get("access_token")

    if not actual_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing"
        )

    payload = decode_access_token(actual_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("sub")
    try:
        import uuid
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format"
        )
    # Use the UUID object for the query
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

def require_admin(current_user: User = Depends(get_current_user)):
    """Enforce admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required"
        )
    return current_user
