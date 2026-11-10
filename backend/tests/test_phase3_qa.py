import json
import sqlite3
import uuid
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.core.config import settings
from backend.core.encryption import is_encrypted
from backend.core.security import create_access_token, hash_password
from backend.database.database import SessionLocal
from backend.database.models import Document, QAHistory, User
from backend.main import app
from backend.services.llm_provider import (
    GeminiProvider,
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    get_llm_provider,
    set_llm_provider,
)
from backend.services.qa_service import (
    DocumentQAService,
    build_grounded_context,
    segment_document_into_passages,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_default_llm_provider():
    """Ensure LLM provider state is cleanly restored after each test."""
    yield
    set_llm_provider(None)


def get_test_db():
    return SessionLocal()


# ============================================================================
# A. GENERATIVE MODEL INTEGRATION TESTS
# ============================================================================

def test_gemini_provider_is_configured_check():
    """Verify provider accurately detects presence and absence of GEMINI_API_KEY."""
    provider_unconfigured = GeminiProvider(api_key="")
    assert provider_unconfigured.is_configured is False

    provider_placeholder = GeminiProvider(api_key="your-gemini-api-key-here")
    assert provider_placeholder.is_configured is False

    provider_configured = GeminiProvider(api_key="AIzaSyValidDummyKey123456789")
    assert provider_configured.is_configured is True


def test_gemini_provider_generate_invokes_api_endpoint():
    """Verify provider constructs the correct official REST URL, headers, and payload."""
    provider = GeminiProvider(
        api_key="AIzaSyTestKeyForMocking",
        model="gemini-1.5-flash",
        max_retries=1
    )

    mock_json_response = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "### 1. Overview\nDocument grounded explanation."}]
                }
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 120,
            "candidatesTokenCount": 45
        }
    }

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_json_response
        )

        res = provider.generate(
            prompt="Explain the document",
            system_instruction="You are a helpful assistant."
        )

        assert res.is_generated is True
        assert "### 1. Overview" in res.text
        assert res.model == "gemini-1.5-flash"
        assert res.provider == "Google Gemini"

        # Verify endpoint and header structure
        args, kwargs = mock_post.call_args
        assert "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent" in args[0]
        assert kwargs["headers"]["x-goog-api-key"] == "AIzaSyTestKeyForMocking"
        assert kwargs["json"]["contents"][0]["parts"][0]["text"] == "Explain the document"
        assert "systemInstruction" in kwargs["json"]


def test_gemini_provider_handles_rate_limit_and_retries():
    """Verify provider retries on HTTP 429 and raises LLMRateLimitError when exhausted."""
    provider = GeminiProvider(
        api_key="AIzaSyTestKey",
        model="gemini-1.5-flash",
        max_retries=2
    )

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=429,
            text="Resource has been exhausted"
        )

        with pytest.raises(LLMRateLimitError):
            provider.generate("Test prompt")
        assert mock_post.call_count == 2


def test_gemini_provider_handles_auth_failure_safely():
    """Verify provider handles HTTP 401/403 without leaking secret keys."""
    provider = GeminiProvider(
        api_key="AIzaSyInvalidKey",
        max_retries=1
    )

    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=401, text="API_KEY_INVALID")

        with pytest.raises(LLAuth_Err := LLMAuthError) as exc_info:
            provider.generate("Test prompt")
        # Ensure secret key is NEVER printed in error message
        assert "AIzaSyInvalidKey" not in str(exc_info.value)
        assert "verify your GEMINI_API_KEY" in str(exc_info.value)


