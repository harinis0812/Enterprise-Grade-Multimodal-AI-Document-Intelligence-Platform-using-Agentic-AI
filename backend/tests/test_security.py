import pytest
from fastapi.testclient import TestClient

from backend.core.security import verify_password
from backend.database.database import SessionLocal
from backend.database.models import AuditLog, Document, User
from backend.main import app

client = TestClient(app)


def test_user_registration_success():
    email = "new_employee@enterprise.com"
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "full_name": "New Enterprise Employee"
        }
    )
    # May be 201 or 400 if already created in earlier test run
    if response.status_code == 201:
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == email

        # Verify plaintext password was NEVER stored in DB
        db = SessionLocal()
        user = db.query(User).filter(User.email == email).first()
        db.close()
        assert user is not None
        assert user.hashed_password != "SecurePassword123!"
        assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")
        assert verify_password("SecurePassword123!", user.hashed_password)


def test_user_registration_duplicate_email():
    email = "duplicate_test@enterprise.com"
    client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": "First User"
        }
    )
    response2 = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "Password456!",
            "full_name": "Second User"
        }
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()


def test_user_registration_weak_password():
    response = client.post(
        "/auth/register",
        json={
            "email": "weak@enterprise.com",
            "password": "123",
            "full_name": "Weak User"
        }
    )
    assert response.status_code == 422


def test_user_login_success():
    email = "login_test@enterprise.com"
    pwd = "LoginPassword123!"
    client.post(
        "/auth/register",
        json={"email": email, "password": pwd, "full_name": "Login User"}
    )

    login_res = client.post(
        "/auth/login",
        json={"email": email, "password": pwd}
    )
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["email"] == email


def test_user_login_invalid_credentials():
    response = client.post(
        "/auth/login",
        json={"email": "nonexistent@enterprise.com", "password": "WrongPassword!"}
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_protected_endpoints_deny_unauthenticated_requests():
    unauth_client = TestClient(app)

    # Documents list without auth
    res1 = unauth_client.get("/documents")
    assert res1.status_code == 401

    # Upload without auth
    res2 = unauth_client.post(
        "/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4 sample", "application/pdf")}
    )
    assert res2.status_code == 401

    # Auth me without auth
    res3 = unauth_client.get("/auth/me")
    assert res3.status_code == 401


def test_tampered_token_is_rejected():
    tampered_client = TestClient(app)
    tampered_client.headers["Authorization"] = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.tampered.token"

    res = tampered_client.get("/documents")
    assert res.status_code == 401


def test_multi_tenant_document_isolation():
    """
    Verify that User B cannot read or query documents uploaded by User A.
    """
    # Create User A
    user_a_email = "usera_iso@enterprise.com"
    res_a = client.post(
        "/auth/register",
        json={"email": user_a_email, "password": "UserAPassword123!", "full_name": "User A"}
    )
    if res_a.status_code == 201:
        token_a = res_a.json()["access_token"]
    else:
        login_a = client.post("/auth/login", json={"email": user_a_email, "password": "UserAPassword123!"})
        token_a = login_a.json()["access_token"]

    # Create User B
    user_b_email = "userb_iso@enterprise.com"
    res_b = client.post(
        "/auth/register",
        json={"email": user_b_email, "password": "UserBPassword123!", "full_name": "User B"}
    )
    if res_b.status_code == 201:
        token_b = res_b.json()["access_token"]
    else:
        login_b = client.post("/auth/login", json={"email": user_b_email, "password": "UserBPassword123!"})
        token_b = login_b.json()["access_token"]

    # User A uploads a document
    client_a = TestClient(app)
    client_a.headers["Authorization"] = f"Bearer {token_a}"

    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kinds [] /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 45 >> stream\n"
        b"BT /F1 12 Tf 100 700 Td (User A Confidential Strategy Plan) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000125 00000 n\n0000000223 00000 n\n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n318\n%%EOF"
    )

    upload_res = client_a.post(
        "/upload",
        files={"file": ("usera_private_doc.pdf", pdf_content, "application/pdf")}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["id"]

    # User A can access document
    get_res_a = client_a.get(f"/documents/{doc_id}")
    assert get_res_a.status_code == 200

    # User B attempts to access User A's document -> Must be 403 Forbidden!
    client_b = TestClient(app)
    client_b.headers["Authorization"] = f"Bearer {token_b}"

    get_res_b = client_b.get(f"/documents/{doc_id}")
    assert get_res_b.status_code == 403
    assert "access denied" in get_res_b.json()["detail"].lower()

    # User B attempts to ask questions about User A's document -> Must be 403 Forbidden!
    qa_res_b = client_b.post(
        f"/documents/{doc_id}/qa",
        json={"question": "What is the confidential strategy?"}
    )
    assert qa_res_b.status_code == 403

    # User B attempts to view Q&A history on User A's document -> Must be 403 Forbidden!
    history_res_b = client_b.get(f"/documents/{doc_id}/qa/history")
    assert history_res_b.status_code == 403


def test_audit_logs_contain_no_passwords_or_tokens():
    db = SessionLocal()
    logs = db.query(AuditLog).all()
    db.close()

    assert len(logs) > 0
    for log in logs:
        details_str = str(log.details or "").lower()
        assert "password123" not in details_str
        assert "bearer " not in details_str


def test_audit_logs_multi_tenant_isolation():
    """
    Ensure users can only view their own audit logs, not other tenants' activity.
    """
    # Create User A
    user_a_email = "audit_user_a@enterprise.com"
    res_a = client.post("/auth/register", json={"email": user_a_email, "password": "UserAPassword123!", "full_name": "Audit A"})
    token_a = res_a.json()["access_token"] if res_a.status_code == 201 else client.post("/auth/login", json={"email": user_a_email, "password": "UserAPassword123!"}).json()["access_token"]

    # Create User B
    user_b_email = "audit_user_b@enterprise.com"
    res_b = client.post("/auth/register", json={"email": user_b_email, "password": "UserBPassword123!", "full_name": "Audit B"})
    token_b = res_b.json()["access_token"] if res_b.status_code == 201 else client.post("/auth/login", json={"email": user_b_email, "password": "UserBPassword123!"}).json()["access_token"]

    client_a = TestClient(app)
    client_a.headers["Authorization"] = f"Bearer {token_a}"

    client_b = TestClient(app)
    client_b.headers["Authorization"] = f"Bearer {token_b}"

    # Query audit logs
    logs_b = client_b.get("/audit-logs").json()
    assert "logs" in logs_b
    # Verify no User A email or private events in User B logs
    for entry in logs_b["logs"]:
        assert user_a_email not in str(entry.get("details", ""))


def test_protected_endpoints_strictly_require_bearer_auth():
    """
    Verify complete authorization enforcement across all protected endpoints.
    """
    unauth = TestClient(app)

    # 1. Documents listing
    assert unauth.get("/documents").status_code == 401

    # 2. Upload endpoint
    assert unauth.post("/upload", files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")}).status_code == 401

    # 3. Document inspection
    assert unauth.get("/documents/1").status_code == 401

    # 4. Document Q&A
    assert unauth.post("/documents/1/qa", json={"question": "Test?"}).status_code == 401

    # 5. Document Q&A history
    assert unauth.get("/documents/1/qa/history").status_code == 401

    # 6. Audit logs
    assert unauth.get("/audit-logs").status_code == 401

    # 7. Authenticated user profile
    assert unauth.get("/auth/me").status_code == 401

