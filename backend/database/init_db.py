from sqlalchemy import inspect, text
from backend.database.database import Base, engine
from backend.database.models import Document, User, QAHistory, AuditLog, RevokedToken, MultiDocQAHistory
from backend.database.migrate_encryption import migrate_data_to_encrypted


def init_database():
    """
    Initialize database tables and run safe, non-destructive schema migrations.
    Preserves all existing user, document, QA, and audit records.
    """
    Base.metadata.create_all(bind=engine)

    try:
        inspector = inspect(engine)

        # 1. Safe migration: check users table columns
        user_cols = [col["name"] for col in inspector.get_columns("users")]
        with engine.connect() as conn:
            if "role" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
                conn.commit()
                print("[Database Migration] Added 'role' column to users table.")

        # 2. Safe migration: check documents table columns
        doc_cols = [col["name"] for col in inspector.get_columns("documents")]
        with engine.connect() as conn:
            if "user_id" not in doc_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                conn.commit()
                print("[Database Migration] Added 'user_id' column to documents table.")

            if "page_count" not in doc_cols:
                conn.execute(text("ALTER TABLE documents ADD COLUMN page_count INTEGER DEFAULT 1"))
                conn.commit()
                print("[Database Migration] Added 'page_count' column to documents table.")

        # 3. Safe migration: encrypt any legacy plaintext records at rest
        migrate_data_to_encrypted()

    except Exception as e:
        print(f"[Database Migration] Warning during migration check: {e}")
