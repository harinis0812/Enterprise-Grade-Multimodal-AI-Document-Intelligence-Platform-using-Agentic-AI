from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
import json

from backend.services.pdf_service import extract_text_from_pdf
from backend.services.ocr_service import extract_text_from_image
from backend.services.document_classifier import detect_document_type
from backend.services.document_intelligence import analyze_document

from backend.agents.graph_workflow import DocumentGraphWorkflow

from backend.database.database import SessionLocal
from backend.database.models import Document


router = APIRouter()

UPLOAD_FOLDER = "backend/uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Create LangGraph workflow
document_workflow = DocumentGraphWorkflow()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):

    # ==========================================
    # 1. SAVE UPLOADED FILE
    # ==========================================

    file_path = os.path.join(
        UPLOAD_FOLDER,
        file.filename
    )

    with open(file_path, "wb") as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )


    # ==========================================
    # 2. EXTRACT TEXT
    # ==========================================

    extracted_text = ""

    filename = file.filename.lower()


    if filename.endswith(".pdf"):

        extracted_text = extract_text_from_pdf(
            file_path
        )


    elif filename.endswith(
        (".jpg", ".jpeg", ".png")
    ):

        extracted_text = extract_text_from_image(
            file_path
        )


    else:

        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )


    # ==========================================
    # 3. RUN LANGGRAPH AGENT WORKFLOW
    # ==========================================

    workflow_result = document_workflow.process(
        file.filename,
        extracted_text
    )


    # ==========================================
    # 4. GET RESULTS FROM LANGGRAPH
    # ==========================================

    document_type = workflow_result.get(
        "document_type",
        "General Document"
    )

    document_information = workflow_result.get(
        "document_information",
        {}
    )

    analysis = workflow_result.get(
        "analysis",
        {}
    )

    supervisor_decision = workflow_result.get(
        "supervisor_decision",
        {}
    )

    verification = workflow_result.get(
        "verification",
        {}
    )


    # ==========================================
    # 5. DATABASE
    # ==========================================

    db = SessionLocal()

    try:

        new_document = Document(

            filename=file.filename,

            document_type=document_type,

            extracted_text=extracted_text,

            extracted_information=json.dumps(
                document_information
            )
        )


        db.add(new_document)

        db.commit()

        db.refresh(new_document)

        document_id = new_document.id

    finally:

        db.close()


    # ==========================================
    # 6. FINAL RESPONSE
    # ==========================================

    return {

        "id": document_id,

        "filename": file.filename,

        "message":
            "Document processed successfully",

        "document_type":
            document_type,

        "document_information":
            document_information,

        "analysis":
            analysis,

        "supervisor_decision":
            supervisor_decision,

        "verification":
            verification,

        "workflow_status":
            workflow_result.get(
                "status",
                "completed"
            ),

        "text":
            extracted_text[:2000]
    }


# ==================================================
# GET ALL DOCUMENTS
# ==================================================

@router.get("/documents")
def get_documents():

    db = SessionLocal()

    try:

        documents = db.query(
            Document
        ).all()

        results = []

        for document in documents:

            results.append({

                "id":
                    document.id,

                "filename":
                    document.filename,

                "document_type":
                    document.document_type,

                "document_information":
                    json.loads(
                        document.extracted_information
                    ),

                "uploaded_at":
                    document.uploaded_at
            })

        return results

    finally:

        db.close()


# ==================================================
# GET SINGLE DOCUMENT
# ==================================================

@router.get("/documents/{document_id}")
def get_document(document_id: int):

    db = SessionLocal()

    try:

        document = db.query(
            Document
        ).filter(
            Document.id == document_id
        ).first()


        if not document:

            raise HTTPException(
                status_code=404,
                detail="Document not found"
            )


        return {

            "id":
                document.id,

            "filename":
                document.filename,

            "document_type":
                document.document_type,

            "document_information":
                json.loads(
                    document.extracted_information
                ),

            "extracted_text":
                document.extracted_text,

            "uploaded_at":
                document.uploaded_at
        }

    finally:

        db.close()