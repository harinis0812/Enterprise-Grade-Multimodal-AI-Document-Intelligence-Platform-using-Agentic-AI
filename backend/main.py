from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api import auth, document, qa
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.database.database import engine, get_db
from backend.database.init_db import init_database
from backend.database.models import AuditLog, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Agentic AI powered enterprise document processing and question answering system",
    version=settings.VERSION,
    lifespan=lifespan
)


# Secure CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"]
)


# Include API routers
app.include_router(auth.router)
app.include_router(document.router)
app.include_router(qa.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to Enterprise Grade Multimodal AI Document Intelligence Platform!"
    }


@app.get("/about")
def about():
    return {
        "project": "Enterprise-Grade Multimodal AI Document Intelligence Platform using Agentic AI",
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        database_status = "connected"

        return {
            "status": "healthy",
            "service": "DocuAI",
            "database": database_status
        }

    except Exception as error:
        return {
            "status": "unhealthy",
            "service": "DocuAI",
            "database": "disconnected",
            "error": str(error)
        }


@app.get("/audit-logs")
def get_user_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns security audit logs scoped to the authenticated user.
    """
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "event_type": log.event_type,
                "ip_address": log.ip_address,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in logs
        ]
    }
