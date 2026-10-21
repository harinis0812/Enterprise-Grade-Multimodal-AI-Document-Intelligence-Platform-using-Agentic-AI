from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code in [200, 404]


def test_documents_endpoint():
    response = client.get("/documents")

    assert response.status_code == 200


def test_document_not_found():
    response = client.get("/documents/999999")

    assert response.status_code == 404

def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "DocuAI"


def test_upload_unsupported_format():
    response = client.post(
        "/upload",
        files={"file": ("test.txt", b"Unsupported content", "text/plain")}
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_empty_file():
    response = client.post(
        "/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_upload_oversized_file():
    big_content = b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/upload",
        files={"file": ("large.pdf", big_content, "application/pdf")}
    )
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]


def test_upload_corrupt_file():
    corrupt_pdf = b"%PDF-1.4 corrupt header without valid structure"
    response = client.post(
        "/upload",
        files={"file": ("corrupt.pdf", corrupt_pdf, "application/pdf")}
    )
    assert response.status_code in [400, 500]


def test_upload_and_verify_supervisor_persistence():
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kinds [] /Count 1 /Kids [3 0 R] >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 100 700 Td (Employee Report Harini AI ML) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000056 00000 n\n0000000125 00000 n\n0000000223 00000 n\n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n328\n%%EOF"
    )
    response = client.post(
        "/upload",
        files={"file": ("sample_employee.pdf", pdf_content, "application/pdf")}
    )
    assert response.status_code == 200
    doc_id = response.json()["id"]

    detail_res = client.get(f"/documents/{doc_id}")
    assert detail_res.status_code == 200
    doc_data = detail_res.json()
    assert doc_data["id"] == doc_id
    assert "analysis" in doc_data
    assert "supervisor_decision" in doc_data["analysis"] or "supervisor_decision" in str(doc_data["analysis"])