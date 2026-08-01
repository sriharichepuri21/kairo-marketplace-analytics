import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.inventory import Inventory
    from app.models.product_image import ProductImage


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="price_nonnegative"),
        CheckConstraint(
            "cost IS NULL OR cost >= 0",
            name="cost_nonnegative",
        ),
        CheckConstraint(
            "review_count >= 0",
            name="review_count_nonnegative",
        ),
        CheckConstraint(
            ("return_rate IS NULL OR (return_rate >= 0 AND return_rate <= 1)"),
            name="return_rate_valid",
        ),
        CheckConstraint(
            "discount_price IS NULL OR discount_price >= 0",
            name="discount_price_nonnegative",
        ),
        CheckConstraint(
            "discount_price IS NULL OR discount_price <= price",
            name="discount_not_above_price",
        ),
        CheckConstraint(
            "average_rating >= 0 AND average_rating <= 5",
            name="rating_between_zero_and_five",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    source_product_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        unique=True,
        index=True,
    )

    sku: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
    )

    seller_source_id: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    subcategory: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(260),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    cost: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 3),
        nullable=True,
    )

    review_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    return_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 6),
        nullable=True,
    )

    launch_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    discount_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )
    average_rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
        index=True,
    )

    is_demo: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=false(),
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

    category: Mapped["Category"] = relationship(
        back_populates="products",
    )
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.display_order",
    )
    inventory: Mapped["Inventory | None"] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        uselist=False,
    )
