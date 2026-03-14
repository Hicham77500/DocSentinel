from datetime import datetime
import uuid

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "file_hash", name="uq_documents_tenant_file_hash"),
        CheckConstraint(
            "document_type IS NULL OR document_type IN "
            "('invoice', 'quote', 'certificate', 'rib', 'kbis', 'supplier_document', 'unknown')",
            name="ck_documents_document_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_bundles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raw_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    bronze_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    silver_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    gold_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fraud_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant = relationship("Tenant", back_populates="documents")
    bundle = relationship("DocumentBundle", back_populates="documents")
    usage_events = relationship("UsageEvent", back_populates="document")
