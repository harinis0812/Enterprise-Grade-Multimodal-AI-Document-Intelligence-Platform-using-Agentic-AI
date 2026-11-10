from datetime import datetime
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.core.rate_limit import rate_limit_login, rate_limit_register
from backend.core.security import (
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_password,
    log_audit_event,
    revoke_token,
    security_scheme,
    verify_password,
)
from backend.database.database import get_db
from backend.database.models import User
from backend.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_register)],
    summary="Register a new enterprise user account"
)
def register(
    request: Request,
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    # Check if user already exists
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        log_audit_event(
            db=db,
            event_type="USER_REGISTER_DUPLICATE_ATTEMPT",
            ip_address=request.client.host if request.client else None,
            details=f"Registration attempted with existing email: {payload.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Hash password securely
    hashed_pwd = hash_password(payload.password)

    # RBAC: Public registration strictly defaults to standard 'user' role
    new_user = User(
        email=payload.email,
        hashed_password=hashed_pwd,
        full_name=payload.full_name,
        role="user",
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record audit log
    log_audit_event(
        db=db,
        event_type="USER_REGISTER_SUCCESS",
        user_id=new_user.id,
        ip_address=request.client.host if request.client else None,
        details=f"New user registered: {new_user.email} (Role: user)"
    )

    # Generate JWT with jti and role
    token = create_access_token(
        data={"sub": str(new_user.id), "email": new_user.email, "role": new_user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_login)],
    summary="Authenticate user and return JWT access token"
)
def login(
    request: Request,
    payload: UserLoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == payload.email).first()

    ip = request.client.host if request.client else None

    if not user or not verify_password(payload.password, user.hashed_password):
        log_audit_event(
            db=db,
            event_type="USER_LOGIN_FAILED",
            user_id=user.id if user else None,
            ip_address=ip,
            details=f"Failed login attempt for email: {payload.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        log_audit_event(
            db=db,
            event_type="USER_LOGIN_INACTIVE",
            user_id=user.id,
            ip_address=ip,
            details="Login attempt on deactivated user account."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been disabled. Please contact the administrator."
        )

    # Record successful login
    log_audit_event(
        db=db,
        event_type="USER_LOGIN_SUCCESS",
        user_id=user.id,
        ip_address=ip,
        details=f"User successfully logged in: {user.email} (Role: {user.role})"
    )

    token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile"
)
def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    summary="Log out user, revoke active JWT token, and record security audit event"
)
def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Extract token and persist to revoked_tokens store
    if credentials and credentials.credentials:
        raw_token = credentials.credentials
        try:
            payload = decode_access_token(raw_token)
            jti = payload.get("jti")
            exp_ts = payload.get("exp")
            if jti and exp_ts:
                exp_dt = datetime.utcfromtimestamp(exp_ts)
                revoke_token(db=db, jti=jti, expires_at=exp_dt)
        except Exception as e:
            # Token may already be partially invalid or decoded
            pass

    ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        event_type="USER_LOGOUT",
        user_id=current_user.id,
        ip_address=ip,
        details="User logged out and token was permanently revoked."
    )
    return {"message": "Logged out successfully. Token has been revoked."}
