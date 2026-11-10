import io
import fitz  # PyMuPDF
import pytest
from unittest.mock import MagicMock

from backend.services.llm_provider import GeminiProvider, LLMError, LLMResponse, set_llm_provider
from backend.services.multimodal_service import extract_multimodal_pdf
from backend.services.qa_service import (
    DocumentQAService,
    is_header_or_metadata,
    clean_passage_text,
    get_substantive_sentences
)


@pytest.fixture(autouse=True)
def restore_llm():
    """Ensure LLM provider state is cleanly restored after each test."""
    yield
    set_llm_provider(None)


# ============================================================================
# 1. HEADER & METADATA FILTERING TESTS
# ============================================================================

def test_is_header_or_metadata_detection():
    """Verify that layout markers, page numbers, and headers are reliably identified."""
    assert is_header_or_metadata("Page 1 - Document Overview - Introduction.") is True
    assert is_header_or_metadata("Page 1 of 10 | Acme Platform Specification") is True
    assert is_header_or_metadata("--- Page 1 ---") is True
    assert is_header_or_metadata("[Table 1 | Page 1]") is True
    assert is_header_or_metadata("[Visual Element: Chart/Diagram | Page 2]") is True
    assert is_header_or_metadata("Caption: No explicit caption") is True
    assert is_header_or_metadata("Extracted Labels: None") is True
    assert is_header_or_metadata("Executive Summary") is True
    assert is_header_or_metadata("Table of Contents") is True
    assert is_header_or_metadata("1. INTRODUCTION") is True
    assert is_header_or_metadata("Section 2.1: Overview") is True
    assert is_header_or_metadata("SYNTHETIC TEST DATA - NOT A REAL COMPANY RECORD") is True

    # Real sentences must NOT be flagged as headers
    assert is_header_or_metadata("This platform automates multimodal document intelligence through autonomous multi-agent systems.") is False
    assert is_header_or_metadata("Total enterprise revenue reached $150 million in fiscal year 2026.") is False
    assert is_header_or_metadata("The Chief Technology Officer is Dr. Jane Smith.") is False
    assert is_header_or_metadata("The quality framework measures completeness, validity, consistency, uniqueness, timeliness, and traceability.") is False


def test_clean_passage_text_removes_page_markers_and_headers():
    """Verify clean_passage_text removes page divider lines while keeping body text."""
    raw = (
        "--- Page 1 ---\n"
        "Page 1 - Document Overview - Introduction.\n"
        "This platform automates multimodal document intelligence.\n"
        "It supports high-precision table extraction and generative QA.\n"
    )
    cleaned = clean_passage_text(raw)
    assert "--- Page 1 ---" not in cleaned
    assert "Page 1 - Document Overview" not in cleaned
    assert "This platform automates multimodal document intelligence." in cleaned
    assert "It supports high-precision table extraction and generative QA." in cleaned


def test_get_substantive_sentences_filters_layout_artifacts():
    """Verify get_substantive_sentences only returns substantive prose sentences."""
    raw = (
        "--- Page 1 ---\n"
        "Page 1 - Document Overview - Introduction.\n"
        "Executive Summary\n"
        "Acme Corp delivers cloud-native AI document solutions for regulated industries.\n"
        "The system complies with SOC 2 Type II and HIPAA security mandates.\n"
    )
    sentences = get_substantive_sentences(raw)
    assert len(sentences) == 2
    assert "Acme Corp delivers cloud-native AI document solutions" in sentences[0]
    assert "The system complies with SOC 2 Type II" in sentences[1]


# ============================================================================
# 2. SINGLE-DOCUMENT QA TESTS (NO METADATA / HEADER RETURNED)
# ============================================================================

