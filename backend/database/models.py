from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from backend.database.database import Base


class Document(Base):

    __tablename__ = "documents"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    document_type = Column(
        String(100),
        nullable=True
    )

    status = Column(
        String(50),
        default="uploaded"
    )

    extracted_text = Column(
        Text,
        nullable=True
    )

    analysis = Column(
        Text,
        nullable=True
    )

    agent_trace = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )
