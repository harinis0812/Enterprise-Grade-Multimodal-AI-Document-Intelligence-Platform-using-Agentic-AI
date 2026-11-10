import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.database.database import SessionLocal
from backend.database.models import Document, User, MultiDocQAHistory
from backend.core.security import create_access_token, hash_password

client = TestClient(app)


@pytest.fixture
def phase7_test_users_and_docs(setup_test_environment):
    db = SessionLocal()
    try:
        # Create User Alpha
        user_alpha = db.query(User).filter(User.email == "alpha_phase7@enterprise.com").first()
        if not user_alpha:
            user_alpha = User(
                email="alpha_phase7@enterprise.com",
                hashed_password=hash_password("Pass12345!"),
                full_name="User Alpha"
            )
            db.add(user_alpha)
            db.commit()
            db.refresh(user_alpha)

        # Create User Beta
        user_beta = db.query(User).filter(User.email == "beta_phase7@enterprise.com").first()
        if not user_beta:
            user_beta = User(
                email="beta_phase7@enterprise.com",
                hashed_password=hash_password("Pass12345!"),
                full_name="User Beta"
            )
            db.add(user_beta)
            db.commit()
            db.refresh(user_beta)

        # User Alpha Doc 1: Q1 Metrics
        doc_a1 = Document(
            filename="alpha_metrics_q1.pdf",
            document_type="Report",
            status="processed",
            user_id=user_alpha.id,
            extracted_text="--- Page 1 ---\nAlpha Corp Q1 revenue totaled $25 million with an operating profit of $6 million."
        )
        # User Alpha Doc 2: Q1 Expansion
        doc_a2 = Document(
            filename="alpha_expansion_q1.pdf",
            document_type="Report",
            status="processed",
            user_id=user_alpha.id,
            extracted_text="--- Page 1 ---\nAlpha Corp expansion roadmap allocated $4 million towards cloud AI infrastructure."
        )
        # User Beta Doc: Confidential Strategy
        doc_b = Document(
            filename="beta_confidential.pdf",
            document_type="Report",
            status="processed",
            user_id=user_beta.id,
            extracted_text="--- Page 1 ---\nBeta Industries confidential IP valuation is $50 million."
        )

        db.add_all([doc_a1, doc_a2, doc_b])
        db.commit()
        db.refresh(doc_a1)
        db.refresh(doc_a2)
        db.refresh(doc_b)

        token_alpha = create_access_token(data={"sub": str(user_alpha.id), "email": user_alpha.email})
        token_beta = create_access_token(data={"sub": str(user_beta.id), "email": user_beta.email})

        yield {
            "user_alpha": user_alpha,
            "user_beta": user_beta,
            "token_alpha": token_alpha,
            "token_beta": token_beta,
            "doc_a1": doc_a1,
            "doc_a2": doc_a2,
            "doc_b": doc_b,
        }
    finally:
        db.close()


def test_phase7_single_and_multi_qa_end_to_end(phase7_test_users_and_docs):
    """
    Verifies that single-document Q&A and multi-document Q&A both execute reliably
    for the authenticated owner, returning accurate page citations and document attribution.
    """
    env = phase7_test_users_and_docs
    headers_alpha = {"Authorization": f"Bearer {env['token_alpha']}"}

    # 1. Single-document Q&A
    single_payload = {"question": "What was the total revenue in Q1?"}
    single_res = client.post(
        f"/documents/{env['doc_a1'].id}/qa",
        json=single_payload,
        headers=headers_alpha
    )
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["has_sufficient_evidence"] is True
    assert len(single_data["citations"]) >= 1

    # 2. Multi-document synthesis Q&A across doc_a1 and doc_a2
    multi_payload = {
        "document_ids": [env["doc_a1"].id, env["doc_a2"].id],
        "question": "What was the revenue and cloud AI allocation?"
    }
    multi_res = client.post(
        "/documents/multi-qa",
        json=multi_payload,
        headers=headers_alpha
    )
    assert multi_res.status_code == 200
    multi_data = multi_res.json()
    assert multi_data["has_sufficient_evidence"] is True
    assert len(multi_data["citations"]) >= 2
    assert len(multi_data["documents_consulted"]) >= 1

    # Check citation document attribution
    citation_filenames = [c["filename"] for c in multi_data["citations"]]
    assert "alpha_metrics_q1.pdf" in citation_filenames or "alpha_expansion_q1.pdf" in citation_filenames

    # 3. Verify multi-document conversation history
    history_res = client.get("/documents/multi-qa/history", headers=headers_alpha)
    assert history_res.status_code == 200
    history_data = history_res.json()
    assert history_data["count"] >= 1
    assert any(h["question"] == "What was the revenue and cloud AI allocation?" for h in history_data["history"])


def test_phase7_cross_user_isolation(phase7_test_users_and_docs):
    """
    Verifies that User Alpha cannot access User Beta's documents in single-doc or multi-doc queries,
    and cannot see User Beta's Q&A history.
    """
    env = phase7_test_users_and_docs
    headers_alpha = {"Authorization": f"Bearer {env['token_alpha']}"}
    headers_beta = {"Authorization": f"Bearer {env['token_beta']}"}

    # 1. User Alpha attempts to query User Beta's doc via single-doc Q&A -> 403 Forbidden
    single_res = client.post(
        f"/documents/{env['doc_b'].id}/qa",
        json={"question": "What is the IP valuation?"},
        headers=headers_alpha
    )
    assert single_res.status_code == 403
    assert "Access denied" in single_res.json()["detail"]

    # 2. User Alpha attempts to include User Beta's doc in multi-doc query -> 403 Forbidden
    cross_res = client.post(
        "/documents/multi-qa",
        json={
            "document_ids": [env["doc_a1"].id, env["doc_b"].id],
            "question": "Compare revenue and valuation."
        },
        headers=headers_alpha
    )
    assert cross_res.status_code == 403
    assert "Access denied" in cross_res.json()["detail"]

    # 3. User Beta queries their own doc
    beta_multi_res = client.post(
        "/documents/multi-qa",
        json={
            "document_ids": [env["doc_b"].id],
            "question": "What is the valuation?"
        },
        headers=headers_beta
    )
    assert beta_multi_res.status_code == 200

    # 4. User Alpha cannot see User Beta's multi-doc history
    alpha_history = client.get("/documents/multi-qa/history", headers=headers_alpha).json()
    for h in alpha_history["history"]:
        assert h["question"] != "What is the valuation?"


def test_phase7_empty_doc_selection_validation(phase7_test_users_and_docs):
    """
    Verifies that passing an empty list of document_ids is safely rejected.
    """
    env = phase7_test_users_and_docs
    headers_alpha = {"Authorization": f"Bearer {env['token_alpha']}"}

    res = client.post(
        "/documents/multi-qa",
        json={"document_ids": [], "question": "What is the summary?"},
        headers=headers_alpha
    )
    # Rejects safely via Pydantic schema validation (min_length=1) with 422 Unprocessable Content
    assert res.status_code == 422
