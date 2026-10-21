from sqlalchemy import inspect, text
from backend.database.database import Base, engine
from backend.database.models import Document, User, QAHistory, AuditLog


def init_database():
    """
    Initialize database tables and run safe, non-destructive schema migrations.
    Preserves all existing document records.
    """
    Base.metadata.create_all(bind=engine)

    # Safe migration: add missing columns to existing documents table if needed
    try:
        inspector = inspect(engine)
        columns = [col["name"] for col in inspector.get_columns("documents")]

        with engine.connect() as conn:
            if "user_id" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id)"))
                conn.commit()
                print("[Database Migration] Added 'user_id' column to documents table.")

            if "page_count" not in columns:
                conn.execute(text("ALTER TABLE documents ADD COLUMN page_count INTEGER DEFAULT 1"))
                conn.commit()
                print("[Database Migration] Added 'page_count' column to documents table.")

    except Exception as e:
        print(f"[Database Migration] Warning during migration check: {e}")
