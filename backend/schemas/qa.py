from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class QARequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Question about the document")

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or whitespace only.")
        if len(cleaned) > 1000:
            raise ValueError("Question is too long (maximum 1000 characters).")
        return cleaned


class Citation(BaseModel):
    quote: str
    page_number: Optional[int] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Retrieval relevance score")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Explicit retrieval relevance")
    evidence_type: Optional[str] = Field("text", description="Evidence type: 'text', 'table', 'chart', or 'ocr'")


class QAResponse(BaseModel):
    document_id: int
    question: str
    answer: str
    citations: List[Citation] = []
    has_sufficient_evidence: bool = True
    answer_mode: str = Field(default="generative", description="'generative' (LLM) or 'retrieval_fallback'")
    model_used: Optional[str] = None
    retrieval_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime


class QAHistoryItem(BaseModel):
    id: int
    document_id: int
    question: str
    answer: str
    citations: List[Citation] = []
    created_at: datetime


class QAHistoryResponse(BaseModel):
    document_id: int
    count: int
    history: List[QAHistoryItem] = []


class MultiQARequest(BaseModel):
    document_ids: List[int] = Field(..., min_length=1, max_length=10, description="List of document IDs to query across")
    question: str = Field(..., min_length=1, max_length=1000, description="Question across the documents")

    @field_validator("document_ids")
    @classmethod
    def validate_document_ids(cls, ids: List[int]) -> List[int]:
        if not ids:
            raise ValueError("At least one document ID must be specified.")
        unique_ids = list(dict.fromkeys(ids))
        if len(unique_ids) > 10:
            raise ValueError("A maximum of 10 documents can be queried simultaneously.")
        return unique_ids

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or whitespace only.")
        if len(cleaned) > 1000:
            raise ValueError("Question is too long (maximum 1000 characters).")
        return cleaned


class MultiDocumentCitation(BaseModel):
    document_id: int
    filename: str
    quote: str
    page_number: Optional[int] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Retrieval relevance score")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    evidence_type: Optional[str] = Field("text", description="Evidence type: 'text', 'table', 'chart', or 'ocr'")


class MultiQAResponse(BaseModel):
    document_ids: List[int]
    question: str
    answer: str
    citations: List[MultiDocumentCitation] = []
    documents_consulted: List[str] = []
    has_sufficient_evidence: bool = True
    answer_mode: str = Field(default="generative", description="'generative' (LLM) or 'retrieval_fallback'")
    model_used: Optional[str] = None
    created_at: datetime


class MultiQAHistoryItem(BaseModel):
    id: int
    document_ids: List[int]
    question: str
    answer: str
    citations: List[MultiDocumentCitation] = []
    documents_consulted: List[str] = []
    created_at: datetime


class MultiQAHistoryResponse(BaseModel):
    count: int
    history: List[MultiQAHistoryItem] = []
