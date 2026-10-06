from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.database.init_db import init_database
from backend.database.database import engine
from backend.api import document


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


app.include_router(document.router)


@app.get("/")
def root():

    return {
        "message":
        "Welcome to Enterprise Grade Multimodal AI Document Intelligence Platform!"
    }


@app.get("/about")
def about():

    return {
        "project":
        "Enterprise-Grade Multimodal AI Document Intelligence Platform using Agentic AI",

        "version": "1.0.0",

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
