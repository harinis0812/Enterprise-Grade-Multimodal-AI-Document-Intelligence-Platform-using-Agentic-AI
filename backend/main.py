from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from backend.database.database import engine
from backend.database.init_db import init_database
from backend.database.models import Document
from backend.api.document import router as document_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Enterprise Grade Multimodal AI Document Intelligence Platform",
    description="Agentic AI powered enterprise document processing system",
    version="1.0.0",
    lifespan=lifespan
)

init_database()

@app.get("/")
def home():
    return {
        "message": "Enterprise Grade Multimodal AI Document Intelligence Platform",
        "status": "running",
        "architecture": "Agentic AI"
    }


@app.get("/about")
def about():
    return {
        "project": "Enterprise Grade Multimodal AI Document Intelligence Platform",
        "version": "1.0.0",
        "technology": [
            "FastAPI",
            "PyMuPDF",
            "PaddleOCR",
            "LangGraph",
            "SQLAlchemy",
            "PostgreSQL",
            "MLflow",
            "Docker",
            "Kubernetes"
        ]
    }


@app.get("/health")
def health():
    database_status = "connected"

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    return {
        "status": "healthy",
        "service": "DocuAI",
        "database": database_status
    }


app.include_router(document_router)