"""Initial EOC provenance and source-health schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-27
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "canonical_records",
        sa.Column("id", sa.String(length=300), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("authority_level", sa.String(length=40), nullable=False),
        sa.Column("source_record_id", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("geography", sa.JSON(), nullable=False),
        sa.Column(
            "geom",
            Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("zip_scope", sa.JSON(), nullable=False),
        sa.Column("raw_snapshot_hash", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_id", "source_record_id", name="uq_record_source_identity"
        ),
    )
    op.create_index(
        "ix_records_category_active",
        "canonical_records",
        ["category", "expires_at", "stale"],
    )
    op.create_index("ix_records_retrieved_at", "canonical_records", ["retrieved_at"])
    op.create_index("ix_canonical_records_source_id", "canonical_records", ["source_id"])
    op.create_index(
        "ix_canonical_records_geom",
        "canonical_records",
        ["geom"],
        postgresql_using="gist",
    )
    op.create_table(
        "source_health",
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("last_attempt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_authoritative_observation", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_known_good", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("authority_level", sa.String(length=40), nullable=False),
        sa.Column("circuit_breaker_state", sa.String(length=20), nullable=False),
        sa.Column("circuit_open_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_table(
        "raw_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("byte_count", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "sha256", name="uq_snapshot_source_hash"),
    )
    op.create_index(
        "ix_snapshots_source_retrieved",
        "raw_snapshots",
        ["source_id", "retrieved_at"],
    )


def downgrade() -> None:
    op.drop_table("raw_snapshots")
    op.drop_table("source_health")
    op.drop_table("canonical_records")
