"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-14 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("monthly_document_quota", sa.Integer(), nullable=False),
        sa.Column("monthly_api_quota", sa.Integer(), nullable=False),
        sa.Column("current_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenants_current_subscription_id", "tenants", ["current_subscription_id"], unique=False)
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("monthly_price_cents", sa.Integer(), nullable=False),
        sa.Column("monthly_document_quota", sa.Integer(), nullable=False),
        sa.Column("monthly_api_quota", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_external_id", "subscriptions", ["external_id"], unique=True)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"], unique=False)
    op.create_foreign_key(
        "fk_tenants_current_subscription_id",
        "tenants",
        "subscriptions",
        ["current_subscription_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"], unique=False)

    op.create_table(
        "document_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("reference", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "reference", name="uq_document_bundles_tenant_reference"),
    )
    op.create_index("ix_document_bundles_reference", "document_bundles", ["reference"], unique=False)
    op.create_index("ix_document_bundles_tenant_id", "document_bundles", ["tenant_id"], unique=False)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_path", sa.String(length=1024), nullable=False),
        sa.Column("bronze_path", sa.String(length=1024), nullable=True),
        sa.Column("silver_path", sa.String(length=1024), nullable=True),
        sa.Column("gold_path", sa.String(length=1024), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=True),
        sa.Column("fraud_score", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "document_type IS NULL OR document_type IN "
            "('invoice', 'quote', 'certificate', 'rib', 'kbis', 'supplier_document', 'unknown')",
            name="ck_documents_document_type",
        ),
        sa.ForeignKeyConstraint(["bundle_id"], ["document_bundles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "file_hash", name="uq_documents_tenant_file_hash"),
    )
    op.create_index("ix_documents_bundle_id", "documents", ["bundle_id"], unique=False)
    op.create_index("ix_documents_file_hash", "documents", ["file_hash"], unique=False)
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"], unique=False)

    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("units", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_document_id", "usage_events", ["document_id"], unique=False)
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"], unique=False)
    op.create_index("ix_usage_events_tenant_id", "usage_events", ["tenant_id"], unique=False)

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "external_event_id",
            name="uq_billing_webhook_events_provider_external_event_id",
        ),
    )
    op.create_index("ix_billing_webhook_events_event_type", "billing_webhook_events", ["event_type"], unique=False)
    op.create_index("ix_billing_webhook_events_provider", "billing_webhook_events", ["provider"], unique=False)
    op.create_index("ix_billing_webhook_events_status", "billing_webhook_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_webhook_events_status", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_provider", table_name="billing_webhook_events")
    op.drop_index("ix_billing_webhook_events_event_type", table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")

    op.drop_index("ix_usage_events_tenant_id", table_name="usage_events")
    op.drop_index("ix_usage_events_event_type", table_name="usage_events")
    op.drop_index("ix_usage_events_document_id", table_name="usage_events")
    op.drop_table("usage_events")

    op.drop_index("ix_documents_tenant_id", table_name="documents")
    op.drop_index("ix_documents_file_hash", table_name="documents")
    op.drop_index("ix_documents_bundle_id", table_name="documents")
    op.drop_table("documents")

    op.drop_index("ix_document_bundles_tenant_id", table_name="document_bundles")
    op.drop_index("ix_document_bundles_reference", table_name="document_bundles")
    op.drop_table("document_bundles")

    op.drop_index("ix_api_keys_tenant_id", table_name="api_keys")
    op.drop_index("ix_api_keys_key_hash", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_constraint("fk_tenants_current_subscription_id", "tenants", type_="foreignkey")

    op.drop_index("ix_subscriptions_tenant_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_external_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_plans_code", table_name="plans")
    op.drop_table("plans")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_index("ix_tenants_current_subscription_id", table_name="tenants")
    op.drop_table("tenants")
