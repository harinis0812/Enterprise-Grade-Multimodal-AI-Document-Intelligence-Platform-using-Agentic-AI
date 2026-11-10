import io
import json
import sqlite3
import uuid
from unittest.mock import MagicMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient

from backend.agents.document_agent import DocumentAgent
from backend.core.security import create_access_token, hash_password
from backend.database.database import SessionLocal
from backend.database.models import Document, QAHistory, User
from backend.main import app
from backend.services.llm_provider import (
    GeminiProvider,
    LLMResponse,
    get_llm_provider,
    set_llm_provider,
)
from backend.services.multimodal_service import (
    ExtractedTable,
    VisualElement,
    detect_tables_from_page,
    detect_visual_elements_from_page,
    extract_multimodal_image,
    extract_multimodal_pdf,
    format_table_to_markdown,
)
from backend.services.qa_service import (
    DocumentQAService,
    Passage,
    build_grounded_context,
    segment_document_into_passages,
)

client = TestClient(app)


def get_test_db():
    return SessionLocal()


def create_sample_pdf_with_table_and_chart() -> bytes:
    """Helper creating an in-memory PyMuPDF PDF with text, a vector table, and a chart."""
    doc = fitz.open()

    # Page 1: Text and Vector Table
    p1 = doc.new_page()
    p1.insert_text((50, 40), "Enterprise Financial Performance Q4 2026")
    p1.insert_text((50, 60), "The following table summarizes the financial metrics for FY25 and FY26.")

    # Insert table text
    p1.insert_text((55, 95), "Metric\t2025\t2026\nRevenue\t10 lakh\t15 lakh\nExpenses\t4 lakh\t6 lakh")
    # Draw table bounding boxes and cell gridlines so find_tables() identifies it
    p1.draw_rect(fitz.Rect(50, 80, 320, 150))
    p1.draw_line((50, 105), (320, 105))
    p1.draw_line((140, 80), (140, 150))
    p1.draw_line((230, 80), (230, 150))

    # Page 2: Vector Chart & Diagram
    p2 = doc.new_page()
    p2.insert_text((50, 40), "Architecture and Growth Trends")
    p2.insert_text((50, 60), "Figure 2.1: Revenue Growth Trajectory and System Architecture.")
    # Draw multiple vector lines and curves to simulate a chart
    for i in range(12):
        p2.draw_line((50 + i * 20, 200 - i * 8), (70 + i * 20, 190 - i * 8))
        p2.draw_rect(fitz.Rect(50 + i * 20, 220, 65 + i * 20, 250))
    p2.insert_text((50, 270), "Target: 20 lakh. Q1 Actual: 12 lakh, Q2 Actual: 15 lakh.")

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ============================================================================
# A. PDF, TABLE, AND OCR MULTIMODAL INGESTION TESTS
# ============================================================================

def test_multimodal_pdf_table_and_chart_extraction():
    """Verify that extract_multimodal_pdf detects vector tables and vector charts."""
    pdf_bytes = create_sample_pdf_with_table_and_chart()
    res = extract_multimodal_pdf(pdf_bytes)

    assert res.total_pages == 2
    assert len(res.tables) >= 1
    t = res.tables[0]
    assert t.page_number == 1
    assert t.col_count >= 2
    assert "Revenue" in t.markdown or "Revenue" in str(t.rows)

    assert len(res.visual_elements) >= 1
    p2_visuals = [ve for ve in res.visual_elements if ve.page_number == 2]
    assert len(p2_visuals) >= 1
    v = p2_visuals[0]
    assert v.page_number == 2
    assert v.drawing_count >= 8
    assert "Chart" in v.element_type or "Diagram" in v.element_type
    assert len(v.captions) >= 1
    assert "Figure 2.1" in v.captions[0]

    # Check unified text contains structured markers
    assert "--- Page 1 ---" in res.full_text
    assert "--- Page 2 ---" in res.full_text
    assert "[Table " in res.full_text
    assert "[Visual Element:" in res.full_text


def test_format_table_to_markdown_utility():
    """Verify that table formatting correctly converts rows and headers to Markdown."""
    headers = ["Metric", "2025", "2026"]
    rows = [
        ["Revenue", "10 lakh", "15 lakh"],
        ["Expenses", "4 lakh", "6 lakh"]
    ]
    md = format_table_to_markdown(headers, rows)
    assert "| Metric | 2025 | 2026 |" in md
    assert "| --- | --- | --- |" in md
    assert "| Revenue | 10 lakh | 15 lakh |" in md
    assert "| Expenses | 4 lakh | 6 lakh |" in md


