import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.core.security import get_current_user, log_audit_event
from backend.database.database import get_db
from backend.database.models import Document, QAHistory, User, MultiDocQAHistory
from backend.schemas.qa import (
    Citation,
    MultiDocumentCitation,
    MultiQAHistoryItem,
    MultiQAHistoryResponse,
    MultiQARequest,
    MultiQAResponse,
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

    # Multi-tenant ownership check: enforce strict ownership; unowned/NULL documents are denied
    if document.user_id != current_user.id:
        log_audit_event(
            db=db,
            event_type="CROSS_USER_ACCESS_DENIED",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Unauthorized Q&A attempt on document {document_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not have permission to query this document."
        )

    # Process question with upgraded generative Q&A engine
    document_text = document.extracted_text or ""
    qa_result = qa_engine.answer_question(
        document_text=document_text,
        question=payload.question,
        document_id=document.id,
        filename=document.filename
    )
    answer, citations, has_evidence = qa_result
    answer_mode = getattr(qa_result, "answer_mode", "generative")
    model_used = getattr(qa_result, "model_used", None)
    retrieval_relevance = getattr(qa_result, "retrieval_relevance", 0.0)

    # Persist Q&A turn in QAHistory (encrypted at rest)
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
        details=f"Q&A executed on document ID {document.id}. Mode: {answer_mode}. Evidence found: {has_evidence}."
    )

    parsed_citations = [
        Citation(
            quote=c.get("quote", ""),
            page_number=c.get("page_number"),
            confidence=c.get("confidence", 1.0),
            relevance_score=c.get("relevance_score", c.get("confidence", 1.0)),
            evidence_type=c.get("evidence_type", "text")
        )
        for c in citations
    ]

    return QAResponse(
        document_id=document.id,
        question=payload.question,
        answer=answer,
        citations=parsed_citations,
        has_sufficient_evidence=has_evidence,
        answer_mode=answer_mode,
        model_used=model_used,
        retrieval_relevance=retrieval_relevance,
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

    # Multi-tenant ownership check: enforce strict ownership; unowned/NULL documents are denied
    if document.user_id != current_user.id:
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
                        confidence=c.get("confidence", 1.0),
                        relevance_score=c.get("relevance_score", c.get("confidence", 1.0)),
                        evidence_type=c.get("evidence_type", "text")
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


@router.post(
    "/documents/multi-qa",
    response_model=MultiQAResponse,
    summary="Ask questions across multiple owned documents"
)
def ask_multi_document_question(
    payload: MultiQARequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    doc_ids = payload.document_ids

    # 1. Fetch requested documents
    documents = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    found_map = {d.id: d for d in documents}

    # 2. Validate existence of every requested document
    missing_ids = [d_id for d_id in doc_ids if d_id not in found_map]
    if missing_ids:
        log_audit_event(
            db=db,
            event_type="MULTI_DOC_QA_NOT_FOUND",
            user_id=current_user.id,
            ip_address=ip,
            details=f"Missing document IDs in multi-doc query: {missing_ids}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documents with IDs {missing_ids} were not found."
        )

    # 3. Strict multi-tenant isolation: check ownership of ALL documents
    for doc in documents:
        if doc.user_id != current_user.id:
            log_audit_event(
                db=db,
                event_type="CROSS_USER_ACCESS_DENIED",
                user_id=current_user.id,
                ip_address=ip,
                details=f"Unauthorized multi-doc query attempt on document ID {doc.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. You do not have permission to query document ID {doc.id}."
            )

    # 4. Build documents input list for qa_engine
    docs_input = [
        {"id": d.id, "filename": d.filename, "text": d.extracted_text or ""}
        for d in documents
    ]

    qa_result = qa_engine.answer_multi_document_question(
        documents=docs_input,
        question=payload.question
    )
    answer, citations, has_evidence = qa_result
    answer_mode = getattr(qa_result, "answer_mode", "generative")
    model_used = getattr(qa_result, "model_used", None)

    consulted_filenames = list({c.get("filename", "") for c in citations if c.get("filename")})
    if not consulted_filenames:
        consulted_filenames = [d.filename for d in documents]

    # 5. Persist encrypted record in MultiDocQAHistory
    history_record = MultiDocQAHistory(
        user_id=current_user.id,
        document_ids=",".join(map(str, sorted(doc_ids))),
        question=payload.question,
        answer=answer,
        citations=json.dumps(citations),
        documents_consulted=json.dumps(consulted_filenames),
        created_at=datetime.utcnow()
    )
    db.add(history_record)
    db.commit()
    db.refresh(history_record)

    log_audit_event(
        db=db,
        event_type="MULTI_DOCUMENT_QA_SUCCESS",
        user_id=current_user.id,
        ip_address=ip,
        details=f"Multi-doc Q&A executed across {len(doc_ids)} documents. Mode: {answer_mode}."
    )

    parsed_citations = [
        MultiDocumentCitation(
            document_id=c.get("document_id") or doc_ids[0],
            filename=c.get("filename") or "Document",
            quote=c.get("quote", ""),
            page_number=c.get("page_number"),
            confidence=c.get("confidence", 1.0),
            relevance_score=c.get("relevance_score", c.get("confidence", 1.0)),
            evidence_type=c.get("evidence_type", "text")
        )
        for c in citations
    ]

    return MultiQAResponse(
        document_ids=doc_ids,
        question=payload.question,
        answer=answer,
        citations=parsed_citations,
        documents_consulted=consulted_filenames,
        has_sufficient_evidence=has_evidence,
        answer_mode=answer_mode,
        model_used=model_used,
        created_at=history_record.created_at
    )


@router.get(
    "/documents/multi-qa/history",
    response_model=MultiQAHistoryResponse,
    summary="Get multi-document Q&A history for the authenticated user"
)
def get_multi_document_qa_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    records = (
        db.query(MultiDocQAHistory)
        .filter(MultiDocQAHistory.user_id == current_user.id)
        .order_by(MultiDocQAHistory.created_at.desc())
        .limit(50)
        .all()
    )

    items = []
    for r in records:
        try:
            parsed_cits = json.loads(r.citations) if r.citations else []
        except Exception:
            parsed_cits = []
        try:
            parsed_docs = json.loads(r.documents_consulted) if r.documents_consulted else []
        except Exception:
            parsed_docs = []
        try:
            d_ids = [int(i.strip()) for i in r.document_ids.split(",") if i.strip().isdigit()]
        except Exception:
            d_ids = []

        items.append(
            MultiQAHistoryItem(
                id=r.id,
                document_ids=d_ids,
                question=r.question,
                answer=r.answer,
                citations=[
                    MultiDocumentCitation(
                        document_id=c.get("document_id", d_ids[0] if d_ids else 0),
                        filename=c.get("filename", "Document"),
                        quote=c.get("quote", ""),
                        page_number=c.get("page_number"),
                        confidence=c.get("confidence", 1.0),
                        relevance_score=c.get("relevance_score", 1.0),
                        evidence_type=c.get("evidence_type", "text")
                    )
                    for c in parsed_cits
                ],
                documents_consulted=parsed_docs,
                created_at=r.created_at
            )
        )

    return MultiQAHistoryResponse(
        count=len(items),
        history=items
    )
