import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.database import SessionLocal
from backend.database.models import Document, User, MultiDocQAHistory
from backend.core.security import create_access_token, hash_password
from backend.agents.graph_workflow import DocumentGraphWorkflow
from backend.services.qa_service import DocumentQAService
from backend.services.llm_provider import GeminiProvider, LLMResponse, set_llm_provider

client = TestClient(app)


@pytest.fixture
def test_users_and_docs(setup_test_environment):
    db = SessionLocal()
    try:
        # Create User A
        user_a = db.query(User).filter(User.email == "phase5_user_a@enterprise.com").first()
        if not user_a:
            user_a = User(
                email="phase5_user_a@enterprise.com",
                hashed_password=hash_password("Pass12345!"),
                full_name="User A"
            )
            db.add(user_a)
            db.commit()
            db.refresh(user_a)

        # Create User B
        user_b = db.query(User).filter(User.email == "phase5_user_b@enterprise.com").first()
        if not user_b:
            user_b = User(
                email="phase5_user_b@enterprise.com",
                hashed_password=hash_password("Pass12345!"),
                full_name="User B"
            )
            db.add(user_b)
            db.commit()
            db.refresh(user_b)

        # User A Doc 1: Revenue report
        doc_a1 = Document(
            filename="financial_q1.pdf",
            document_type="Report",
            status="processed",
            user_id=user_a.id,
            extracted_text="--- Page 1 ---\nIn Q1 2026, total revenue was $15 million with an operating margin of 22 percent."
        )
        # User A Doc 2: Expense report
        doc_a2 = Document(
            filename="expenses_q1.pdf",
            document_type="Report",
            status="processed",
            user_id=user_a.id,
            extracted_text="--- Page 1 ---\nIn Q1 2026, operating expenses reached $8 million across R&D and Marketing."
        )
        # User B Doc: Private strategy
        doc_b = Document(
            filename="confidential_strategy.pdf",
            document_type="Strategy",
            status="processed",
            user_id=user_b.id,
            extracted_text="--- Page 1 ---\nUser B confidential strategic acquisition target: Alpha Corp for $50 million."
        )

        db.add_all([doc_a1, doc_a2, doc_b])
        db.commit()
        db.refresh(doc_a1)
        db.refresh(doc_a2)
        db.refresh(doc_b)

        token_a = create_access_token({"sub": str(user_a.id), "email": user_a.email})
        token_b = create_access_token({"sub": str(user_b.id), "email": user_b.email})

        yield {
            "user_a": user_a,
            "user_b": user_b,
            "token_a": token_a,
            "token_b": token_b,
            "doc_a1": doc_a1,
            "doc_a2": doc_a2,
            "doc_b": doc_b
        }
    finally:
        db.close()


# =====================================================================
# 1. Agent Architecture & Execution Tracking
# =====================================================================

def test_agent_execution_tracking_and_metrics():
    """
    Verifies that the Agentic Workflow tracks execution metrics,
    including supervisor decisions and trace history.
    """
    workflow = DocumentGraphWorkflow()
    text = "Employee Report Harini Department AI Python Machine Learning"
    res = workflow.process("test_metrics.pdf", text)

    assert "agent_trace" in res
    assert "agent_metrics" in res
    assert "Supervisor Agent" in res["agent_metrics"]
    assert res["agent_metrics"]["Supervisor Agent"]["status"] == "completed"
    assert res["verification"]["status"] == "verified"


def test_supervisor_retry_boundary():
    """
    Verifies that the Supervisor enforces retry limits when extraction
    is missing, preventing infinite loops and escalating to verification.
    """
    workflow = DocumentGraphWorkflow()

    # Call supervisor with empty text and retry count 2
    state = {
        "extracted_text": "",
        "document_type": "",
        "document_information": {},
        "analysis": {},
        "agent_trace": [],
        "retry_counts": {"extraction": 2}
    }
    decision = workflow._supervisor_node(state)
    assert decision["supervisor_decision"]["next_agent"] == "verification"
    assert "retry threshold reached" in decision["supervisor_decision"]["reason"].lower()


# =====================================================================
# 2. Intelligent Document Understanding & Intent Classification
# =====================================================================

