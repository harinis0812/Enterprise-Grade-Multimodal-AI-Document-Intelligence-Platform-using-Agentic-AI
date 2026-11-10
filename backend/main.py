from contextlib import asynccontextmanager
import logging
import re
import time
import uuid

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api import admin, auth, document, qa
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.database.database import engine, get_db
from backend.database.init_db import init_database
from backend.database.models import AuditLog, User

logger = logging.getLogger("docuai.request")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce valid cryptographic security configuration at startup
    _ = settings.JWT_SECRET_KEY
    _ = settings.DOCUMENT_ENCRYPTION_KEY
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
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)


class RequestIDMiddleware:
    """
    Pure ASGI middleware that extracts or generates a unique X-Request-ID tracking header,
    attaches it to response headers, and records structured request latency without logging sensitive data.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_request_id = headers.get(b"x-request-id", b"").decode("utf-8", "ignore")
        if raw_request_id and re.match(r"^[a-zA-Z0-9\-_]{1,64}$", raw_request_id):
            request_id = raw_request_id
        else:
            request_id = str(uuid.uuid4())

        start_time = time.perf_counter()
        status_code = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
                resp_headers = list(message.get("headers", []))
                resp_headers.append((b"x-request-id", request_id.encode("utf-8")))
                message["headers"] = resp_headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            client = scope.get("client")
            client_ip = client[0] if client else "unknown"
            # Safe structured logging: Never log credentials, authorization headers, tokens, or document body
            logger.info(
                "request_id=%s method=%s path=%s status_code=%d duration_ms=%.2fms client_ip=%s",
                request_id,
                scope.get("method", "UNKNOWN"),
                scope.get("path", ""),
                status_code[0],
                duration_ms,
                client_ip
            )


# Add request tracking & structured latency logging middleware
app.add_middleware(RequestIDMiddleware)


# Include API routers
app.include_router(auth.router)
app.include_router(admin.router)
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
