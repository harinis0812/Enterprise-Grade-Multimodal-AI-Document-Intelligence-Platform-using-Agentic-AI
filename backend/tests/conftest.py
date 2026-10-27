import os
import tempfile
from pathlib import Path

# Ensure cache dirs use writable workspace / temp directory
_paddlex_dir = Path(__file__).resolve().parent.parent.parent / ".paddlex"
_paddlex_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(_paddlex_dir))
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

import pytest
from sqlalchemy.orm import Session

from backend.database.database import SessionLocal
from backend.database.init_db import init_database
from backend.database.models import User
from backend.core.security import hash_password, create_access_token


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Initializes database and provides default authentication headers
    so existing document tests continue passing without regression.
    """
    init_database()

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "testuser@docuai.enterprise").first()
        if not user:
            user = User(
                email="testuser@docuai.enterprise",
                hashed_password=hash_password("EnterprisePass123!"),
                full_name="Enterprise Test User",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        token = create_access_token(data={"sub": str(user.id), "email": user.email})

        # Inject auth header into test_document.client across any module naming
        import sys
        for mod_name in ["backend.tests.test_document", "test_document"]:
            if mod_name in sys.modules and hasattr(sys.modules[mod_name], "client"):
                sys.modules[mod_name].client.headers["Authorization"] = f"Bearer {token}"

        yield {"user": user, "token": token}
    finally:
        db.close()


@pytest.fixture(autouse=True)
def apply_auth_headers_per_test(setup_test_environment):
    import sys
    token = setup_test_environment["token"]
    for mod_name in ["backend.tests.test_document", "test_document"]:
        if mod_name in sys.modules and hasattr(sys.modules[mod_name], "client"):
            sys.modules[mod_name].client.headers["Authorization"] = f"Bearer {token}"
