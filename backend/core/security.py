from datetime import datetime, timedelta
from typing import Optional
import uuid

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.database.database import get_db
from backend.database.models import AuditLog, RevokedToken, User

security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """
    Securely hash a password using bcrypt.
    Never stores plaintext passwords.
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored bcrypt hash.
    """
    try:
        plain_bytes = plain_password.encode("utf-8")
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a signed JWT access token with a unique jti claim for revocation tracking.
    """
    to_encode = data.copy()
    if "jti" not in to_encode:
        to_encode["jti"] = uuid.uuid4().hex

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def is_token_revoked(db: Session, jti: Optional[str]) -> bool:
    """
    Checks whether a JWT unique identifier (jti) has been recorded in the revocation store.
    """
    if not jti:
        return False
    return db.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None


def revoke_token(
    db: Session,
    jti: str,
    expires_at: datetime,
    token_type: str = "access"
) -> RevokedToken:
    """
    Adds a JWT to the server-side revocation store.
    """
    revoked = RevokedToken(
        jti=jti,
        token_type=token_type,
        expires_at=expires_at,
        revoked_at=datetime.utcnow()
    )
    db.add(revoked)
    db.commit()
    return revoked


def cleanup_expired_revoked_tokens(db: Session) -> int:
    """
    Removes expired entries from the revoked_tokens store to prevent unbounded growth.
    """
    deleted = (
        db.query(RevokedToken)
        .filter(RevokedToken.expires_at < datetime.utcnow())
        .delete()
    )
    db.commit()
    return deleted


def decode_access_token(token: str) -> dict:
    """
    Decode and validate JWT access token signature and expiration.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to extract and verify the current authenticated user.
    Enforces signature verification, expiration check, and server-side revocation check.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = decode_access_token(token)

    # Server-side revocation verification
    jti = payload.get("jti")
    if jti and is_token_revoked(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token payload.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or has been disabled.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional user dependency: returns authenticated User if token is present and valid,
    otherwise returns None without raising an exception.
    """
    if not credentials or not credentials.credentials:
        return None

    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        jti = payload.get("jti")
        if jti and is_token_revoked(db, jti):
            return None

        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = int(user_id_str)
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
    except Exception:
        return None


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    FastAPI dependency enforcing Administrator role for protected management endpoints.
    """
    if getattr(current_user, "role", "user") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Administrator privileges required."
        )
    return current_user


def log_audit_event(
    db: Session,
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    details: Optional[str] = None
):
    """
    Record an enterprise audit log event.
    NEVER logs passwords, tokens, or private document contents.
    """
    try:
        audit_entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            details=details,
            created_at=datetime.utcnow()
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Audit Log] Warning: Failed to record audit log: {e}")
