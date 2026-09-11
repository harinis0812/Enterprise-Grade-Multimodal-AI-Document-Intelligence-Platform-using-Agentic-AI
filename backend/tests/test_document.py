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