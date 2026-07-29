import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.product import Product


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            (
                "status IN ("
                "'pending', "
                "'confirmed', "
                "'processing', "
                "'shipped', "
                "'delivered', "
                "'cancelled'"
                ")"
            ),
            name="status_valid",
        ),
        CheckConstraint(
            ("payment_status IN ('pending', 'paid', 'failed', 'refunded')"),
            name="payment_status_valid",
        ),
        CheckConstraint(
            "subtotal >= 0",
            name="subtotal_nonnegative",
        ),
        CheckConstraint(
            "shipping_amount >= 0",
            name="shipping_amount_nonnegative",
        ),
        CheckConstraint(
            "tax_amount >= 0",
            name="tax_amount_nonnegative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="total_amount_nonnegative",
        ),
        CheckConstraint(
            ("total_amount = subtotal + shipping_amount + tax_amount"),
            name="total_matches_components",
        ),
        CheckConstraint(
            "char_length(currency_code) = 3",
            name="currency_code_length",
        ),
        CheckConstraint(
            "char_length(shipping_country_code) = 2",
            name="shipping_country_code_length",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "addresses.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    payment_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
    )

    currency_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="INR",
        server_default="INR",
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    shipping_full_name: Mapped[str] = mapped_column(
        String(160),
        nullable=False,
    )

    shipping_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    shipping_address_line_1: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    shipping_address_line_2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    shipping_city: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    shipping_state: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    shipping_postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    shipping_country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
    )

    customer_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.created_at",
    )

    status_history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        UniqueConstraint(
            "order_id",
            "product_id",
            name="one_product_per_order",
        ),
        CheckConstraint(
            "quantity > 0",
            name="quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0",
            name="unit_price_nonnegative",
        ),
        CheckConstraint(
            "line_total >= 0",
            name="line_total_nonnegative",
        ),
        CheckConstraint(
            "line_total = unit_price * quantity",
            name="line_total_matches_quantity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
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

    product_name: Mapped[str] = mapped_column(
        String(240),
        nullable=False,
    )

    product_slug: Mapped[str] = mapped_column(
        String(260),
        nullable=False,
    )

    product_brand: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped["Order"] = relationship(
        back_populates="items",
    )

    product: Mapped["Product | None"] = relationship()


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    __table_args__ = (
        CheckConstraint(
            (
                "status IN ("
                "'pending', "
                "'confirmed', "
                "'processing', "
                "'shipped', "
                "'delivered', "
                "'cancelled'"
                ")"
            ),
            name="status_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped["Order"] = relationship(
        back_populates="status_history",
    )
