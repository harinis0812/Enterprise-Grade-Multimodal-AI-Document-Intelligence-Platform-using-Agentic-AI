import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.qa_service import DocumentQAService, segment_document_into_passages

client = TestClient(app)


def test_qa_service_unit_relevant_answer_and_citation():
    doc_text = (
        "--- Page 1 ---\n"
        "Acme Corporation Financial Report 2026.\n"
        "Total enterprise revenue reached $150 million in fiscal year 2026.\n"
        "Operating expenses were held at $45 million.\n\n"
        "--- Page 2 ---\n"
        "The Chief Technology Officer is Dr. Jane Smith.\n"
        "Engineering headquarters is located in Austin, Texas.\n"
    )

    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(doc_text, "What was the total enterprise revenue?")

    assert has_evidence is True
    assert "$150 million" in answer or "$150 million" in citations[0]["quote"]
    assert len(citations) >= 1
    assert citations[0]["page_number"] == 1
    assert citations[0]["confidence"] > 0.5


def test_qa_service_unit_insufficient_evidence():
    doc_text = (
        "--- Page 1 ---\n"
        "Acme Corporation sells industrial manufacturing hardware.\n"
        "All products are manufactured in Ohio.\n"
    )

    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(doc_text, "Who won the 1994 football world cup?")

    assert has_evidence is False
    assert len(citations) == 0
    assert "not contain enough evidence" in answer.lower()


def test_qa_service_unit_empty_document():
    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question("", "What is the policy?")

    assert has_evidence is False
    assert len(citations) == 0
    assert "empty" in answer.lower()


def test_qa_service_unit_summary_query():
    doc_text = (
        "--- Page 1 ---\n"
        "Global Enterprise Strategy 2026.\n"
        "This strategic initiative focuses on digital transformation and agentic AI integration.\n"
        "The project aims to achieve 99.4 percent accuracy across document verification pipelines.\n"
    )
    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(
        doc_text,
        "Provide a concise summary of the key findings in this document."
    )

    assert has_evidence is True
    assert len(citations) >= 1
    assert citations[0]["page_number"] == 1
    assert "summary" in answer.lower()
    assert "digital transformation" in answer.lower() or "accuracy" in answer.lower()


def test_qa_service_unit_financial_query_extracts_concrete_value():
    doc_text = (
        "--- Page 1 ---\n"
        "Procurement and Billing Specification.\n"
        "The report should extract the currency, each category, each amount, and the total.\n\n"
        "--- Page 2 ---\n"
        "Invoice Breakdown and Final Charges.\n"
        "Category A Hardware: $42,500.\n"
        "Total billing amount finalized at $128,750 USD.\n"
    )
    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(
        doc_text,
        "What is the total amount or financial value mentioned?"
    )

    assert has_evidence is True
    assert len(citations) >= 1
    # Ensure it extracted the concrete monetary value, NOT the instruction sentence
    assert "$128,750" in answer or "$128,750" in citations[0]["quote"]
    assert "the report should extract" not in answer.lower()
    assert citations[0]["page_number"] == 2


def test_qa_service_unit_financial_query_no_values():
    doc_text = (
        "--- Page 1 ---\n"
        "Employee Code of Conduct and Work Ethics.\n"
        "All staff members must wear formal identification badges.\n"
    )
    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(
        doc_text,
        "What is the total amount or financial value mentioned?"
    )

    assert has_evidence is False
    assert len(citations) == 0
    assert "not contain" in answer.lower() or "not mention" in answer.lower()


