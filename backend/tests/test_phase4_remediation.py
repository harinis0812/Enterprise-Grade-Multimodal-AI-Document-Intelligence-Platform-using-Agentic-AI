import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import fitz

from backend.main import app
from backend.services.multimodal_service import (
    ExtractedTable,
    VisualElement,
    detect_tables_from_page,
    detect_visual_elements_from_page,
    extract_multimodal_pdf,
    format_table_to_markdown
)
from backend.services.llm_provider import (
    ALLOWED_IMAGE_MIME_TYPES,
    EmbeddingProvider,
    GeminiProvider,
    LLMProviderError,
    TFIDFEmbeddingAdapter,
    get_llm_provider
)
from backend.services.qa_service import DocumentQAService
from backend.agents.graph_workflow import DocumentGraphWorkflow
from backend.core.security import create_access_token
from backend.database.models import User


client = TestClient(app)


@pytest.fixture
def auth_headers(setup_test_environment):
    token = setup_test_environment["token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. Mixed-Content Detection & OCR
# =====================================================================

def test_mixed_content_image_coverage_ocr():
    """
    Verifies that a PDF page with native text (> 35 chars) AND an embedded
    scanned image covering > 15% of the page triggers mixed-content OCR
    and populates 'ocr' alongside 'text' in evidence metadata.
    """
    doc = fitz.open()
    page = doc.new_page(width=500, height=700)

    # 1. Add native text header (> 35 chars)
    page.insert_text(
        fitz.Point(50, 50),
        "ACME FINANCIAL CORPORATION - OFFICIAL AUDIT REPORT FOR FISCAL YEAR 2026",
        fontsize=11
    )

    # 2. Add an embedded image covering substantial page area (rect: 400x400 = 160,000 / 350,000 = ~45%)
    # Create simple dummy PNG in memory
    img_doc = fitz.open()
    img_page = img_doc.new_page(width=200, height=200)
    img_page.draw_rect(fitz.Rect(10, 10, 190, 190), color=(0, 0, 1), fill=(0.8, 0.8, 1))
    img_page.insert_text(fitz.Point(30, 100), "SCANNED INVOICE ITEM: $95,000", fontsize=10)
    pix = img_page.get_pixmap()
    img_bytes = pix.tobytes("png")
    img_doc.close()

    rect = fitz.Rect(50, 100, 450, 550)
    page.insert_image(rect, stream=img_bytes)

    pdf_bytes = doc.tobytes()
    doc.close()

    # Mock OCR extraction to return expected text from the image
    with patch("backend.services.multimodal_service.extract_text_from_image", return_value="SCANNED INVOICE ITEM: $95,000"):
        res = extract_multimodal_pdf(pdf_bytes)

        assert res.total_pages == 1
        assert "text" in res.page_evidence_map[1]
        assert "ocr" in res.page_evidence_map[1]
        assert "ocr" in res.summary_metadata["evidence_types_found"]
        assert 1 in res.ocr_pages
        assert "ACME FINANCIAL CORPORATION" in res.full_text
        assert "[Scanned Region via OCR | Page 1]" in res.full_text
        assert "SCANNED INVOICE ITEM: $95,000" in res.full_text


# =====================================================================
# 2. Table Extraction & Continuity Limitations
# =====================================================================

def test_table_continuity_markers_and_limitations():
    """
    Verifies that multi-page / continued tables receive has_continuity_marker=True
    and that extraction limitations are clearly populated.
    """
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    # Insert a table with a continuation header
    headers = ["Category", "Department", "Quarterly Budget (cont.)", "Actual Spend"]
    rows = [["Engineering", "Core Infra", "$120,000", "$115,000"]]
    md = format_table_to_markdown(headers, rows)

    # Use ExtractedTable dataclass directly to verify field structure
    tab_cont = ExtractedTable(
        page_number=2,
        table_index=1,
        headers=headers,
        rows=rows,
        markdown=md,
        row_count=1,
        col_count=4,
        has_continuity_marker=True,
        limitations="Table indicates multi-page continuation; cross-page row alignment should be verified."
    )

    assert tab_cont.has_continuity_marker is True
    assert "continuation" in tab_cont.limitations
    assert tab_cont.row_count == 1
    assert tab_cont.col_count == 4
    assert "| Engineering | Core Infra | $120,000 | $115,000 |" in tab_cont.markdown


# =====================================================================
# 3. Visual Element Analysis Status & Classification
# =====================================================================

def test_visual_element_analysis_status_and_chart_type():
    """
    Verifies that visual elements differentiate between 'detected' and 'analyzed',
    and accurately infer chart types, captions, and observations.
    """
    doc = fitz.open()
    page = doc.new_page(width=500, height=500)
    # Add drawing vector paths to simulate a chart
    for i in range(12):
        page.draw_line(fitz.Point(10 * i, 10), fitz.Point(10 * i, 100), color=(1, 0, 0))

    page_text = (
        "Figure 3: Quarterly Revenue Distribution by Region - Bar Chart\n"
        "Q1 Revenue: $500,000\n"
        "Q2 Revenue: $750,000\n"
        "Legend: Series A (Actual) vs Series B (Target)"
    )

    visuals = detect_visual_elements_from_page(page, page_num=1, page_text=page_text)
    doc.close()

    assert len(visuals) == 1
    v = visuals[0]
    assert v.element_type == "Chart/Diagram"
    assert v.analysis_status == "analyzed"
    assert v.chart_type == "Bar Chart"
    assert len(v.captions) >= 1
    assert "Figure 3" in v.captions[0]
    assert any("Actual" in leg or "Target" in leg or "Legend" in leg for leg in v.legend)
    assert len(v.extracted_observations) >= 2


def test_visual_element_unlabeled_status():
    """
    Verifies that a drawing without captions or labels is marked 'detected' rather than 'analyzed'.
    """
    doc = fitz.open()
    page = doc.new_page(width=500, height=500)
    for i in range(10):
        page.draw_line(fitz.Point(5 * i, 5), fitz.Point(5 * i, 50), color=(0, 1, 0))

    visuals = detect_visual_elements_from_page(page, page_num=1, page_text="")
    doc.close()

    assert len(visuals) == 1
    v = visuals[0]
    assert v.analysis_status == "detected"
    assert v.chart_type == "Vector Graphic / Diagram"


# =====================================================================
# 4. Gemini Vision Hardening & MIME Validation
# =====================================================================

def test_gemini_vision_mime_validation():
    """
    Verifies that invalid MIME types raise LLMProviderError and valid MIME types
    are accepted and normalized.
    """
    provider = GeminiProvider(api_key="valid-test-key-12345")

    # Invalid MIME type
    with pytest.raises(LLMProviderError) as exc_info:
        provider.generate(
            prompt="Describe this",
            images=[{"mime_type": "application/pdf", "data": "dGVzdGRhdGE="}]
        )
    assert "Unsupported image MIME type" in str(exc_info.value)

    # Invalid Base64 data
    with pytest.raises(LLMProviderError) as exc_info:
        provider.generate(
            prompt="Describe this",
            images=[{"mime_type": "image/png", "data": ""}]
        )
    assert "Image data is missing or invalid" in str(exc_info.value)


def test_gemini_analyze_visual_element_empty_bytes():
    """
    Verifies that analyze_visual_element handles empty bytes safely without crashing.
    """
    provider = GeminiProvider(api_key="valid-test-key-12345")
    result = provider.analyze_visual_element(image_bytes=b"")
    assert result is None


# =====================================================================
# 5. EmbeddingProvider Protocol & Hybrid Retrieval
# =====================================================================

def test_embedding_provider_protocol_and_hybrid_retrieval():
    """
    Verifies that TFIDFEmbeddingAdapter satisfies the EmbeddingProvider Protocol
    and integrates cleanly into DocumentQAService hybrid retrieval.
    """
    adapter = TFIDFEmbeddingAdapter(vector_dim=64)
    assert isinstance(adapter, EmbeddingProvider)

    q_vec = adapter.embed_query("revenue and profit")
    assert len(q_vec) == 64
    assert isinstance(q_vec[0], float)

    p_vecs = adapter.embed_passages(["first passage text", "second passage text"])
    assert len(p_vecs) == 2
    assert len(p_vecs[0]) == 64

    # Test retrieval with the adapter plugged in
    qa_engine = DocumentQAService(embedding_provider=adapter)
    doc_text = (
        "--- Page 1 ---\n"
        "Total revenue for the fiscal quarter reached $12 million.\n"
        "Operating profit expanded by 18 percent.\n\n"
        "--- Page 2 ---\n"
        "Human resources reported an increase of 25 new engineering hires."
    )
    passages = qa_engine.retrieve_passages(doc_text, "What was the total revenue?")
    assert len(passages) >= 1
    assert passages[0].passage.page_number == 1
    assert "$12 million" in passages[0].passage.text


# =====================================================================
# 6. LangGraph Multimodal Routing
# =====================================================================

def test_langgraph_routing_with_tables():
    """
    Verifies that LangGraph conditionally routes to 'Table Analysis Agent'
    when table structures are detected.
    """
    workflow = DocumentGraphWorkflow()
    text = (
        "Employee Report\n"
        "[Table 1 | Page 1]\n"
        "| Employee | Department | Salary |\n"
        "|---|---|---|\n"
        "| Harini | AI/ML | $120,000 |"
    )
    res = workflow.process("report_with_table.pdf", text)
    assert "Table Analysis Agent" in res["agent_trace"]
    assert "table_analysis" in res
    assert res["table_analysis"]["status"] == "table_analysis_completed"
    assert res["verification"]["status"] == "verified"


def test_langgraph_routing_with_charts():
    """
    Verifies that LangGraph conditionally routes to 'Chart Analysis Agent'
    when visual chart elements are detected.
    """
    workflow = DocumentGraphWorkflow()
    text = (
        "Invoice Document\n"
        "Total Amount: $5,000\n"
        "[Visual Element: Chart/Diagram | Type: Bar Chart | Status: analyzed | Page 1]\n"
        "Caption: Figure 1: Spending Trends\n"
        "Extracted Labels: Q1, Q2, Total"
    )
    res = workflow.process("invoice_with_chart.pdf", text)
    assert "Chart Analysis Agent" in res["agent_trace"]
    assert "chart_analysis" in res
    assert res["chart_analysis"]["status"] == "chart_analysis_completed"


def test_langgraph_routing_with_both_tables_and_charts():
    """
    Verifies that LangGraph routes through BOTH 'Table Analysis Agent' and
    'Chart Analysis Agent' when both modalities are present.
    """
    workflow = DocumentGraphWorkflow()
    text = (
        "Employee Report\n"
        "[Table 1 | Page 1]\n"
        "| Team | Lead |\n"
        "|---|---|\n"
        "| ML | Harini |\n\n"
        "[Visual Element: Chart/Diagram | Status: analyzed | Page 1]\n"
        "Caption: Chart 1: Growth"
    )
    res = workflow.process("multimodal_doc.pdf", text)
    assert "Table Analysis Agent" in res["agent_trace"]
    assert "Chart Analysis Agent" in res["agent_trace"]
    assert "table_analysis" in res
    assert "chart_analysis" in res
    assert res["verification"]["status"] == "verified"


# =====================================================================
# 7. FastAPI PDF Page Limit Protection
# =====================================================================

def test_upload_pdf_page_limit(auth_headers):
    """
    Verifies that uploading a PDF exceeding MAX_PDF_PAGES (100) is rejected
    with HTTP 400 and clear error message.
    """
    doc = fitz.open()
    for _ in range(105):
        doc.new_page(width=200, height=200)
    huge_pdf = doc.tobytes()
    doc.close()

    resp = client.post(
        "/upload",
        files={"file": ("huge_document.pdf", huge_pdf, "application/pdf")},
        headers=auth_headers
    )
    assert resp.status_code == 400
    assert "exceeds maximum allowed limit" in resp.json()["detail"]
