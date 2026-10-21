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
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class QAResponse(BaseModel):
    document_id: int
    question: str
    answer: str
    citations: List[Citation] = []
    has_sufficient_evidence: bool = True
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
