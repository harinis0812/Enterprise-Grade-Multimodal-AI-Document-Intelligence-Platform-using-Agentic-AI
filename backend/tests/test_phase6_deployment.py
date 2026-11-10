import logging
import uuid
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_request_id_generated_automatically(setup_test_environment):
    """Verify that a unique X-Request-ID is generated and returned if omitted by client."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    # Check that it's a valid UUID
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


def test_request_id_propagated_when_valid(setup_test_environment):
    """Verify that a valid client-supplied X-Request-ID is retained in the response."""
    custom_id = "trace-corp-12345-abcde"
    response = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_request_id_sanitized_when_invalid(setup_test_environment):
    """Verify that malicious/invalid client-supplied headers are sanitized to a secure UUID."""
    malicious_id = "invalid-id-with-bad-chars<script>alert(1)</script>"
    response = client.get("/health", headers={"X-Request-ID": malicious_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") != malicious_id
    # Should generate a fresh valid UUID
    req_id = response.headers["X-Request-ID"]
    parsed = uuid.UUID(req_id)
    assert str(parsed) == req_id


def test_structured_logging_never_leaks_sensitive_data(setup_test_environment, caplog):
    """
    Verify that structured request logging records request_id, method, path, and duration,
    and NEVER logs authorization tokens, passwords, or document body text.
    """
    caplog.set_level(logging.INFO, logger="docuai.request")
    secret_token = "secret-super-sensitive-jwt-token-12345"
    
    response = client.get(
        "/health",
        headers={
            "Authorization": f"Bearer {secret_token}",
            "X-Request-ID": "test-safe-logging-id"
        }
    )
    assert response.status_code == 200
    
    # Check log records
    matching_records = [
        rec for rec in caplog.records
        if "test-safe-logging-id" in rec.getMessage()
    ]
    assert len(matching_records) >= 1
    log_msg = matching_records[0].getMessage()
    
    # Must contain structured timing and request metadata
    assert "request_id=test-safe-logging-id" in log_msg
    assert "method=GET" in log_msg
    assert "path=/health" in log_msg
    assert "status_code=200" in log_msg
    assert "duration_ms=" in log_msg
    
    # Must NEVER contain the token or sensitive headers
    assert secret_token not in log_msg
    assert "Authorization" not in log_msg
    assert "Bearer" not in log_msg


def test_health_check_database_connectivity(setup_test_environment):
    """Verify that /health reports healthy status and verifies DB connection."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "DocuAI"
