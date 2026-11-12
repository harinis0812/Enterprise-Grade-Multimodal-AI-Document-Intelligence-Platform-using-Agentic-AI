import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./docuai.db"
)

# Normalize Render/Heroku legacy postgres:// URL prefix to postgresql:// for SQLAlchemy 2.0+
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


connect_args = {}

engine_kwargs = {
    "pool_pre_ping": True
}


if DATABASE_URL.startswith("sqlite"):

    connect_args = {
        "check_same_thread": False
    }

else:

    engine_kwargs.update(
        {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30
        }
    )


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


Base = declarative_base()


def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