def test_multimodal_scanned_pdf_triggers_ocr(monkeypatch):
    """Verify that a scanned PDF page with low extractable text invokes OCR cleanly."""
    doc = fitz.open()
    p = doc.new_page()
    # No text inserted; blank/scanned page
    p.draw_rect(fitz.Rect(50, 50, 200, 200))
    pdf_bytes = doc.write()
    doc.close()

    mock_ocr = MagicMock(return_value="Scanned Invoice Number 99882 Total $45,000")
    monkeypatch.setattr("backend.services.multimodal_service.extract_text_from_image", mock_ocr)

    res = extract_multimodal_pdf(pdf_bytes)
    assert res.total_pages == 1
    assert 1 in res.ocr_pages
    assert "Scanned Invoice Number 99882" in res.full_text
    assert mock_ocr.call_count >= 1


def test_multimodal_image_extraction(monkeypatch):
    """Verify image documents (.png, .jpg) are extracted via OCR and tagged as OCR evidence."""
    mock_ocr = MagicMock(return_value="| Header A | Header B |\n| Val 1 | Val 2 |")
    monkeypatch.setattr("backend.services.multimodal_service.extract_text_from_image", mock_ocr)

    res = extract_multimodal_image("dummy_image.png")
    assert res.total_pages == 1
    assert "ocr" in res.page_evidence_map[1]
    assert "Header A" in res.full_text
    assert "[Image Document via OCR]" in res.full_text


# ============================================================================
# B. GEMINI MULTIMODAL VISION TESTS
# ============================================================================

def test_gemini_provider_multimodal_payload_generation():
    """Verify that GeminiProvider generates correct inlineData payload for multimodal requests."""
    provider = GeminiProvider(api_key="AIzaSyMockKeyForMultimodal")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {"parts": [{"text": "The diagram illustrates a multi-tier microservices architecture."}]}
        }],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20}
    }

    dummy_image = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
        analysis = provider.analyze_visual_element(
            image_bytes=dummy_image,
            mime_type="image/png",
            prompt="Analyze this diagram."
        )

        assert analysis is not None
        assert "microservices architecture" in analysis
        call_kwargs = mock_post.call_args.kwargs
        sent_payload = call_kwargs["json"]
        parts = sent_payload["contents"][0]["parts"]
        assert len(parts) == 2
        assert parts[0]["text"] == "Analyze this diagram."
        assert "inlineData" in parts[1]
        assert parts[1]["inlineData"]["mimeType"] == "image/png"


def test_gemini_provider_unconfigured_safely_skips_visual_call():
    """Verify that if Gemini is unconfigured, analyze_visual_element returns None safely."""
    provider = GeminiProvider(api_key=None)
    assert provider.is_configured is False
    res = provider.analyze_visual_element(b"dummy")
    assert res is None


# ============================================================================
# C. HYBRID RETRIEVAL & EVIDENCE TYPE TESTS
# ============================================================================

def test_segment_document_into_passages_preserves_multimodal_types():
    """Verify that segment_document_into_passages tags tables, charts, and text with distinct evidence types."""
    doc_text = (
        "--- Page 1 ---\n"
        "Executive Summary: Company growth remained strong in fiscal year 2026.\n\n"
        "[Table 1 | Page 1]\n"
        "| Metric | 2025 | 2026 |\n"
        "|---|---|---|\n"
        "| Revenue | 10 lakh | 15 lakh |\n\n"
        "--- Page 2 ---\n"
        "[Visual Element: Chart/Diagram | Page 2]\n"
        "Caption: Figure 2.1: Revenue Growth Trajectory\n"
        "Extracted Labels: Q1 10 lakh, Q2 12 lakh, Q3 15 lakh\n\n"
        "--- Page 3 ---\n"
        "[Scanned Content via OCR]\n"
        "The signed contract terms have been formally notarized.\n"
    )

    passages = segment_document_into_passages(doc_text)
    assert len(passages) >= 4

    types_found = {p.evidence_type for p in passages}
    assert "text" in types_found
    assert "table" in types_found
    assert "chart" in types_found
    assert "ocr" in types_found

    # Check table passage preservation
    table_p = [p for p in passages if p.evidence_type == "table"][0]
    assert table_p.page_number == 1
    assert "| Revenue | 10 lakh | 15 lakh |" in table_p.text