def test_qa_service_honest_fallback_when_unconfigured():
    """Verify when GEMINI_API_KEY is not configured, service reports retrieval_fallback mode."""
    # Ensure unconfigured provider
    set_llm_provider(GeminiProvider(api_key=""))

    doc_text = (
        "--- Page 1 ---\n"
        "Enterprise Architecture Document.\n"
        "The distributed ledger processes 50,000 transactions per second.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "How many transactions per second are processed?")

    assert result.has_sufficient_evidence is True
    assert result.answer_mode == "retrieval_fallback"
    assert result.model_used is None
    assert "50,000" in result.answer or "50,000" in result.citations[0]["quote"]


# ============================================================================
# B. DOCUMENT RETRIEVAL & OVERLAPPING CHUNKS TESTS
# ============================================================================

def test_document_segmentation_with_overlapping_chunks():
    """Verify document chunking creates overlapping passages while respecting page boundaries."""
    page_text = (
        "--- Page 1 ---\n"
        "Sentence one describes the enterprise platform architecture. "
        "Sentence two details the data processing layer and pipeline components. "
        "Sentence three highlights the agentic reasoning and LangGraph verification. "
        "Sentence four outlines the security protocols and access controls. "
        "Sentence five provides the performance benchmarks and latency targets.\n\n"
        "--- Page 2 ---\n"
        "Page two starts with deployment configurations and Kubernetes manifests. "
        "Page two continues with cloud infrastructure topology and observability.\n"
    )

    passages = segment_document_into_passages(page_text, chunk_size=150, overlap=40)
    assert len(passages) >= 2

    # Verify no page blending: every passage from Page 1 must have page_number == 1
    p1_passages = [p for p in passages if p.page_number == 1]
    p2_passages = [p for p in passages if p.page_number == 2]

    assert len(p1_passages) >= 1
    assert len(p2_passages) >= 1
    assert all("Page two" not in p.text for p in p1_passages)
    assert all("architecture" not in p.text for p in p2_passages)


def test_multi_passage_top_k_retrieval_and_relevance():
    """Verify retrieve_passages retrieves multiple relevant passages ranked by relevance."""
    doc_text = (
        "--- Page 1 ---\n"
        "Natural language processing allows autonomous agents to understand documents.\n"
        "Tokenization divides raw text into smaller meaningful tokens for processing.\n\n"
        "--- Page 2 ---\n"
        "Vector embeddings transform textual tokens into dense high-dimensional vectors.\n"
        "Cosines similarity measures semantic relatedness between vector embeddings.\n\n"
        "--- Page 3 ---\n"
        "Transformer architectures utilize self-attention mechanisms to weigh contextual relationships.\n"
        "Unrelated topic: employee vacation policy details.\n"
    )

    qa = DocumentQAService()
    scored = qa.retrieve_passages(doc_text, "Explain tokenization and vector embeddings", top_k=3)

    assert len(scored) >= 2
    # The top retrieved passages must have positive relevance scores
    assert scored[0].score > 0.20
    pages_retrieved = {sp.passage.page_number for sp in scored}
    # Pages 1 and 2 discuss tokenization and embeddings
    assert 1 in pages_retrieved or 2 in pages_retrieved


def test_retrieval_filters_unrelated_content():
    """Verify completely unrelated queries do not match irrelevant passages."""
    doc_text = (
        "--- Page 1 ---\n"
        "Medical journal regarding cardiovascular surgical procedures and outcomes.\n"
    )
    qa = DocumentQAService()
    scored = qa.retrieve_passages(doc_text, "How do I build a wooden dining table?")
    assert len(scored) == 0


# ============================================================================
# C. GROUNDED ANSWER GENERATION TESTS (WITH MOCKED MODEL)
# ============================================================================

def test_grounded_generative_synthesis_with_mocked_llm():
    """Verify DocumentQAService formats context and returns structured generative answer."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.is_configured = True
    mock_provider.model = "gemini-1.5-flash"

    mock_answer = (
        "### 1. Tokenization\n"
        "Tokenization is the process of breaking down text into discrete token units.\n\n"
        "### 2. Vector Embeddings\n"
        "Embeddings represent words as numerical vectors in a semantic space.\n\n"
        "- Preserves semantic distances\n"
        "- Facilitates multi-dimensional cosine similarity"
    )

    mock_provider.generate.return_value = LLMResponse(
        text=mock_answer,
        model="gemini-1.5-flash",
        provider="Google Gemini",
        is_generated=True
    )
    set_llm_provider(mock_provider)

    doc_text = (
        "--- Page 1 ---\n"
        "NLP Fundamentals: Tokenization breaks text into atomic words or subwords.\n"
        "Embeddings map tokens into vectors for mathematical similarity comparison.\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(
        document_text=doc_text,
        question="Explain tokenization and embeddings",
        document_id=42,
        filename="nlp_guide.pdf"
    )

    assert res.has_sufficient_evidence is True
    assert res.answer_mode == "generative"
    assert res.model_used == "gemini-1.5-flash"
    assert "### 1. Tokenization" in res.answer
    assert "### 2. Vector Embeddings" in res.answer
    assert len(res.citations) >= 1
    assert res.citations[0]["page_number"] == 1

    # Verify context block passed to LLM was properly formatted
    prompt_arg = mock_provider.generate.call_args.kwargs["prompt"]
    assert '<document_context document_id="42" filename="nlp_guide.pdf">' in prompt_arg
    assert "[Passage 1 | Page 1" in prompt_arg


def test_insufficient_evidence_abstains_without_calling_llm():
    """Verify that when evidence is insufficient, the system abstains without calling the LLM."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.is_configured = True
    set_llm_provider(mock_provider)

    doc_text = (
        "--- Page 1 ---\n"
        "Standard invoice with order numbers and billing details.\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "What is the chemical composition of basalt rocks?")

    assert res.has_sufficient_evidence is False
    assert "not contain enough evidence" in res.answer.lower()
    # LLM must NOT be called when retrieval determines evidence is absent
    assert mock_provider.generate.call_count == 0


# ============================================================================
# D. CITATION ACCURACY & METADATA TESTS
# ============================================================================

def test_citations_reflect_actual_document_passages_and_pages():
    """Verify citation quotes and page numbers match authentic document text."""
    doc_text = (
        "--- Page 4 ---\n"
        "Section 4.1: The primary data center is located in Frankfurt, Germany.\n\n"
        "--- Page 9 ---\n"
        "Section 9.2: The secondary disaster recovery site is situated in Tokyo, Japan.\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "Where is the secondary disaster recovery site?")

    assert res.has_sufficient_evidence is True
    assert len(res.citations) >= 1
    top_citation = res.citations[0]

    assert top_citation["page_number"] == 9
    assert "Tokyo" in top_citation["quote"]
    assert top_citation["confidence"] > 0.3


def test_multipart_question_retrieves_multi_page_evidence():
    """Verify multi-part questions retrieve evidence and citations across multiple pages."""
    doc_text = (
        "--- Page 2 ---\n"
        "Financial Performance: Total revenue reached $150 million.\n\n"
        "--- Page 8 ---\n"
        "Corporate Leadership: The Chief Executive Officer is Dr. Robert Vance.\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "What was the total revenue and who is the CEO?")

    assert res.has_sufficient_evidence is True
    assert len(res.citations) >= 2
    pages = {c["page_number"] for c in res.citations}
    assert 2 in pages
    assert 8 in pages


# ============================================================================
# E. SECURITY & MULTI-TENANT REGRESSION TESTS
# ============================================================================

def test_qa_history_stored_encrypted_at_rest():
    """Verify Q&A questions and generated answers are stored encrypted in docuai.db."""
    db = get_test_db()
    user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()
    assert user is not None

    doc = db.query(Document).filter(Document.user_id == user.id).first()
    assert doc is not None

    unique_q = f"Confidential Security Inquiry {uuid.uuid4().hex[:6]}"
    unique_a = f"### 1. Certified Protocol\nConfidential Answer Detail {uuid.uuid4().hex[:6]}"

    qa_record = QAHistory(
        document_id=doc.id,
        user_id=user.id,
        question=unique_q,
        answer=unique_a
    )
    db.add(qa_record)
    db.commit()
    record_id = qa_record.id
    db.close()

    # Query raw database directly via sqlite3
    conn = sqlite3.connect("docuai.db")
    c = conn.cursor()
    c.execute("SELECT question, answer FROM qa_history WHERE id = ?", (record_id,))
    raw_q, raw_a = c.fetchone()
    conn.close()

    # Raw database must store Fernet ciphertext (starts with gAAAAA)
    assert raw_q.startswith("gAAAAA")
    assert raw_a.startswith("gAAAAA")
    assert unique_q not in raw_q
    assert unique_a not in raw_a


def test_cross_user_qa_access_strictly_denied():
    """Verify User B cannot query or read Q&A history for User A's document."""
    db = get_test_db()

    # Create User A
    user_a = User(
        email=f"usera_p3_{uuid.uuid4().hex[:6]}@enterprise.com",
        hashed_password=hash_password("PassA123!"),
        role="user",
        is_active=True
    )
    # Create User B
    user_b = User(
        email=f"userb_p3_{uuid.uuid4().hex[:6]}@enterprise.com",
        hashed_password=hash_password("PassB123!"),
        role="user",
        is_active=True
    )
    db.add(user_a)
    db.add(user_b)
    db.commit()
    db.refresh(user_a)
    db.refresh(user_b)

    # User A owns a document
    doc_a = Document(
        filename="user_a_private.txt",
        document_type="Strategy",
        status="completed",
        extracted_text="Confidential Strategy of User A.",
        user_id=user_a.id
    )
    db.add(doc_a)
    db.commit()
    db.refresh(doc_a)

    token_b = create_access_token(data={"sub": str(user_b.id), "email": user_b.email, "role": "user"})
    db.close()

    # User B attempts to query User A's document -> 403 Forbidden
    res_qa_denied = client.post(
        f"/documents/{doc_a.id}/qa",
        json={"question": "What is the strategy?"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_qa_denied.status_code == 403
    assert "Access denied" in res_qa_denied.json()["detail"]

    # User B attempts to view User A's Q&A history -> 403 Forbidden
    res_hist_denied = client.get(
        f"/documents/{doc_a.id}/qa/history",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert res_hist_denied.status_code == 403
    assert "Access denied" in res_hist_denied.json()["detail"]
