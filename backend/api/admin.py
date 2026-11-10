from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.security import get_current_user, log_audit_event, require_admin
from backend.database.database import get_db
from backend.database.models import Document, QAHistory, RevokedToken, User
from backend.schemas.auth import UserResponse

router = APIRouter(prefix="/admin", tags=["Administration"])


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., description="Role to assign: 'user' or 'admin'")


class AdminStatsResponse(BaseModel):
    total_users: int
    total_documents: int
    total_qa_queries: int
    total_revoked_tokens: int


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all registered platform users (Admin only)"
)
def list_all_users(
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        event_type="ADMIN_LIST_USERS",
        user_id=admin_user.id,
        ip_address=ip,
        details="Admin viewed user directory"
    )
    users = db.query(User).order_by(User.id.asc()).all()
    return [UserResponse.model_validate(u) for u in users]


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update a user's role (Admin only)"
)
def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    target_role = payload.role.strip().lower()
    if target_role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'user' or 'admin'."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found."
        )

    old_role = target_user.role
    target_user.role = target_role
    db.commit()
    db.refresh(target_user)

    ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        event_type="ADMIN_USER_ROLE_CHANGED",
        user_id=admin_user.id,
        ip_address=ip,
        details=f"Admin {admin_user.email} changed role of user ID {target_user.id} ({target_user.email}) from '{old_role}' to '{target_role}'"
    )

    return UserResponse.model_validate(target_user)


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="System-wide administration metrics (Admin only)"
)
def get_system_stats(
    request: Request,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    log_audit_event(
        db=db,
        event_type="ADMIN_VIEW_STATS",
        user_id=admin_user.id,
        ip_address=ip,
        details="Admin viewed system metrics"
    )
    return AdminStatsResponse(
        total_users=db.query(User).count(),
        total_documents=db.query(Document).count(),
        total_qa_queries=db.query(QAHistory).count(),
        total_revoked_tokens=db.query(RevokedToken).count(),
    )
