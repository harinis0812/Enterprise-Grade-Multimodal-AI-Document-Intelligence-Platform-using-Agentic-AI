import os
from typing import List


class Settings:
    PROJECT_NAME: str = "Enterprise Grade Multimodal AI Document Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./docuai.db")

    # JWT / Security Settings
    # Reads from environment variable JWT_SECRET_KEY.
    # In production, a cryptographically secure random key MUST be provided in the environment.
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "docuai-enterprise-secret-key-development-mode-only-32bytes"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # CORS settings
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:3000,http://127.0.0.1:3000,http://localhost:8080,http://127.0.0.1:8080"
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]


settings = Settings()
