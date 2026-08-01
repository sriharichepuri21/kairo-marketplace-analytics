import uuid
from datetime import datetime
from typing import Any, TypeAlias

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

JsonValue: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None

JSON_TYPE = JSON().with_variant(
    JSONB(),
    "postgresql",
)


class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"

    __table_args__ = (
        CheckConstraint(
            ("status IN ('running', 'passed', 'warning', 'failed')"),
            name="data_quality_run_status_valid",
        ),
        CheckConstraint(
            (
                "total_checks >= 0 "
                "AND passed_checks >= 0 "
                "AND warning_checks >= 0 "
                "AND failed_checks >= 0"
            ),
            name="data_quality_run_counts_nonnegative",
        ),
        CheckConstraint(
            ("passed_checks + warning_checks + failed_checks <= total_checks"),
            name="data_quality_run_counts_reconcile",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="operational",
        server_default="operational",
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        server_default="running",
        index=True,
    )

    triggered_by: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual",
        server_default="manual",
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    total_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    passed_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    warning_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    failed_checks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    run_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON_TYPE,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
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

    checks: Mapped[list["DataQualityCheckResult"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DataQualityCheckResult(Base):
    __tablename__ = "data_quality_check_results"

    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "check_name",
            name="one_result_per_quality_run_check",
        ),
        CheckConstraint(
            ("status IN ('passed', 'warning', 'failed')"),
            name="data_quality_check_status_valid",
        ),
        CheckConstraint(
            ("severity IN ('info', 'warning', 'error')"),
            name="data_quality_check_severity_valid",
        ),
        CheckConstraint(
            "failure_count >= 0",
            name="data_quality_failure_count_nonnegative",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "data_quality_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    check_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    check_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    check_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="operational_sql",
        server_default="operational_sql",
        index=True,
    )

    target_name: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="error",
        server_default="error",
    )

    observed_value: Mapped[JsonValue] = mapped_column(
        JSON_TYPE,
        nullable=True,
    )

    expected_value: Mapped[JsonValue] = mapped_column(
        JSON_TYPE,
        nullable=True,
    )

    failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    details: Mapped[dict[str, Any]] = mapped_column(
        JSON_TYPE,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    run: Mapped["DataQualityRun"] = relationship(
        back_populates="checks",
    )