def test_qa_header_and_page_metadata_never_returned_as_answer():
    """
    CRITICAL REGRESSION TEST:
    Verify that when user asks a question about document purpose or overview,
    the answer contains actual explanatory body text and NEVER page numbers or headings.
    """
    doc_text = (
        "--- Page 1 ---\n"
        "Page 1 - Document Overview - Introduction.\n"
        "Page 1 of 10 | Acme Platform Specification\n"
        "Executive Summary\n"
        "This enterprise platform automates multimodal document intelligence through autonomous multi-agent systems.\n"
        "The core objective is to accelerate document verification and audit readiness across enterprise workflows.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "What is the main purpose of this document?")

    assert result.has_sufficient_evidence is True
    ans_lower = result.answer.lower()

    # MUST NOT return page numbers, headers, or metadata
    assert "page 1 - document overview" not in ans_lower
    assert "page 1 of 10" not in ans_lower
    assert ans_lower.strip() != "executive summary"

    # MUST return the actual substantive explanatory answer
    assert "automates multimodal document intelligence" in ans_lower or "accelerate document verification" in ans_lower

    # Citations must also be substantive, never page headers
    assert len(result.citations) >= 1
    quote_lower = result.citations[0]["quote"].lower()
    assert "page 1 - document overview" not in quote_lower
    assert "page 1 of 10" not in quote_lower
    assert "automates multimodal document intelligence" in quote_lower or "accelerate document verification" in quote_lower


def test_qa_factual_question_returns_coherent_answer():
    """Verify factual questions return complete, coherent statements with exact figures."""
    doc_text = (
        "--- Page 3 ---\n"
        "Page 3 | Financial Overview & Performance\n"
        "In fiscal year 2024, Acme Corp achieved a net profit of $8.4 million, representing a 22 percent increase.\n"
        "Operating margins expanded to 31 percent due to automation efficiencies.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "What was the net profit in fiscal year 2024?")

    assert result.has_sufficient_evidence is True
    assert "$8.4 million" in result.answer or "$8.4 million" in result.citations[0]["quote"]
    assert "page 3 | financial overview" not in result.answer.lower()
    assert result.citations[0]["page_number"] == 3


def test_qa_definition_and_explanation_returns_thorough_answer():
    """Verify definition and explanation queries return multi-sentence substantive explanations."""
    doc_text = (
        "--- Page 1 ---\n"
        "Page 1 - Section 1: Methodology\n"
        "Tokenization is the algorithmic process of segmenting unstructured natural language text into discrete token units.\n"
        "This process preserves morphological root boundaries and facilitates dense vector mapping in high-dimensional semantic space.\n"
        "Downstream transformers utilize these token embeddings to calculate contextual self-attention scores.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "Explain what tokenization is and how it works.")

    assert result.has_sufficient_evidence is True
    ans_lower = result.answer.lower()
    assert "tokenization is the algorithmic process" in ans_lower
    assert "preserves morphological root boundaries" in ans_lower or "dense vector mapping" in ans_lower
    assert "page 1 - section 1" not in ans_lower


def test_qa_summary_question_synthesizes_body_paragraphs():
    """Verify document-level summary questions combine key narrative points and skip layout markers."""
    doc_text = (
        "--- Page 1 ---\n"
        "Page 1 - Document Overview - Introduction.\n"
        "Executive Summary\n"
        "Acme Corp transitioned 100 percent of on-premises workloads to cloud-native microservices.\n"
        "The migration reduced mean infrastructure latency from 120ms to 18ms.\n"
        "Annual cloud infrastructure expenditure was stabilized at $3.2 million.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "Provide a concise summary of the key findings in this document.")

    assert result.has_sufficient_evidence is True
    assert "summary of the document" in result.answer.lower()
    assert "page 1 - document overview" not in result.answer.lower()
    assert "executive summary" not in result.answer.lower()
    assert "transitioned 100 percent" in result.answer.lower() or "microservices" in result.answer.lower()


def test_qa_comparison_question_synthesizes_contrasting_evidence():
    """Verify comparison queries synthesize evidence across contrasting entities/years."""
    doc_text = (
        "--- Page 2 ---\n"
        "Comparative Financial Analysis.\n"
        "In fiscal year 2023, gross revenue was recorded at $12.0 million with operating expenses of $7.5 million.\n"
        "In fiscal year 2024, gross revenue surged to $14.2 million, while operating expenses decreased to $6.8 million.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "Compare the revenue and operating expenses between fiscal year 2023 and 2024.")

    assert result.has_sufficient_evidence is True
    ans = result.answer
    assert "$12.0 million" in ans
    assert "$14.2 million" in ans
    assert "comparative financial analysis" not in ans.lower() or len(ans) > 80


def test_qa_insufficient_evidence_clean_abstention():
    """Verify questions lacking evidence abstain cleanly without hallucinations or fake citations."""
    doc_text = (
        "--- Page 1 ---\n"
        "Acme Enterprise Cloud Migration Specification.\n"
        "The platform utilizes Kubernetes clusters deployed in Frankfurt and Dublin.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "What is the secret recipe for Belgian chocolate waffles?")

    assert result.has_sufficient_evidence is False
    assert "not contain enough evidence" in result.answer.lower()
    assert len(result.citations) == 0


# ============================================================================
# 3. MULTI-DOCUMENT QA TESTS (NO METADATA / HEADER RETURNED)
# ============================================================================

def test_multi_doc_qa_synthesis_no_headers_clean_attribution():
    """
    Verify multi-document synthesis extracts clean substantive sentences
    from each document, attributes citations properly, and excludes page headers.
    """
    docs = [
        {
            "id": 101,
            "filename": "revenue_report.pdf",
            "text": (
                "--- Page 1 ---\n"
                "Page 1 - Revenue Summary - FY2024\n"
                "Total enterprise gross revenue reached $18.5 million in fiscal year 2024.\n"
                "Software subscriptions contributed 72 percent of overall revenue.\n"
            )
        },
        {
            "id": 102,
            "filename": "headcount_report.pdf",
            "text": (
                "--- Page 1 ---\n"
                "Page 1 - Human Resources & Headcount\n"
                "Total enterprise headcount expanded to 240 full-time engineers and researchers.\n"
                "Engineering turnover remained below 3 percent throughout the fiscal year.\n"
            )
        }
    ]

    qa = DocumentQAService()
    result = qa.answer_multi_document_question(docs, "What was the total revenue and headcount in FY2024?")

    assert result.has_sufficient_evidence is True
    ans = result.answer

    # Both documents must be attributed in the synthesis
    assert "revenue_report.pdf" in ans
    assert "headcount_report.pdf" in ans

    # Must contain the substantive facts
    assert "$18.5 million" in ans
    assert "240" in ans

    # Must NOT contain the running page headers
    assert "page 1 - revenue summary" not in ans.lower()
    assert "page 1 - human resources" not in ans.lower()

    # Citations must be attributed and substantive
    assert len(result.citations) >= 2
    for c in result.citations:
        assert "page 1 -" not in c["quote"].lower()


# ============================================================================
# 4. GENERATIVE AI VS EXTRACTIVE FALLBACK TESTS
# ============================================================================

def test_gemini_generative_synthesis_when_configured():
    """Verify that when Gemini is configured, generative answer synthesis is executed."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.is_configured = True
    mock_provider.model = "gemini-1.5-flash"
    mock_provider.generate.return_value = LLMResponse(
        text=(
            "### 1. Platform Purpose\n"
            "The platform automates enterprise multimodal document intelligence.\n\n"
            "- Accelerates verification workflows\n"
            "- Guarantees audit readiness"
        ),
        model="gemini-1.5-flash",
        provider="Google Gemini",
        is_generated=True
    )
    set_llm_provider(mock_provider)

    doc_text = (
        "--- Page 1 ---\n"
        "Page 1 - Document Overview - Introduction.\n"
        "This enterprise platform automates multimodal document intelligence.\n"
        "It accelerates verification workflows and guarantees audit readiness.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "What is the primary purpose of the platform?")

    assert result.has_sufficient_evidence is True
    assert result.answer_mode == "generative"
    assert result.model_used == "gemini-1.5-flash"
    assert "### 1. Platform Purpose" in result.answer

    # Ensure prompt sent to Gemini was cleaned of raw page markers
    call_prompt = mock_provider.generate.call_args.kwargs["prompt"]
    assert "--- Page 1 ---" not in call_prompt


def test_gemini_fallback_on_api_error_returns_clean_substantive_answer():
    """Verify that when Gemini encounters an API error, fallback executes cleanly without error."""
    mock_provider = MagicMock(spec=GeminiProvider)
    mock_provider.is_configured = True
    mock_provider.generate.side_effect = LLMError("API Quota Exceeded")
    set_llm_provider(mock_provider)

    doc_text = (
        "--- Page 1 ---\n"
        "Page 1 - System Specifications.\n"
        "The distributed database replica achieves 99.999 percent uptime with automated multi-region failover.\n"
    )

    qa = DocumentQAService()
    result = qa.answer_question(doc_text, "What is the uptime of the distributed database replica?")

    assert result.has_sufficient_evidence is True
    assert result.answer_mode == "retrieval_fallback"
    assert "99.999 percent" in result.answer
    assert "page 1 - system specifications" not in result.answer.lower()


# ============================================================================
# 5. REALISTIC PDF FIXTURE INGESTION & QA PIPELINE TEST
# ============================================================================

def test_realistic_pdf_fixture_ingestion_and_qa():
    """
    Creates an authentic in-memory 2-page PDF with PyMuPDF, ingests it via extract_multimodal_pdf,
    and runs DocumentQAService to verify end-to-end question answering on actual extracted PDF text.
    """
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page(width=612, height=792)
    p1_text = (
        "Page 1 - Executive Summary - Enterprise Platform\n\n"
        "DocuAI Platform Architecture\n\n"
        "DocuAI is an enterprise multimodal AI platform designed for automated document intelligence.\n"
        "The platform coordinates specialized LangGraph agents to extract, classify, and verify unstructured documents.\n"
        "Security is enforced through authenticated AES-256 Fernet field-level encryption at rest.\n"
    )
    page1.insert_text((50, 72), p1_text, fontsize=11)

    # Page 2
    page2 = doc.new_page(width=612, height=792)
    p2_text = (
        "Page 2 - Financial Summary & Key Performance Indicators\n\n"
        "Fiscal Year 2025 Performance Metrics\n\n"
        "In fiscal year 2025, total recurring software revenue reached $24.8 million USD.\n"
        "The platform processed over 4.5 million multimodal pages with zero data leakage incidents.\n"
        "Operating expenses were held at $11.2 million USD, generating operating profit of $13.6 million USD.\n"
    )
    page2.insert_text((50, 72), p2_text, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()

    # Ingest using official multimodal extractor
    ingest_result = extract_multimodal_pdf(pdf_bytes)
    assert ingest_result.total_pages == 2
    full_text = ingest_result.full_text

    qa = DocumentQAService()

    # Query 1: Purpose / Architecture question
    q1_res = qa.answer_question(full_text, "What is DocuAI and what is its primary architecture?")
    assert q1_res.has_sufficient_evidence is True
    assert "page 1 - executive summary" not in q1_res.answer.lower()
    assert "langgraph agents" in q1_res.answer.lower() or "automated document intelligence" in q1_res.answer.lower()
    assert q1_res.citations[0]["page_number"] == 1

    # Query 2: Financial revenue question
    q2_res = qa.answer_question(full_text, "What was the total recurring software revenue in fiscal year 2025?")
    assert q2_res.has_sufficient_evidence is True
    assert "page 2 - financial summary" not in q2_res.answer.lower()
    assert "$24.8 million" in q2_res.answer or "$24.8 million" in q2_res.citations[0]["quote"]
    assert q2_res.citations[0]["page_number"] == 2

    # Query 3: Missing information question (Abstention)
    q3_res = qa.answer_question(full_text, "What is the CEO's favorite sports car?")
    assert q3_res.has_sufficient_evidence is False
    assert "not contain enough evidence" in q3_res.answer.lower()
    assert len(q3_res.citations) == 0
