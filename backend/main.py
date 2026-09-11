from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.document import router as document_router


app = FastAPI(
    title="Enterprise Grade Multimodal AI Document Intelligence Platform",
    description="Agentic AI powered enterprise document processing system",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(document_router)