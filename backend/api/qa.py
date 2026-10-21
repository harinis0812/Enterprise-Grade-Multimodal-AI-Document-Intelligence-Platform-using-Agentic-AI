import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.security import get_current_user, log_audit_event
from backend.database.database import get_db
from backend.database.models import Document, QAHistory, User
from backend.schemas.qa import (
    Citation,
    QAHistoryItem,
    QAHistoryResponse,
    QARequest,
    QAResponse,
)
from backend.services.qa_service import DocumentQAService

router = APIRouter(tags=["Document Question Answering"])
qa_engine = DocumentQAService()


@router.post(
    "/documents/{document_id}/qa",
    response_model=QAResponse,
    summary="Ask questions about an uploaded document"
)
def ask_document_question(
    document_id: int,
    payload: QARequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None

    # Retrieve target document
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        log_audit_event(
            db=db,
            event_type="DOCUMENT_QA_NOT_FOUND",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Query attempted on non-existent document ID: {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Multi-tenant ownership check
    if document.user_id is not None and document.user_id != current_user.id:
        log_audit_event(
            db=db,
            event_type="CROSS_USER_ACCESS_DENIED",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Unauthorized Q&A attempt on document {document_id} owned by user {document.user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to query this document."
        )

    # Claim legacy documents if unassigned
    if document.user_id is None:
        document.user_id = current_user.id
        db.commit()

    # Process question with Q&A engine
    document_text = document.extracted_text or ""
    answer, citations, has_evidence = qa_engine.answer_question(
        document_text=document_text,
        question=payload.question
    )

    # Persist Q&A turn in QAHistory
    qa_record = QAHistory(
        document_id=document.id,
        user_id=current_user.id,
        question=payload.question,
        answer=answer,
        citations=json.dumps(citations),
        created_at=datetime.utcnow()
    )
    db.add(qa_record)
    db.commit()
    db.refresh(qa_record)

    # Log audit event (safe summary: no private doc text or secret queries)
    log_audit_event(
        db=db,
        event_type="DOCUMENT_QA_SUCCESS",
        user_id=current_user.id,
        ip_address=ip,
        details=f"Q&A executed on document ID {document.id}. Evidence found: {has_evidence}."
    )

    parsed_citations = [
        Citation(
            quote=c.get("quote", ""),
            page_number=c.get("page_number"),
            confidence=c.get("confidence", 1.0)
        )
        for c in citations
    ]

    return QAResponse(
        document_id=document.id,
        question=payload.question,
        answer=answer,
        citations=parsed_citations,
        has_sufficient_evidence=has_evidence,
        created_at=qa_record.created_at
    )


@router.get(
    "/documents/{document_id}/qa/history",
    response_model=QAHistoryResponse,
    summary="Get conversation history for a document scoped to the authenticated user"
)
def get_document_qa_history(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found."
        )

    # Multi-tenant ownership check
    if document.user_id is not None and document.user_id != current_user.id:
        log_audit_event(
            db=db,
            event_type="CROSS_USER_ACCESS_DENIED",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Unauthorized history view attempt on document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to view history for this document."
        )

    records = (
        db.query(QAHistory)
        .filter(
            QAHistory.document_id == document_id,
            QAHistory.user_id == current_user.id
        )
        .order_by(QAHistory.created_at.asc())
        .all()
    )

    history_items = []
    for r in records:
        try:
            parsed_citations = json.loads(r.citations) if r.citations else []
        except Exception:
            parsed_citations = []

        history_items.append(
            QAHistoryItem(
                id=r.id,
                document_id=r.document_id,
                question=r.question,
                answer=r.answer,
                citations=[
                    Citation(
                        quote=c.get("quote", ""),
                        page_number=c.get("page_number"),
                        confidence=c.get("confidence", 1.0)
                    )
                    for c in parsed_citations
                ],
                created_at=r.created_at
            )
        )

    return QAHistoryResponse(
        document_id=document_id,
        count=len(history_items),
        history=history_items
    )