def test_hybrid_retrieval_prioritizes_table_query():
    """Verify that a table-oriented query boosts table passages in hybrid retrieval."""
    doc_text = (
        "--- Page 1 ---\n"
        "Overview of operations and regional marketing initiatives.\n\n"
        "--- Page 4 ---\n"
        "[Table 1 | Page 4]\n"
        "| Category | Q1 Charges | Q2 Charges |\n"
        "| Hardware | $45,000 | $60,000 |\n"
        "| Cloud | $12,000 | $18,000 |\n\n"
        "--- Page 9 ---\n"
        "General discussion on cloud infrastructure and hardware lifecycles.\n"
    )

    qa = DocumentQAService()
    scored = qa.retrieve_passages(doc_text, "Compare the charges in the table on page 4")

    assert len(scored) >= 1
    top_p = scored[0].passage
    assert top_p.evidence_type == "table"
    assert top_p.page_number == 4
    assert "$45,000" in top_p.text


def test_hybrid_retrieval_prioritizes_chart_query():
    """Verify that a visual/chart query boosts chart passages in hybrid retrieval."""
    doc_text = (
        "--- Page 2 ---\n"
        "Standard paragraphs regarding operational performance.\n\n"
        "--- Page 5 ---\n"
        "[Visual Element: Chart/Diagram | Page 5]\n"
        "Caption: Figure 5.1: Customer Adoption Growth Trend\n"
        "Extracted Labels: Jan 5k, Feb 8k, Mar 14k\n"
    )

    qa = DocumentQAService()
    scored = qa.retrieve_passages(doc_text, "What growth trend does the chart on page 5 show?")

    assert len(scored) >= 1
    top_p = scored[0].passage
    assert top_p.evidence_type == "chart"
    assert top_p.page_number == 5
    assert "Figure 5.1" in top_p.text


def test_grounded_context_includes_evidence_type():
    """Verify build_grounded_context includes Type annotation in XML context."""
    p = Passage(
        passage_id=1,
        text="| Col1 | Col2 |\n| Val1 | Val2 |",
        page_number=3,
        evidence_type="table"
    )
    scored = [MagicMock(passage=p, score=0.92)]

    ctx = build_grounded_context(scored, document_id=10, filename="report.pdf")
    assert '<document_context document_id="10" filename="report.pdf">' in ctx
    assert "[Passage 1 | Page 3 | Type: table | Retrieval Relevance: 92%]" in ctx
    assert "</document_context>" in ctx


# ============================================================================
# D. MULTIMODAL QUESTION ANSWERING & CITATION TESTS
# ============================================================================

