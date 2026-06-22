import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, Index, Enum as SAEnum,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from nozzle.domain.enums import (
    AlertStatus, ClusterStatus, Decision, FeedbackSource,
    SourceType, SourceStatus, UserTier
)


class Base(DeclarativeBase):
    pass


def utcnow():
    return datetime.utcnow()


def new_uuid():
    return uuid.uuid4()


# ============================================================
# Source
# ============================================================

class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[SourceType] = mapped_column(SAEnum(SourceType), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[SourceStatus] = mapped_column(
        SAEnum(SourceStatus), default=SourceStatus.ACTIVE
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship(back_populates="source", lazy="selectin")

    __table_args__ = (
        Index("ix_sources_type_status", "type", "status"),
    )


# ============================================================
# User
# ============================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    tier: Mapped[UserTier] = mapped_column(SAEnum(UserTier), default=UserTier.FREE)
    alert_limit_daily: Mapped[int] = mapped_column(Integer, default=1000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="user", lazy="selectin")


# ============================================================
# Alert
# ============================================================

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(
        String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str | None] = mapped_column(String(512))
    severity: Mapped[int] = mapped_column(Integer, default=0)
    agent_name: Mapped[str | None] = mapped_column(String(255))
    agent_id: Mapped[str | None] = mapped_column(String(128))
    source_ip: Mapped[str | None] = mapped_column(INET)
    source_hostname: Mapped[str | None] = mapped_column(String(255))
    destination_ip: Mapped[str | None] = mapped_column(INET)
    description: Mapped[str] = mapped_column(Text, default="")
    full_log: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[AlertStatus] = mapped_column(SAEnum(AlertStatus), default=AlertStatus.NEW)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36), ForeignKey("clusters.id", ondelete="SET NULL")
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    normalized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    source: Mapped["Source"] = relationship(back_populates="alerts")
    cluster: Mapped["Cluster | None"] = relationship(back_populates="alerts")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="alert", lazy="selectin")

    __table_args__ = (
        Index("ix_alerts_source_external", "source_id", "external_id", unique=True),
        Index("ix_alerts_received_at", "received_at"),
        Index("ix_alerts_rule_id", "rule_id"),
        Index("ix_alerts_agent_name", "agent_name"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_cluster_id", "cluster_id"),
        Index("ix_alerts_severity_received", "severity", "received_at"),
    )


# ============================================================
# Cluster
# ============================================================

class Cluster(Base):
    __tablename__ = "clusters"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    strategy: Mapped[str] = mapped_column(String(128), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ClusterStatus] = mapped_column(
        SAEnum(ClusterStatus), default=ClusterStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    alerts: Mapped[list["Alert"]] = relationship(back_populates="cluster", lazy="selectin")
    feedbacks: Mapped[list["Feedback"]] = relationship(back_populates="cluster", lazy="selectin")

    __table_args__ = (
        Index("ix_clusters_status", "status"),
        Index("ix_clusters_created_at", "created_at"),
    )


# ============================================================
# Feedback
# ============================================================

class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36), ForeignKey("alerts.id", ondelete="SET NULL")
    )
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(
        String(36), ForeignKey("clusters.id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    decision: Mapped[Decision] = mapped_column(SAEnum(Decision), nullable=False)
    source: Mapped[FeedbackSource] = mapped_column(
        SAEnum(FeedbackSource), default=FeedbackSource.EXPLICIT
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    extra_data: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Relationships
    alert: Mapped["Alert | None"] = relationship(back_populates="feedbacks")
    cluster: Mapped["Cluster | None"] = relationship(back_populates="feedbacks")
    user: Mapped["User"] = relationship(back_populates="feedbacks")

    __table_args__ = (
        Index("ix_feedback_alert_id", "alert_id"),
        Index("ix_feedback_cluster_id", "cluster_id"),
        Index("ix_feedback_user_id", "user_id"),
        Index("ix_feedback_created_at", "created_at"),
    )


# ============================================================
# Rule stats (materialized view candidate, for now — a table)
# ============================================================

class RuleStats(Base):
    """Агрегированная статистика по правилам."""
    __tablename__ = "rule_stats"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=new_uuid)
    source_id: Mapped[uuid.UUID] = mapped_column(
        String(36), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    external_rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str | None] = mapped_column(String(512))
    noise_score: Mapped[float] = mapped_column(Float, default=0.0)
    times_clustered: Mapped[int] = mapped_column(Integer, default=0)
    times_escalated: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        UniqueConstraint("source_id", "external_rule_id", name="uq_rule_stats_source_rule"),
        Index("ix_rule_stats_noise_score", "noise_score"),
    )