import json
import re
import uuid
from pathlib import Path

import anyio.to_thread
import fitz
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.agents.document_agent import DocumentAgent
from backend.core.security import get_current_user, log_audit_event
from backend.database.database import get_db
from backend.database.models import Document, User
from backend.services.multimodal_service import (
    extract_multimodal_image,
    extract_multimodal_pdf,
)
from backend.services.ocr_service import extract_text_from_image
from backend.services.pdf_service import extract_text_from_pdf
from mlops.tracking import log_document_processing

router = APIRouter()


# Temporary upload directory used only while processing a document.
UPLOAD_DIR = Path("backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Supported document formats.
ALLOWED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
}


# Maximum upload size: 10 MB.
MAX_FILE_SIZE = 10 * 1024 * 1024

# Maximum allowed PDF page count to safeguard against resource exhaustion.
MAX_PDF_PAGES = 100


def safe_filename(filename: str) -> str:
    """
    Convert the uploaded filename into a safe filesystem filename.
    """
    name = Path(filename or "").name

    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    stem = stem[:180] or "document"

    return f"{stem}{suffix}"


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None

    # ---------------------------------------------------------
    # 1. Validate filename
    # ---------------------------------------------------------
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required"
        )

    # ---------------------------------------------------------
    # 2. Detect file type automatically
    # ---------------------------------------------------------
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                "Allowed formats: PDF, JPG, JPEG, PNG"
            )
        )

    # ---------------------------------------------------------
    # 3. Read uploaded file
    # ---------------------------------------------------------
    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    # ---------------------------------------------------------
    # 4. Validate file size
    # ---------------------------------------------------------
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 10 MB"
        )

    # Validate page limit for PDF files
    if extension == ".pdf":
        try:
            with fitz.open(stream=contents, filetype="pdf") as doc_check:
                if len(doc_check) > MAX_PDF_PAGES:
                    raise HTTPException(
                        status_code=400,
                        detail=f"PDF exceeds maximum allowed limit of {MAX_PDF_PAGES} pages."
                    )
        except HTTPException:
            raise
        except Exception as pdf_err:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupted PDF file: {str(pdf_err)}"
            )

    filename = safe_filename(file.filename)

    # Unique temporary filename per upload to eliminate concurrency collisions
    # and prevent cross-user temporary file overwriting
    unique_upload_id = uuid.uuid4().hex
    temp_filename = f"user_{current_user.id}_{unique_upload_id}_{filename}"
    file_path = UPLOAD_DIR / temp_filename

    try:
        # -----------------------------------------------------
        # 5. Save uploaded file temporarily
        # -----------------------------------------------------
        file_path.write_bytes(contents)

        # -----------------------------------------------------
        # 6. Automatic document extraction (Multimodal Pipeline)
        # Offloaded to worker thread via anyio.to_thread.run_sync
        # to ensure the FastAPI asyncio event loop remains non-blocking.
        # -----------------------------------------------------
        try:
            if extension == ".pdf":
                multimodal_res = await anyio.to_thread.run_sync(extract_multimodal_pdf, contents)
                extracted_text = multimodal_res.full_text
                multimodal_meta = multimodal_res.summary_metadata
            else:
                multimodal_res = await anyio.to_thread.run_sync(extract_multimodal_image, str(file_path))
                extracted_text = multimodal_res.full_text
                multimodal_meta = multimodal_res.summary_metadata
        except Exception as parse_error:
            raise HTTPException(
                status_code=400,
                detail=f"Corrupted or invalid document file: {str(parse_error)}"
            )

        extracted_text = extracted_text.strip()

        # -----------------------------------------------------
        # 7. Handle documents where no text was extracted
        # -----------------------------------------------------
        if not extracted_text:
            status = "needs_review"
        else:
            status = "processed"

        # -----------------------------------------------------
        # 8. Run Agentic AI document workflow (non-blocking)
        # -----------------------------------------------------
        agent = DocumentAgent()

        result = await anyio.to_thread.run_sync(
            agent.process,
            filename,
            extracted_text
        )

        # -----------------------------------------------------
        # 9. Read Agentic AI results
        # -----------------------------------------------------
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

        supervisor_decision = result.get(
            "supervisor_decision",
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

        # -----------------------------------------------------
        # 10. Store processed result in DB with user ownership
        # -----------------------------------------------------
        try:
            document = Document(
                filename=filename,
                document_type=document_type,
                status=status,
                extracted_text=extracted_text,
                user_id=current_user.id,
                analysis=json.dumps(
                    {
                        "document_information": document_information,
                        "analysis": analysis,
                        "supervisor_decision": supervisor_decision,
                        "verification": verification,
                        "multimodal_metadata": multimodal_meta
                    }
                ),
                agent_trace=json.dumps(agent_trace)
            )

            db.add(document)
            db.commit()
            db.refresh(document)

            # Security Audit Log (Never log file contents or tokens)
            log_audit_event(
                db=db,
                event_type="DOCUMENT_UPLOAD_SUCCESS",
                user_id=current_user.id,
                ip_address=ip,
                details=f"Document uploaded: ID {document.id}, {filename} ({document_type})"
            )

            # -------------------------------------------------
            # 11. MLflow tracking
            # -------------------------------------------------
            try:
                log_document_processing(
                    document_type=document_type,
                    word_count=len(extracted_text.split()),
                    status=status
                )
            except Exception as mlflow_error:
                print(
                    f"[MLflow] Tracking warning: "
                    f"{mlflow_error}"
                )

            # -------------------------------------------------
            # 12. Return processed result
            # -------------------------------------------------
            return {
                "id": document.id,
                "filename": document.filename,
                "document_type": document.document_type,
                "status": document.status,
                "user_id": document.user_id,
                "message": "Document processed successfully"
            }

        except Exception:
            db.rollback()
            raise

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(error)}"
        )

    finally:
        # -----------------------------------------------------
        # 13. Delete temporary uploaded file
        # -----------------------------------------------------
        await file.close()

        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as cleanup_error:
                import gc
                gc.collect()
                try:
                    file_path.unlink()
                except Exception:
                    print(
                        f"[Upload Cleanup] Warning: "
                        f"Could not delete temporary file "
                        f"{file_path}: {cleanup_error}"
                    )


# =============================================================
# GET ALL DOCUMENTS (Strictly scoped to authenticated owner)
# =============================================================

@router.get("/documents")
def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Returns documents strictly owned by the authenticated user
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
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
                "user_id": document.user_id,
                "created_at": document.created_at
            }
            for document in documents
        ]
    }


# =============================================================
# GET SINGLE DOCUMENT (Scoped with strict access control)
# =============================================================

@router.get("/documents/{document_id}")
def get_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # Multi-tenant isolation: enforce strict ownership; unowned/NULL documents are denied
    if document.user_id != current_user.id:
        log_audit_event(
            db=db,
            event_type="CROSS_USER_ACCESS_DENIED",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Unauthorized access attempt to document {document_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Access denied. You do not have permission to view this document."
        )

    log_audit_event(
        db=db,
        event_type="DOCUMENT_ACCESS",
        user_id=current_user.id,
        ip_address=ip,
        details=f"Document retrieved: ID {document_id}"
    )

    return {
        "id": document.id,
        "filename": document.filename,
        "document_type": document.document_type,
        "status": document.status,
        "user_id": document.user_id,
        "extracted_text": document.extracted_text,
        "analysis": document.analysis,
        "agent_trace": document.agent_trace,
        "created_at": document.created_at
    }