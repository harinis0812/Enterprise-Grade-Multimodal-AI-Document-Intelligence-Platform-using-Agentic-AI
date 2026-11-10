from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, TypeDecorator
from sqlalchemy.orm import relationship

from backend.core.encryption import encrypt_text, decrypt_text
from backend.database.database import Base


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy TypeDecorator providing transparent field-level encryption at rest.
    Encrypts sensitive data with Fernet authenticated encryption before writing to the database,
    and decrypts back to plaintext when read into application memory.
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_text(value)


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

    role = Column(
        String(50),
        default="user",
        nullable=False
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
        EncryptedText,
        nullable=True
    )

    analysis = Column(
        EncryptedText,
        nullable=True
    )

    agent_trace = Column(
        EncryptedText,
        nullable=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
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
        EncryptedText,
        nullable=False
    )

    answer = Column(
        EncryptedText,
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


class MultiDocQAHistory(Base):
    __tablename__ = "multi_doc_qa_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    document_ids = Column(
        String(255),
        nullable=False
    )

    question = Column(
        EncryptedText,
        nullable=False
    )

    answer = Column(
        EncryptedText,
        nullable=False
    )

    citations = Column(
        Text,
        nullable=True
    )

    documents_consulted = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    user = relationship(
        "User"
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


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    jti = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )

    token_type = Column(
        String(50),
        default="access",
        nullable=False
    )

    expires_at = Column(
        DateTime,
        nullable=False,
        index=True
    )

    revoked_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
