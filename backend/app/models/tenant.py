from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    monthly_document_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    monthly_api_quota: Mapped[int] = mapped_column(Integer, nullable=False, default=10000)
    current_subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "subscriptions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_tenants_current_subscription_id",
        ),
        nullable=True,
        index=True,
    )
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

    api_keys = relationship("ApiKey", back_populates="tenant", cascade="all, delete-orphan")
    document_bundles = relationship("DocumentBundle", back_populates="tenant", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="tenant", cascade="all, delete-orphan")
    usage_events = relationship("UsageEvent", back_populates="tenant", cascade="all, delete-orphan")
    subscriptions = relationship(
        "Subscription",
        back_populates="tenant",
        cascade="all, delete-orphan",
        foreign_keys="Subscription.tenant_id",
    )
    current_subscription = relationship(
        "Subscription",
        foreign_keys=[current_subscription_id],
        post_update=True,
    )