def test_qa_service_unit_data_quality_framework_overview():
    doc_text = (
        "--- Page 1 ---\n"
        "DocuAI Enterprise Multimodal Platform Architecture Overview.\n"
        "This platform orchestrates autonomous LangGraph agent workflows for enterprise intelligence.\n\n"
        "--- Page 15 ---\n"
        "Security, Access Control, and Authentication Protocol.\n"
        "Multi-tenant isolation is strictly enforced via JWT bearer tokens and tenant foreign keys.\n\n"
        "--- Page 29 ---\n"
        "Data Quality Framework Reference: NES-DOC-TEST-030 Section: Data Quality Framework Overview.\n"
        "The quality framework measures completeness, validity, consistency, uniqueness, timeliness, and traceability.\n"
        "Completeness asks whether required fields are present. Validity checks whether values meet allowed formats.\n"
        "Consistency compares related fields. Uniqueness identifies duplicate records.\n"
    )
    qa = DocumentQAService()
    answer, citations, has_evidence = qa.answer_question(
        doc_text,
        "overview of data quality framework"
    )

    assert has_evidence is True
    assert len(citations) >= 1
    # MUST locate the actual Data Quality Framework section on Page 29, NEVER Page 1
    assert citations[0]["page_number"] == 29
    assert "completeness" in answer.lower()
    assert "validity" in answer.lower()
    assert "traceability" in answer.lower()
    # Honest match score should not be artificially clamped to a fake 0.95
    assert 0.0 < citations[0]["confidence"] <= 1.0


def test_qa_service_unit_distinct_questions_return_distinct_pages_and_evidence():
    doc_text = (
        "--- Page 1 ---\n"
        "Acme Enterprise Annual Report.\n"
        "Fiscal Year 2026 total revenue reached $150 million.\n\n"
        "--- Page 7 ---\n"
        "Human Resources and Key Executive Personnel.\n"
        "The Chief Technology Officer is Dr. Jane Smith.\n\n"
        "--- Page 14 ---\n"
        "Global Facilities and Real Estate.\n"
        "The primary engineering headquarters is located in Austin, Texas.\n"
    )
    qa = DocumentQAService()

    # Query 1: Revenue
    ans1, cite1, ev1 = qa.answer_question(doc_text, "What was the total enterprise revenue?")
    assert ev1 is True
    assert cite1[0]["page_number"] == 1
    assert "$150 million" in ans1 or "$150 million" in cite1[0]["quote"]

    # Query 2: Executive
    ans2, cite2, ev2 = qa.answer_question(doc_text, "Who is the Chief Technology Officer?")
    assert ev2 is True
    assert cite2[0]["page_number"] == 7
    assert "Jane Smith" in ans2 or "Jane Smith" in cite2[0]["quote"]

    # Query 3: Headquarters
    ans3, cite3, ev3 = qa.answer_question(doc_text, "Where is the engineering headquarters located?")
    assert ev3 is True
    assert cite3[0]["page_number"] == 14
    assert "Austin" in ans3 or "Austin" in cite3[0]["quote"]

    # Query 4: Unrelated query -> Insufficient evidence
    ans4, cite4, ev4 = qa.answer_question(doc_text, "What is the recipe for chocolate cake?")
    assert ev4 is False
    assert len(cite4) == 0
    assert "not contain enough evidence" in ans4.lower()



