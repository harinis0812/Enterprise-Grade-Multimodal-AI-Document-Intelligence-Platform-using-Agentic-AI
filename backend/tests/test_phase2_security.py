import os
import sqlite3
import uuid
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.encryption import encrypt_text, decrypt_text, is_encrypted
from backend.core.rate_limit import limiter
from backend.core.security import (
    cleanup_expired_revoked_tokens,
    create_access_token,
    decode_access_token,
    hash_password,
    is_token_revoked,
    revoke_token,
)
from backend.database.database import SessionLocal, engine
from backend.database.init_db import init_database
from backend.database.models import Document, QAHistory, RevokedToken, User
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_limiter_state():
    """Reset rate limiter records before and after each test."""
    limiter.reset()
    yield
    limiter.reset()


def get_test_db() -> Session:
    return SessionLocal()


# ============================================================================
# 1. API RATE LIMITING TESTS
# ============================================================================

def test_login_rate_limiting():
    """Verify exceeding login rate limit returns HTTP 429."""
    limiter.reset()
    headers = {"X-Forwarded-For": "198.51.100.10"}
    payload = {"email": "rate_test@example.com", "password": "WrongPassword123!"}

    # Make 5 attempts (configured LOGIN_RATE_LIMIT=5/minute)
    responses = [
        client.post("/auth/login", json=payload, headers=headers)
        for _ in range(5)
    ]
    # First 5 should be 401 Unauthorized (invalid credentials, not 429)
    assert all(r.status_code == 401 for r in responses)

    # 6th attempt should be blocked by rate limiter with HTTP 429
    blocked_response = client.post("/auth/login", json=payload, headers=headers)
    assert blocked_response.status_code == 429
    assert "Too many login attempts" in blocked_response.json()["detail"]
    assert "Retry-After" in blocked_response.headers


def test_register_rate_limiting():
    """Verify exceeding registration rate limit returns HTTP 429."""
    limiter.reset()
    headers = {"X-Forwarded-For": "198.51.100.20"}

    # Attempt 3 registrations (REGISTER_RATE_LIMIT=3/minute)
    for i in range(3):
        res = client.post(
            "/auth/register",
            json={
                "email": f"ratereg_{uuid.uuid4().hex[:6]}@example.com",
                "password": "Password123!",
                "full_name": f"User {i}"
            },
            headers=headers
        )
        assert res.status_code in [201, 400]

    # 4th attempt must trigger HTTP 429
    res_blocked = client.post(
        "/auth/register",
        json={
            "email": "ratereg_blocked@example.com",
            "password": "Password123!",
            "full_name": "Blocked"
        },
        headers=headers
    )
    assert res_blocked.status_code == 429
    assert "Too many registration attempts" in res_blocked.json()["detail"]


def test_rate_limit_ip_isolation():
    """Verify rate limiting on IP A does not lock out IP B."""
    limiter.reset()
    ip_a_headers = {"X-Forwarded-For": "198.51.100.31"}
    ip_b_headers = {"X-Forwarded-For": "198.51.100.32"}

    # Exhaust IP A
    for _ in range(5):
        client.post("/auth/login", json={"email": "a@test.com", "password": "pwd"}, headers=ip_a_headers)
    assert client.post("/auth/login", json={"email": "a@test.com", "password": "pwd"}, headers=ip_a_headers).status_code == 429

    # IP B should NOT be rate-limited
    res_b = client.post("/auth/login", json={"email": "b@test.com", "password": "pwd"}, headers=ip_b_headers)
    assert res_b.status_code != 429


# ============================================================================
# 2. SERVER-SIDE JWT REVOCATION & EXPIRY TESTS
# ============================================================================

def test_access_token_has_jti_claim():
    """Verify newly minted JWT access tokens include a unique jti claim."""
    token = create_access_token(data={"sub": "123", "email": "jti_test@example.com"})
    payload = decode_access_token(token)
    assert "jti" in payload
    assert len(payload["jti"]) >= 16


