import json
import os
import re
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Document
from backend.agents.document_agent import DocumentAgent
from backend.services.pdf_service import extract_text_from_pdf
from backend.services.ocr_service import extract_text_from_image


router = APIRouter()

UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def safe_filename(filename: str) -> str:
    """Return a filesystem-safe filename."""
    name = Path(filename or "").name
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    stem = stem[:180] or "document"

    return f"{stem}{suffix}"


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, JPG, JPEG, PNG"
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 10 MB"
        )

    filename = safe_filename(file.filename)
    file_path = UPLOAD_DIR / filename

    try:
        file_path.write_bytes(contents)

        if extension == ".pdf":
            extracted_text = extract_text_from_pdf(str(file_path))
        else:
            extracted_text = extract_text_from_image(str(file_path))

        if not extracted_text.strip():
            status = "needs_review"
        else:
            status = "processed"

        agent = DocumentAgent()

        result = agent.process(
            filename,
            extracted_text
        )

        document_type = result.get(
            "document_type",
            "Unknown"
        )

        document_information = result.get(
            "document_information",
            {}
        )

        analysis = result.get(
            "analysis",
            {}
        )

        verification = result.get(
            "verification",
            {}
        )

        agent_trace = result.get(
            "agent_trace",
            []
        )

        status = result.get(
            "status",
            status
        )

        db: Session = SessionLocal()

        try:
            document = Document(
                filename=filename,
                document_type=document_type,
                status=status,
                extracted_text=extracted_text,
                analysis=json.dumps(
                    {
                        "document_information": document_information,
                        "analysis": analysis,
                        "verification": verification
                    }
                ),
                agent_trace=json.dumps(agent_trace)
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            return {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "status": document.status,
                "message": "Document processed successfully"
            }

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}"
        )

    finally:
        await file.close()


@router.get("/documents")
def get_documents():

    db: Session = SessionLocal()

    try:
        documents = (
            db.query(Document)
            .order_by(Document.id.desc())
            .all()
        )

        return {
            "count": len(documents),
            "documents": [
                {
                    "id": document.id,
                    "filename": document.filename,
                    "document_type": document.document_type,
                    "status": document.status,
                    "created_at": document.created_at
                }
                for document in documents
            ]
        }

    finally:
        db.close()


@router.get("/documents/{document_id}")
def get_document(document_id: int):

    db: Session = SessionLocal()

    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )

        if not document:
            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )

        return {
            "id": document.id,
            "filename": document.filename,
            "document_type": document.document_type,
            "status": document.status,
            "extracted_text": document.extracted_text,
            "analysis": document.analysis,
            "agent_trace": document.agent_trace,
            "created_at": document.created_at
        }

    finally:
        db.close()
