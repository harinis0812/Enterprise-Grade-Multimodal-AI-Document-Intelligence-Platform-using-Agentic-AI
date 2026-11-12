import os
from pathlib import Path
from typing import List, Optional

try:
    from dotenv import load_dotenv
    # Load .env from project root if it exists
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass


def _get_validated_jwt_secret() -> str:
    """
    Validates and retrieves the JWT secret key from the environment.
    Enforces a minimum length of 32 characters and strictly rejects
    missing values or known insecure development placeholders.
    Never prints or leaks the secret value in logs or error messages.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret or not secret.strip():
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: The 'JWT_SECRET_KEY' environment variable "
            "is not set. A cryptographically secure secret key of at least 32 characters is required "
            "to start the application. Hardcoded development fallback secrets are strictly prohibited."
        )

    secret = secret.strip()
    insecure_placeholders = {
        "docuai-enterprise-secret-key-development-mode-only-32bytes",
        "change-this-to-a-secure-random-secret-in-production",
        "secret",
        "jwt_secret",
        "changeme",
        "password",
        "admin"
    }

    if secret.lower() in insecure_placeholders:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: An insecure, default, or placeholder 'JWT_SECRET_KEY' "
            "is configured. Please supply a cryptographically strong, unique secret key (at least 32 characters)."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"CRITICAL SECURITY CONFIGURATION ERROR: 'JWT_SECRET_KEY' is too short ({len(secret)} characters). "
            "To prevent signature forgery attacks, the secret key must be at least 32 characters (256 bits)."
        )

    return secret


def _get_validated_encryption_key() -> str:
    """
    Validates and retrieves the encryption key for sensitive document & Q&A fields.
    Enforces a valid 32-byte url-safe base64 Fernet key distinct from JWT_SECRET_KEY.
    Never prints or leaks the key in logs or error messages.
    """
    enc_key = os.getenv("DOCUMENT_ENCRYPTION_KEY")
    if not enc_key or not enc_key.strip():
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: The 'DOCUMENT_ENCRYPTION_KEY' environment variable "
            "is not set. A dedicated Fernet encryption key is required for authenticated field-level encryption at rest."
        )

    enc_key = enc_key.strip()
    jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()

    if enc_key == jwt_secret:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: 'DOCUMENT_ENCRYPTION_KEY' must be distinct from 'JWT_SECRET_KEY'."
        )

    insecure_placeholders = {
        "change-this-to-a-valid-fernet-key-32-base64-bytes=",
        "changeme",
        "password",
        "secret",
        "admin"
    }
    if enc_key.lower() in insecure_placeholders:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: An insecure placeholder 'DOCUMENT_ENCRYPTION_KEY' is configured."
        )

    # Validate that it is a valid Fernet key
    from cryptography.fernet import Fernet
    try:
        Fernet(enc_key.encode("utf-8"))
    except Exception as e:
        raise RuntimeError(
            "CRITICAL SECURITY CONFIGURATION ERROR: 'DOCUMENT_ENCRYPTION_KEY' is not a valid 32-byte urlsafe base64 key: "
            f"{e}"
        )

    return enc_key


class Settings:
    PROJECT_NAME: str = "Enterprise Grade Multimodal AI Document Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Database
    @property
    def DATABASE_URL(self) -> str:
        url = os.getenv("DATABASE_URL", "sqlite:///./docuai.db")
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # JWT / Security Settings
    # Enforces non-empty, cryptographically strong key from environment (no hardcoded fallback)
    @property
    def JWT_SECRET_KEY(self) -> str:
        return _get_validated_jwt_secret()

    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))

    # Authenticated Encryption at Rest Settings
    @property
    def DOCUMENT_ENCRYPTION_KEY(self) -> str:
        return _get_validated_encryption_key()

    # Rate Limiting Settings
    LOGIN_RATE_LIMIT: str = os.getenv("LOGIN_RATE_LIMIT", "5/minute")
    REGISTER_RATE_LIMIT: str = os.getenv("REGISTER_RATE_LIMIT", "3/minute")

    # Generative AI & Q&A Settings
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    QA_TOP_K: int = int(os.getenv("QA_TOP_K", "5"))
    QA_CHUNK_SIZE: int = int(os.getenv("QA_CHUNK_SIZE", "900"))
    QA_CHUNK_OVERLAP: int = int(os.getenv("QA_CHUNK_OVERLAP", "150"))

    # CORS settings
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]


settings = Settings()