def test_logout_revokes_token():
    """Verify calling POST /auth/logout adds token jti to revoked_tokens store."""
    db = get_test_db()
    email = f"logout_{uuid.uuid4().hex[:6]}@example.com"
    user = User(email=email, hashed_password=hash_password("Pass123!"), is_active=True, role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    payload = decode_access_token(token)
    jti = payload["jti"]

    assert not is_token_revoked(db, jti)

    # Perform logout
    res = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "revoked" in res.json()["message"].lower()

    # Verify persistent revocation in DB
    assert is_token_revoked(db, jti)
    db.close()


def test_revoked_token_rejected_on_auth_me():
    """Verify that a revoked token is rejected with HTTP 401 on /auth/me."""
    db = get_test_db()
    email = f"revoke_me_{uuid.uuid4().hex[:6]}@example.com"
    user = User(email=email, hashed_password=hash_password("Pass123!"), is_active=True, role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    assert client.get("/auth/me", headers=headers).status_code == 200

    # Logout to revoke token
    assert client.post("/auth/logout", headers=headers).status_code == 200

    # Token must now be rejected with 401
    res_me_revoked = client.get("/auth/me", headers=headers)
    assert res_me_revoked.status_code == 401
    assert "revoked" in res_me_revoked.json()["detail"].lower()
    db.close()


def test_revoked_token_rejected_on_documents_endpoint():
    """Verify that a revoked token is rejected with HTTP 401 on /documents."""
    db = get_test_db()
    email = f"revoke_docs_{uuid.uuid4().hex[:6]}@example.com"
    user = User(email=email, hashed_password=hash_password("Pass123!"), is_active=True, role="user")
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    assert client.get("/documents", headers=headers).status_code == 200

    # Logout to revoke token
    assert client.post("/auth/logout", headers=headers).status_code == 200

    # Token must now be rejected with 401 on /documents
    res_docs_revoked = client.get("/documents", headers=headers)
    assert res_docs_revoked.status_code == 401
    assert "revoked" in res_docs_revoked.json()["detail"].lower()
    db.close()


def test_token_cleanup_function():
    """Verify cleanup_expired_revoked_tokens removes past expired records."""
    db = get_test_db()
    past_jti = f"expired_jti_{uuid.uuid4().hex}"
    future_jti = f"active_jti_{uuid.uuid4().hex}"

    # Past expired token
    db.add(RevokedToken(
        jti=past_jti,
        expires_at=datetime.utcnow() - timedelta(minutes=10),
        revoked_at=datetime.utcnow() - timedelta(minutes=20)
    ))
    # Active unexpired token
    db.add(RevokedToken(
        jti=future_jti,
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        revoked_at=datetime.utcnow()
    ))
    db.commit()

    deleted = cleanup_expired_revoked_tokens(db)
    assert deleted >= 1

    assert not is_token_revoked(db, past_jti)
    assert is_token_revoked(db, future_jti)
    db.close()


# ============================================================================
# 3. AUTHENTICATED ENCRYPTION AT REST TESTS
# ============================================================================

def test_document_extracted_text_encrypted_at_rest():
    """Verify Document.extracted_text is encrypted with Fernet in the raw SQLite database."""
    db = get_test_db()
    user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()
    assert user is not None

    plain_content = f"Confidential Enterprise Financial Record {uuid.uuid4().hex}"
    doc = Document(
        filename="confidential_audit.txt",
        document_type="Financial",
        status="completed",
        extracted_text=plain_content,
        user_id=user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    doc_id = doc.id
    db.close()

    # Inspect raw database storage directly using raw SQL
    conn = sqlite3.connect("docuai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT extracted_text FROM documents WHERE id = ?", (doc_id,))
    raw_stored_text = cursor.fetchone()[0]
    conn.close()

    # Raw value in SQLite must be Fernet ciphertext (starts with gAAAAA)
    assert raw_stored_text.startswith("gAAAAA")
    assert plain_content not in raw_stored_text
    assert is_encrypted(raw_stored_text)


def test_document_analysis_and_trace_encrypted_at_rest():
    """Verify analysis and agent_trace fields are encrypted at rest."""
    db = get_test_db()
    user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()

    raw_analysis = '{"confidential_metric": 99.8, "sensitive_tag": "classified"}'
    raw_trace = '[{"agent": "SecurityAgent", "step": "verified_auth"}]'

    doc = Document(
        filename="analysis_trace_test.txt",
        document_type="Report",
        status="completed",
        extracted_text="Some document text",
        analysis=raw_analysis,
        agent_trace=raw_trace,
        user_id=user.id
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()

    conn = sqlite3.connect("docuai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT analysis, agent_trace FROM documents WHERE id = ?", (doc_id,))
    stored_analysis, stored_trace = cursor.fetchone()
    conn.close()

    assert stored_analysis.startswith("gAAAAA")
    assert stored_trace.startswith("gAAAAA")
    assert "confidential_metric" not in stored_analysis
    assert "SecurityAgent" not in stored_trace


def test_qa_history_encrypted_at_rest():
    """Verify QAHistory question and answer fields are stored encrypted in SQLite."""
    db = get_test_db()
    user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()
    doc = db.query(Document).filter(Document.user_id == user.id).first()
    assert doc is not None

    plain_q = f"What is the secret trade revenue {uuid.uuid4().hex[:6]}?"
    plain_a = f"The secret trade revenue is $50,000,000 {uuid.uuid4().hex[:6]}."

    qa = QAHistory(
        document_id=doc.id,
        user_id=user.id,
        question=plain_q,
        answer=plain_a
    )
    db.add(qa)
    db.commit()
    qa_id = qa.id
    db.close()

    conn = sqlite3.connect("docuai.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question, answer FROM qa_history WHERE id = ?", (qa_id,))
    stored_q, stored_a = cursor.fetchone()
    conn.close()

    assert stored_q.startswith("gAAAAA")
    assert stored_a.startswith("gAAAAA")
    assert plain_q not in stored_q
    assert plain_a not in stored_a


def test_encryption_transparent_decryption():
    """Verify reading encrypted entities via SQLAlchemy transparently provides decrypted plaintext."""
    db = get_test_db()
    user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()

    unique_phrase = f"Unique Plaintext String {uuid.uuid4().hex}"
    doc = Document(
        filename="transparent_decrypt.txt",
        document_type="Contract",
        status="completed",
        extracted_text=unique_phrase,
        analysis=f'{{"phrase": "{unique_phrase}"}}',
        user_id=user.id
    )
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()

    # Re-query through a fresh SQLAlchemy session
    new_db = get_test_db()
    reloaded_doc = new_db.query(Document).filter(Document.id == doc_id).first()
    assert reloaded_doc.extracted_text == unique_phrase
    assert unique_phrase in reloaded_doc.analysis
    new_db.close()


# ============================================================================
# 4. ROLE-BASED ACCESS CONTROL (RBAC) TESTS
# ============================================================================

def test_rbac_registration_defaults_to_user_role():
    """Verify public registration always assigns 'user' role regardless of request payload."""
    reg_email = f"rbac_user_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/auth/register",
        json={
            "email": reg_email,
            "password": "SecurePassword123!",
            "full_name": "Standard Employee",
            "role": "admin"  # Attempt to elevate privilege during registration
        }
    )
    assert res.status_code == 201
    user_data = res.json()["user"]
    assert user_data["role"] == "user"

    # Confirm in DB
    db = get_test_db()
    created_user = db.query(User).filter(User.email == reg_email).first()
    assert created_user.role == "user"
    db.close()


def test_rbac_admin_route_protection():
    """Verify non-admin users receive HTTP 403 Forbidden on /admin/* routes, and admins succeed."""
    db = get_test_db()

    # Create a regular user
    regular_email = f"regular_{uuid.uuid4().hex[:6]}@example.com"
    regular_user = User(
        email=regular_email,
        hashed_password=hash_password("Pass123!"),
        role="user",
        is_active=True
    )
    db.add(regular_user)

    # Create an admin user
    admin_email = f"admin_{uuid.uuid4().hex[:6]}@example.com"
    admin_user = User(
        email=admin_email,
        hashed_password=hash_password("AdminPass123!"),
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(regular_user)
    db.refresh(admin_user)

    regular_token = create_access_token(data={"sub": str(regular_user.id), "email": regular_user.email, "role": "user"})
    admin_token = create_access_token(data={"sub": str(admin_user.id), "email": admin_user.email, "role": "admin"})
    db.close()

    # 1. Regular user accessing /admin/users must get 403 Forbidden
    res_forbidden = client.get("/admin/users", headers={"Authorization": f"Bearer {regular_token}"})
    assert res_forbidden.status_code == 403
    assert "Administrator privileges required" in res_forbidden.json()["detail"]

    # 2. Regular user accessing /admin/stats must get 403 Forbidden
    res_stats_forbidden = client.get("/admin/stats", headers={"Authorization": f"Bearer {regular_token}"})
    assert res_stats_forbidden.status_code == 403

    # 3. Admin user accessing /admin/users must succeed (200 OK)
    res_admin = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    users_list = res_admin.json()
    assert isinstance(users_list, list)
    assert any(u["email"] == admin_email for u in users_list)

    # 4. Admin user accessing /admin/stats must succeed
    res_stats = client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_users" in stats
    assert "total_documents" in stats
