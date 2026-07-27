from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CanonicalRecordRow(Base):
    __tablename__ = "canonical_records"
    __table_args__ = (
        UniqueConstraint("source_id", "source_record_id", name="uq_record_source_identity"),
        Index("ix_records_category_active", "category", "expires_at", "stale"),
        Index("ix_records_retrieved_at", "retrieved_at"),
    )

    id: Mapped[str] = mapped_column(String(300), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(120), index=True)
    source_name: Mapped[str] = mapped_column(String(240))
    source_type: Mapped[str] = mapped_column(String(40))
    authority_level: Mapped[str] = mapped_column(String(40))
    source_record_id: Mapped[str] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(120), index=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
    stale_reason: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    geography: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    geom: Mapped[WKBElement | None] = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=False),
        nullable=True,
    )
    zip_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_snapshot_hash: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class SourceHealthRow(Base):
    __tablename__ = "source_health"

    source_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(240))
    state: Mapped[str] = mapped_column(String(40))
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_authoritative_observation: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    poll_interval_seconds: Mapped[int] = mapped_column(Integer)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_known_good: Mapped[bool] = mapped_column(Boolean, default=False)
    authority_level: Mapped[str] = mapped_column(String(40))
    circuit_breaker_state: Mapped[str] = mapped_column(String(20), default="closed")
    circuit_open_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    message: Mapped[str | None] = mapped_column(Text)


class RawSnapshotRow(Base):
    __tablename__ = "raw_snapshots"
    __table_args__ = (
        UniqueConstraint("source_id", "sha256", name="uq_snapshot_source_hash"),
        Index("ix_snapshots_source_retrieved", "source_id", "retrieved_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(120))
    sha256: Mapped[str] = mapped_column(String(64))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_type: Mapped[str] = mapped_column(String(120))
    byte_count: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(Text)
