from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    full_name = Column(
        String(255),
        nullable=True
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    documents = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan"
    )

    qa_records = relationship(
        "QAHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )


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

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    page_count = Column(
        Integer,
        default=1,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    # Relationships
    owner = relationship(
        "User",
        back_populates="documents"
    )

    qa_records = relationship(
        "QAHistory",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class QAHistory(Base):
    __tablename__ = "qa_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    document_id = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    question = Column(
        Text,
        nullable=False
    )

    answer = Column(
        Text,
        nullable=False
    )

    citations = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # Relationships
    document = relationship(
        "Document",
        back_populates="qa_records"
    )

    user = relationship(
        "User",
        back_populates="qa_records"
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        nullable=True,
        index=True
    )

    event_type = Column(
        String(100),
        nullable=False,
        index=True
    )

    ip_address = Column(
        String(100),
        nullable=True
    )

    details = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