def test_multimodal_qa_table_fallback():
    """Verify that table queries in fallback mode return structured table evidence and citations."""
    set_llm_provider(None)  # Force honest fallback mode

    doc_text = (
        "--- Page 3 ---\n"
        "Quarterly Procurement Ledger.\n\n"
        "[Table 1 | Page 3]\n"
        "| Department | Budget | Actual |\n"
        "| Engineering | $100k | $95k |\n"
        "| Marketing | $50k | $48k |\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "Explain the table on page 3")

    assert res.has_sufficient_evidence is True
    assert res.answer_mode == "retrieval_fallback"
    assert "According to the table in the document (Page 3)" in res.answer
    assert "| Engineering | $100k | $95k |" in res.answer
    assert len(res.citations) >= 1
    assert res.citations[0]["page_number"] == 3
    assert res.citations[0]["evidence_type"] == "table"


def test_multimodal_qa_generative_synthesis_with_mocked_gemini():
    """Verify that multimodal Q&A calls Gemini and returns citations with evidence_type."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.is_configured = True
    mock_provider.model = "gemini-1.5-flash"
    mock_provider.generate.return_value = LLMResponse(
        text=(
            "### 1. Revenue and Expense Breakdown\n"
            "According to the table on Page 1, the metrics for FY25 and FY26 are:\n\n"
            "- **Revenue**: 10 lakh in 2025, increasing to 15 lakh in 2026.\n"
            "- **Expenses**: 4 lakh in 2025, increasing to 6 lakh in 2026.\n\n"
            "### 2. Profit Margin Analysis\n"
            "Net operating profit grew from 6 lakh to 9 lakh across the two fiscal periods."
        ),
        model="gemini-1.5-flash",
        provider="Google Gemini",
        is_generated=True
    )
    set_llm_provider(mock_provider)

    doc_text = (
        "--- Page 1 ---\n"
        "[Table 1 | Page 1]\n"
        "| Metric | 2025 | 2026 |\n"
        "| Revenue | 10 lakh | 15 lakh |\n"
        "| Expenses | 4 lakh | 6 lakh |\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "What was the revenue and expense for 2025 and 2026?", document_id=1, filename="fin.pdf")

    assert res.has_sufficient_evidence is True
    assert res.answer_mode == "generative"
    assert res.model_used == "gemini-1.5-flash"
    assert "### 1. Revenue and Expense Breakdown" in res.answer
    assert len(res.citations) >= 1
    assert res.citations[0]["page_number"] == 1
    assert res.citations[0]["evidence_type"] == "table"


def test_multimodal_qa_chart_fallback():
    """Verify that chart queries in fallback mode return visual labels and chart evidence."""
    set_llm_provider(None)

    doc_text = (
        "--- Page 2 ---\n"
        "[Visual Element: Chart/Diagram | Page 2]\n"
        "Caption: Figure 2.1: Quarterly Growth Trajectory\n"
        "Extracted Labels: Q1 10 lakh, Q2 12 lakh, Q3 15 lakh\n"
    )

    qa = DocumentQAService()
    res = qa.answer_question(doc_text, "What trend does the chart show on page 2?")

    assert res.has_sufficient_evidence is True
    assert "According to the visual element in the document (Page 2)" in res.answer
    assert "Figure 2.1" in res.answer
    assert res.citations[0]["evidence_type"] == "chart"


# ============================================================================
# E. LANGGRAPH WORKFLOW MULTIMODAL INTEGRATION
# ============================================================================

def test_agent_workflow_processes_multimodal_document():
    """Verify that DocumentAgent workflow processes multimodal text and populates insights."""
    doc_text = (
        "--- Page 1 ---\n"
        "Financial Report for Acme Corp.\n\n"
        "[Table 1 | Page 1]\n"
        "| Item | Amount |\n"
        "| Cloud Hosting | $20,000 |\n\n"
        "[Visual Element: Chart/Diagram | Page 1]\n"
        "Caption: Figure 1: Cost Trend\n"
    )

    agent = DocumentAgent()
    result = agent.process("financial_report.pdf", doc_text)

    assert result["status"] in ["verification_passed", "analysis_completed", "document_received", "verified"]
    assert "document_information" in result
    info = result["document_information"]
    assert info.get("has_tables") is True
    assert info.get("has_charts") is True

    analysis = result.get("analysis", {})
    insights = analysis.get("multimodal_insights", {})
    assert insights.get("tabular_data_present") is True
    assert insights.get("visual_elements_present") is True


# ============================================================================
# F. SECURITY & MULTI-TENANT ISOLATION REGRESSION
# ============================================================================

def test_multimodal_upload_and_encrypted_at_rest_storage():
    """Verify that multimodal metadata and extracted text are encrypted at rest in docuai.db."""
    db = get_test_db()
    unique_email = f"user_p4_{uuid.uuid4().hex[:6]}@enterprise.com"
    user = User(
        email=unique_email,
        hashed_password=hash_password("PassWord123!"),
        role="user",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email, "role": "user"})

    # Prepare in-memory PDF
    pdf_bytes = create_sample_pdf_with_table_and_chart()

    response = client.post(
        "/upload",
        files={"file": ("test_multimodal.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    res_data = response.json()
    doc_id = res_data.get("id") or res_data.get("document_id")

    # Verify that raw database storage is encrypted at rest
    conn = sqlite3.connect("docuai.db")
    c = conn.cursor()
    c.execute("SELECT extracted_text, analysis FROM documents WHERE id = ?", (doc_id,))
    raw_extracted, raw_analysis = c.fetchone()
    conn.close()

    # Raw database must store Fernet ciphertext (starts with gAAAAA)
    assert raw_extracted.startswith("gAAAAA")
    assert raw_analysis.startswith("gAAAAA")
    assert "Revenue" not in raw_extracted  # Plaintext must not be exposed in raw DB

    # Verify that querying through ORM transparently decrypts
    doc_orm = db.query(Document).filter(Document.id == doc_id).first()
    assert doc_orm is not None
    assert "Revenue" in doc_orm.extracted_text
    parsed_meta = json.loads(doc_orm.analysis).get("multimodal_metadata", {})
    assert parsed_meta.get("tables_detected", 0) >= 1
    assert parsed_meta.get("charts_detected", 0) >= 1

    # Cleanup test user
    db.delete(doc_orm)
    db.delete(user)
    db.commit()
    db.close()