def test_document_qa_api_end_to_end_and_isolation():
    """
    Test complete lifecycle:
    1. User 1 registers and uploads a document.
    2. User 1 asks a question -> receives valid answer with citations.
    3. User 1 asks an irrelevant question -> receives insufficient evidence notice.
    4. User 1 views QA history -> turn history is recorded.
    5. User 2 attempts to query User 1's document -> 403 Forbidden.
    6. User 2 attempts to view User 1's QA history -> 403 Forbidden.
    7. User 2 document list does not contain User 1's document.
    """
    # Register User 1
    user1_email = "qa_user1_test@enterprise.com"
    r1 = client.post("/auth/register", json={"email": user1_email, "password": "User1Password123!", "full_name": "QA User One"})
    token1 = r1.json()["access_token"] if r1.status_code == 201 else client.post("/auth/login", json={"email": user1_email, "password": "User1Password123!"}).json()["access_token"]

    # Register User 2
    user2_email = "qa_user2_test@enterprise.com"
    r2 = client.post("/auth/register", json={"email": user2_email, "password": "User2Password123!", "full_name": "QA User Two"})
    token2 = r2.json()["access_token"] if r2.status_code == 201 else client.post("/auth/login", json={"email": user2_email, "password": "User2Password123!"}).json()["access_token"]

    client1 = TestClient(app)
    client1.headers["Authorization"] = f"Bearer {token1}"

    client2 = TestClient(app)
    client2.headers["Authorization"] = f"Bearer {token2}"

    # 1. User 1 uploads a document
    doc_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kinds [] /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 75 >> stream\n"
        b"BT /F1 12 Tf 100 700 Td (Annual Security Audit Report. The security audit score is 98 percent.) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000125 00000 n\n0000000223 00000 n\n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n348\n%%EOF"
    )
    upload_res = client1.post("/upload", files={"file": ("security_audit_user1.pdf", doc_content, "application/pdf")})
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # 2. User 1 asks a question with clear evidence
    qa_res = client1.post(f"/documents/{doc_id}/qa", json={"question": "What is the security audit score?"})
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert qa_data["document_id"] == doc_id
    assert qa_data["has_sufficient_evidence"] is True
    assert "98 percent" in qa_data["answer"] or "98 percent" in str(qa_data["citations"])
    assert len(qa_data["citations"]) >= 1

    # 3. User 1 asks a question with insufficient evidence
    qa_insuf_res = client1.post(f"/documents/{doc_id}/qa", json={"question": "What is the recipe for chocolate cake?"})
    assert qa_insuf_res.status_code == 200
    qa_insuf_data = qa_insuf_res.json()
    assert qa_insuf_data["has_sufficient_evidence"] is False
    assert len(qa_insuf_data["citations"]) == 0
    assert "not contain enough evidence" in qa_insuf_data["answer"].lower()

    # 4. User 1 views QA history
    history_res = client1.get(f"/documents/{doc_id}/qa/history")
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["count"] >= 2
    assert len(history_data["history"]) >= 2

    # 5. User 2 attempts to query User 1's document -> 403 Forbidden
    u2_qa_res = client2.post(f"/documents/{doc_id}/qa", json={"question": "What is the score?"})
    assert u2_qa_res.status_code == 403
    assert "access denied" in u2_qa_res.json()["detail"].lower()

    # 6. User 2 attempts to view User 1's QA history -> 403 Forbidden
    u2_hist_res = client2.get(f"/documents/{doc_id}/qa/history")
    assert u2_hist_res.status_code == 403
    assert "access denied" in u2_hist_res.json()["detail"].lower()

    # 7. User 2 attempts to view User 1's document details -> 403 Forbidden
    u2_doc_res = client2.get(f"/documents/{doc_id}")
    assert u2_doc_res.status_code == 403

    # 8. User 2 lists documents -> User 1's private document should not be returned
    u2_list_res = client2.get("/documents")
    assert u2_list_res.status_code == 200
    u2_doc_ids = [d["id"] for d in u2_list_res.json()["documents"]]
    assert doc_id not in u2_doc_ids

    # 9. QA on non-existent document ID -> 404
    not_found_res = client1.post("/documents/9999999/qa", json={"question": "Where is it?"})
    assert not_found_res.status_code == 404


def test_document_qa_validation_errors():
    client1 = TestClient(app)
    # Register/login
    user_email = "qa_val_test@enterprise.com"
    r = client.post("/auth/register", json={"email": user_email, "password": "User1Password123!", "full_name": "Val User"})
    token = r.json()["access_token"] if r.status_code == 201 else client.post("/auth/login", json={"email": user_email, "password": "User1Password123!"}).json()["access_token"]
    client1.headers["Authorization"] = f"Bearer {token}"

    # Empty question
    res = client1.post("/documents/1/qa", json={"question": "   "})
    assert res.status_code == 422

    # Missing question
    res2 = client1.post("/documents/1/qa", json={})
    assert res2.status_code == 422
