import json
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.models import Document
from backend.agents.document_agent import DocumentAgent
from backend.services.pdf_service import extract_text_from_pdf
from backend.services.ocr_service import extract_text_from_image


router = APIRouter()

UPLOAD_DIR = "backend/uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    contents = await file.read()

    with open(file_path, "wb") as output_file:
        output_file.write(contents)

    db: Session = SessionLocal()

    try:

        # -----------------------------
        # DOCUMENT EXTRACTION
        # -----------------------------

        if extension == ".pdf":
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_image(file_path)

        # -----------------------------
        # AGENTIC AI WORKFLOW
        # -----------------------------

        agent = DocumentAgent()

        result = agent.process(
            file.filename,
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
            "processed"
        )

        # -----------------------------
        # DATABASE STORAGE
        # -----------------------------

        document = Document(
            filename=file.filename,
            document_type=document_type,
            status=status,
            extracted_text=extracted_text,
            analysis=json.dumps({
                "document_information": document_information,
                "analysis": analysis,
                "verification": verification
            }),
            agent_trace=json.dumps(agent_trace)
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # -----------------------------
        # RESPONSE
        # -----------------------------

        return {
            "message": "Document processed successfully",
            "document_id": document.id,
            "filename": file.filename,
            "document_type": document_type,
            "document_information": document_information,
            "analysis": analysis,
            "verification": verification,
            "agent_trace": agent_trace,
            "status": status,
            "extracted_text": extracted_text
        }

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}"
        )

    finally:

        db.close()


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
