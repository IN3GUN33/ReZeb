"""Initial schema: auth, control, pto, ntd, audit

Revision ID: 0001
Revises:
Create Date: 2026-04-27 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 3072


def upgrade() -> None:
    # Enable extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin")

    # Create schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")
    op.execute("CREATE SCHEMA IF NOT EXISTS control")
    op.execute("CREATE SCHEMA IF NOT EXISTS pto")
    op.execute("CREATE SCHEMA IF NOT EXISTS ntd")
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # ─── auth.users ──────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("daily_control_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_pto_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="auth",
    )
    op.create_index("ix_auth_users_email", "users", ["email"], schema="auth", unique=True)

    # ─── auth.refresh_tokens ─────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="auth",
    )
    op.create_index("ix_auth_refresh_tokens_hash", "refresh_tokens", ["token_hash"], schema="auth")

    # ─── control.sessions ────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("construction_type", sa.String(100), nullable=True),
        sa.Column("construction_type_confidence", sa.Float(), nullable=True),
        sa.Column("verdict", postgresql.JSONB(), nullable=True),
        sa.Column("verdict_model", sa.String(100), nullable=True),
        sa.Column("escalated", sa.Boolean(), server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost_rub", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="control",
    )
    op.create_index("ix_control_sessions_user_id", "sessions", ["user_id"], schema="control")

    # ─── control.photos ──────────────────────────────────────────────────────
    op.create_table(
        "photos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("control.sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("is_blurry", sa.Boolean(), server_default="false"),
        sa.Column("sharpness_score", sa.Float(), nullable=True),
        sa.Column("has_aruco_marker", sa.Boolean(), server_default="false"),
        sa.Column("aruco_scale_mm_per_px", sa.Float(), nullable=True),
        sa.Column("yolo_detections", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="control",
    )

    # ─── control.defects ─────────────────────────────────────────────────────
    op.create_table(
        "defects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("control.sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("photo_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("control.photos.id"), nullable=True),
        sa.Column("defect_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("measurement_mm", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("ntd_references", postgresql.JSONB(), server_default="[]"),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="control",
    )

    # ─── pto.registry ────────────────────────────────────────────────────────
    op.create_table(
        "registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalized", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("category", sa.String(200), nullable=True),
        sa.Column("manufacturer", sa.String(200), nullable=True),
        sa.Column("extra", postgresql.JSONB(), server_default="{}"),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("fts_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="pto",
    )
    op.create_index("ix_pto_registry_code", "registry", ["code"], schema="pto")
    op.create_index("ix_pto_registry_fts", "registry", ["fts_vector"],
                    schema="pto", postgresql_using="gin")

    # ─── pto.synonyms ────────────────────────────────────────────────────────
    op.create_table(
        "synonyms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("registry_item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("pto.registry.id", ondelete="CASCADE"), nullable=False),
        sa.Column("synonym", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="pto",
    )
    op.create_unique_constraint("uq_synonym", "synonyms",
                                ["registry_item_id", "synonym"], schema="pto")

    # ─── pto.queries ─────────────────────────────────────────────────────────
    op.create_table(
        "queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("auth.users.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("results", postgresql.JSONB(), server_default="[]"),
        sa.Column("best_match_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("pto.registry.id"), nullable=True),
        sa.Column("match_status", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("cached_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost_rub", sa.Float(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="pto",
    )
    op.create_index("ix_pto_queries_user_id", "queries", ["user_id"], schema="pto")

    # ─── ntd.documents ───────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("effective_date", sa.String(50), nullable=True),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        schema="ntd",
    )
    op.create_index("ix_ntd_documents_code", "documents", ["code"], schema="ntd", unique=True)

    # ─── ntd.clauses ─────────────────────────────────────────────────────────
    op.create_table(
        "clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ntd.documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clause_number", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("fts_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="ntd",
    )
    op.create_index("ix_ntd_clauses_document_id", "clauses", ["document_id"], schema="ntd")
    op.create_index("ix_ntd_clauses_fts", "clauses", ["fts_vector"],
                    schema="ntd", postgresql_using="gin")
    op.create_index(
        "ix_ntd_clauses_embedding", "clauses", ["embedding"],
        schema="ntd", postgresql_using="ivfflat",
        postgresql_with={"lists": 50},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # ─── audit.events ────────────────────────────────────────────────────────
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(100), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        schema="audit",
    )
    op.create_index("ix_audit_events_user_id", "events", ["user_id"], schema="audit")
    op.create_index("ix_audit_events_entity", "events", ["entity_type", "entity_id"], schema="audit")
    op.create_index("ix_audit_events_created_at", "events", ["created_at"], schema="audit")

    # Append-only trigger for audit.events
    op.execute("""
        CREATE OR REPLACE FUNCTION audit.prevent_update_delete()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'audit.events is append-only'; END; $$
    """)
    op.execute("""
        CREATE TRIGGER audit_events_immutable
        BEFORE UPDATE OR DELETE ON audit.events
        FOR EACH ROW EXECUTE FUNCTION audit.prevent_update_delete()
    """)

    # FTS update trigger for pto.registry
    op.execute("""
        CREATE OR REPLACE FUNCTION pto.update_registry_fts()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            NEW.fts_vector := to_tsvector('russian', coalesce(NEW.name, '') || ' ' || coalesce(NEW.name_normalized, ''));
            RETURN NEW;
        END; $$
    """)
    op.execute("""
        CREATE TRIGGER trg_registry_fts
        BEFORE INSERT OR UPDATE ON pto.registry
        FOR EACH ROW EXECUTE FUNCTION pto.update_registry_fts()
    """)


def downgrade() -> None:
    op.drop_table("events", schema="audit")
    op.drop_table("clauses", schema="ntd")
    op.drop_table("documents", schema="ntd")
    op.drop_table("queries", schema="pto")
    op.drop_table("synonyms", schema="pto")
    op.drop_table("registry", schema="pto")
    op.drop_table("defects", schema="control")
    op.drop_table("photos", schema="control")
    op.drop_table("sessions", schema="control")
    op.drop_table("refresh_tokens", schema="auth")
    op.drop_table("users", schema="auth")
    op.execute("DROP SCHEMA IF EXISTS audit")
    op.execute("DROP SCHEMA IF EXISTS ntd")
    op.execute("DROP SCHEMA IF EXISTS pto")
    op.execute("DROP SCHEMA IF EXISTS control")
    op.execute("DROP SCHEMA IF EXISTS auth")
