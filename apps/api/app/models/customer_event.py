import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CustomerEvent(Base):
    __tablename__ = "customer_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'product_view', "
                "'product_search', "
                "'add_to_cart', "
                "'remove_from_cart', "
                "'checkout_started', "
                "'order_placed'"
                ")"
            ),
            name="event_type_valid",
        ),
        CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL",
            name="customer_or_session_required",
        ),
        Index(
            "ix_customer_events_user_occurred_at",
            "user_id",
            "occurred_at",
        ),
        Index(
            "ix_customer_events_session_occurred_at",
            "session_id",
            "occurred_at",
        ),
        Index(
            "ix_customer_events_type_occurred_at",
            "event_type",
            "occurred_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    session_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    properties: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