def test_question_intent_classification():
    """
    Verifies that classify_question_intent accurately identifies
    financial, comparative, tabular, visual, and summary intents.
    """
    qa = DocumentQAService()

    # Financial
    fin_res = qa.classify_question_intent("What is the total revenue and salary budget?")
    assert fin_res["intent"] == "financial"
    assert fin_res["is_financial"] is True

    # Comparison
    comp_res = qa.classify_question_intent("Compare the differences between Q1 and Q2 performance")
    assert comp_res["intent"] == "comparison"
    assert comp_res["is_comparison"] is True

    # Tabular
    tab_res = qa.classify_question_intent("Show me the breakdown in the table of employees")
    assert tab_res["intent"] == "tabular"
    assert tab_res["is_tabular"] is True

    # Visual
    vis_res = qa.classify_question_intent("What does the growth trajectory chart indicate?")
    assert vis_res["intent"] == "visual"
    assert vis_res["is_visual"] is True

    # Summary
    sum_res = qa.classify_question_intent("Summarize the key findings of this report")
    assert sum_res["intent"] == "summary"
    assert sum_res["is_summary"] is True


# =====================================================================
# 3. Multi-Document Retrieval & Question Answering
# =====================================================================

def test_multi_document_retrieval_and_answer():
    """
    Verifies that DocumentQAService retrieves and answers questions
    across multiple documents with clear source attribution.
    """
    qa = DocumentQAService()
    docs = [
        {
            "id": 101,
            "filename": "revenue.pdf",
            "text": "--- Page 1 ---\nAnnual recurring revenue reached $25 million in 2026."
        },
        {
            "id": 102,
            "filename": "headcount.pdf",
            "text": "--- Page 1 ---\nTotal engineering headcount increased to 120 employees."
        }
    ]

    passages = qa.retrieve_multi_document_passages(docs, "What was the revenue and how many employees?")
    assert len(passages) >= 2

    # Check attribution metadata
    doc_ids_found = {p.passage.metadata.get("document_id") for p in passages}
    assert 101 in doc_ids_found
    assert 102 in doc_ids_found

    # Test multi-doc answer fallback
    result = qa.answer_multi_document_question(docs, "What was the revenue and headcount?")
    assert result.has_sufficient_evidence is True
    assert len(result.citations) >= 2
    assert "revenue.pdf" in result.answer or "headcount.pdf" in result.answer


# =====================================================================
# 4. Multi-Document API & Strict Multi-Tenant Isolation
# =====================================================================

def test_multi_doc_qa_api_success(test_users_and_docs):
    """
    Verifies that User A can query across multiple documents they own.
    """
    env = test_users_and_docs
    headers = {"Authorization": f"Bearer {env['token_a']}"}

    payload = {
        "document_ids": [env["doc_a1"].id, env["doc_a2"].id],
        "question": "What was the total revenue and operating expenses in Q1?"
    }

    resp = client.post("/documents/multi-qa", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_sufficient_evidence"] is True
    assert len(data["citations"]) >= 2
    assert len(data["documents_consulted"]) >= 1
    assert "financial_q1.pdf" in data["documents_consulted"] or "expenses_q1.pdf" in data["documents_consulted"]


def test_multi_doc_qa_cross_user_denial(test_users_and_docs):
    """
    Verifies that User A CANNOT include a document owned by User B in a multi-doc query.
    Access must be denied with HTTP 403.
    """
    env = test_users_and_docs
    headers = {"Authorization": f"Bearer {env['token_a']}"}

    # Attempt to query User A doc + User B doc
    payload = {
        "document_ids": [env["doc_a1"].id, env["doc_b"].id],
        "question": "What is the strategic acquisition target?"
    }

    resp = client.post("/documents/multi-qa", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "Access denied" in resp.json()["detail"]


def test_multi_doc_qa_not_found(test_users_and_docs):
    """
    Verifies that querying a non-existent document ID returns HTTP 404.
    """
    env = test_users_and_docs
    headers = {"Authorization": f"Bearer {env['token_a']}"}

    payload = {
        "document_ids": [env["doc_a1"].id, 999999],
        "question": "What is the revenue?"
    }

    resp = client.post("/documents/multi-qa", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_multi_doc_qa_history(test_users_and_docs):
    """
    Verifies that multi-document Q&A turns are saved and queryable via history API.
    """
    env = test_users_and_docs
    headers = {"Authorization": f"Bearer {env['token_a']}"}

    # Execute a query first
    client.post(
        "/documents/multi-qa",
        json={"document_ids": [env["doc_a1"].id], "question": "What was the revenue?"},
        headers=headers
    )

    # Fetch history
    resp = client.get("/documents/multi-qa/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    assert len(data["history"]) >= 1
    assert data["history"][0]["question"] == "What was the revenue?"
