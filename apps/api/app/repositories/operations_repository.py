from __future__ import annotations

from datetime import (
    date,
    timedelta,
)
from typing import Any

from sqlalchemy import (
    and_,
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.inventory import Inventory
from app.models.order import (
    Order,
    OrderItem,
)
from app.models.product import Product

eligible_order_condition = and_(
    Order.payment_status == "paid",
    Order.status != "cancelled",
)


class OperationsRepository:
    @staticmethod
    def get_analysis_window(
        database: Session,
        *,
        days: int,
    ) -> tuple[
        date | None,
        date | None,
    ]:
        end_date = database.scalar(
            select(
                func.max(
                    func.date(
                        Order.created_at
                    )
                )
            ).where(
                eligible_order_condition
            )
        )

        if end_date is None:
            return None, None

        start_date = (
            end_date
            - timedelta(days=days - 1)
        )

        return start_date, end_date

    @classmethod
    def get_summary(
        cls,
        database: Session,
        *,
        days: int,
    ) -> tuple[
        date | None,
        date | None,
        Any | None,
        list[Any],
    ]:
        (
            start_date,
            end_date,
        ) = cls.get_analysis_window(
            database,
            days=days,
        )

        if (
            start_date is None
            or end_date is None
        ):
            return (
                start_date,
                end_date,
                None,
                [],
            )

        order_date = func.date(
            Order.created_at
        )

        period_condition = and_(
            order_date >= start_date,
            order_date <= end_date,
        )

        summary = database.execute(
            select(
                func.count(
                    Order.id
                ).label(
                    "total_orders"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                eligible_order_condition,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "eligible_orders"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status
                                == "delivered",
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "delivered_orders"
                ),

                func.coalesce(
                    func.sum(
                        case(
                            (
                                Order.status
                                == "cancelled",
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "cancelled_orders"
                ),

                func.count(
                    func.distinct(
                        case(
                            (
                                eligible_order_condition,
                                Order.user_id,
                            ),
                            else_=None,
                        )
                    )
                ).label(
                    "active_customers"
                ),
            )
            .where(
                period_condition
            )
        ).one()

        gross_sales = func.coalesce(
            func.sum(Order.total_amount),
            0,
        )

        currency_rows = database.execute(
            select(
                Order.currency_code.label(
                    "currency_code"
                ),

                func.count(
                    Order.id
                ).label(
                    "eligible_orders"
                ),

                gross_sales.label(
                    "gross_sales"
                ),

                func.coalesce(
                    func.avg(
                        Order.total_amount
                    ),
                    0,
                ).label(
                    "average_order_value"
                ),
            )
            .where(
                period_condition,
                eligible_order_condition,
            )
            .group_by(
                Order.currency_code
            )
            .order_by(
                gross_sales.desc(),
                Order.currency_code.asc(),
            )
        ).all()

        return (
            start_date,
            end_date,
            summary,
            list(currency_rows),
        )

    @classmethod
    def get_revenue_trend(
        cls,
        database: Session,
        *,
        days: int,
    ) -> tuple[
        date | None,
        date | None,
        list[Any],
    ]:
        (
            start_date,
            end_date,
        ) = cls.get_analysis_window(
            database,
            days=days,
        )

        if (
            start_date is None
            or end_date is None
        ):
            return (
                start_date,
                end_date,
                [],
            )

        order_date = func.date(
            Order.created_at
        )

        gross_sales = func.coalesce(
            func.sum(Order.total_amount),
            0,
        )

        rows = database.execute(
            select(
                order_date.label(
                    "order_date"
                ),

                Order.currency_code.label(
                    "currency_code"
                ),

                func.count(
                    Order.id
                ).label(
                    "eligible_orders"
                ),

                gross_sales.label(
                    "gross_sales"
                ),

                func.coalesce(
                    func.avg(
                        Order.total_amount
                    ),
                    0,
                ).label(
                    "average_order_value"
                ),
            )
            .where(
                eligible_order_condition,
                order_date >= start_date,
                order_date <= end_date,
            )
            .group_by(
                order_date,
                Order.currency_code,
            )
            .order_by(
                order_date.asc(),
                Order.currency_code.asc(),
            )
        ).all()

        return (
            start_date,
            end_date,
            list(rows),
        )

    @classmethod
    def get_order_statuses(
        cls,
        database: Session,
        *,
        days: int,
    ) -> tuple[
        date | None,
        date | None,
        list[Any],
    ]:
        (
            start_date,
            end_date,
        ) = cls.get_analysis_window(
            database,
            days=days,
        )

        if (
            start_date is None
            or end_date is None
        ):
            return (
                start_date,
                end_date,
                [],
            )

        order_date = func.date(
            Order.created_at
        )

        order_count = func.count(
            Order.id
        )

        rows = database.execute(
            select(
                Order.status.label(
                    "status"
                ),

                order_count.label(
                    "order_count"
                ),
            )
            .where(
                order_date >= start_date,
                order_date <= end_date,
            )
            .group_by(
                Order.status
            )
            .order_by(
                order_count.desc(),
                Order.status.asc(),
            )
        ).all()

        return (
            start_date,
            end_date,
            list(rows),
        )

    @classmethod
    def get_category_performance(
        cls,
        database: Session,
        *,
        days: int,
    ) -> tuple[
        date | None,
        date | None,
        list[Any],
        list[Any],
    ]:
        (
            start_date,
            end_date,
        ) = cls.get_analysis_window(
            database,
            days=days,
        )

        if (
            start_date is None
            or end_date is None
        ):
            return (
                start_date,
                end_date,
                [],
                [],
            )

        order_date = func.date(
            Order.created_at
        )

        common_filters = (
            eligible_order_condition,
            order_date >= start_date,
            order_date <= end_date,
        )

        category_rows = database.execute(
            select(
                Category.id.label(
                    "category_id"
                ),
                Category.name.label(
                    "category_name"
                ),
                func.count(
                    func.distinct(
                        Product.id
                    )
                ).label(
                    "products_sold"
                ),
                func.count(
                    func.distinct(
                        Order.id
                    )
                ).label(
                    "eligible_orders"
                ),
                func.coalesce(
                    func.sum(
                        OrderItem.quantity
                    ),
                    0,
                ).label(
                    "units_sold"
                ),
            )
            .select_from(Order)
            .join(
                OrderItem,
                OrderItem.order_id
                == Order.id,
            )
            .join(
                Product,
                Product.id
                == OrderItem.product_id,
            )
            .join(
                Category,
                Category.id
                == Product.category_id,
            )
            .where(*common_filters)
            .group_by(
                Category.id,
                Category.name,
            )
            .order_by(
                func.sum(
                    OrderItem.quantity
                ).desc(),
                Category.name.asc(),
            )
        ).all()

        category_currency_rows = (
            database.execute(
                select(
                    Category.id.label(
                        "category_id"
                    ),
                    Order.currency_code.label(
                        "currency_code"
                    ),
                    func.coalesce(
                        func.sum(
                            OrderItem.quantity
                        ),
                        0,
                    ).label(
                        "units_sold"
                    ),
                    func.coalesce(
                        func.sum(
                            OrderItem.line_total
                        ),
                        0,
                    ).label(
                        "gross_sales"
                    ),
                )
                .select_from(Order)
                .join(
                    OrderItem,
                    OrderItem.order_id
                    == Order.id,
                )
                .join(
                    Product,
                    Product.id
                    == OrderItem.product_id,
                )
                .join(
                    Category,
                    Category.id
                    == Product.category_id,
                )
                .where(*common_filters)
                .group_by(
                    Category.id,
                    Order.currency_code,
                )
                .order_by(
                    Category.id.asc(),
                    Order.currency_code.asc(),
                )
            ).all()
        )

        return (
            start_date,
            end_date,
            list(category_rows),
            list(category_currency_rows),
        )

    @staticmethod
    def get_inventory_alerts(
        database: Session,
        *,
        threshold: int,
        page: int,
        page_size: int,
    ) -> tuple[
        Any,
        list[Any],
        int,
    ]:
        summary = database.execute(
            select(
                func.count(
                    Product.id
                ).label(
                    "total_products"
                ),
                func.count(
                    Inventory.product_id
                ).label(
                    "tracked_products"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Inventory.product_id
                                .is_(None),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "untracked_products"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Inventory
                                .available_quantity
                                == 0,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "out_of_stock_products"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Inventory
                                .available_quantity
                                .between(1, 5),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "critical_stock_products"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                and_(
                                    Inventory
                                    .available_quantity
                                    > 5,
                                    Inventory
                                    .available_quantity
                                    <= threshold,
                                ),
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "low_stock_products"
                ),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                Inventory
                                .available_quantity
                                > threshold,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label(
                    "healthy_stock_products"
                ),
            )
            .select_from(Product)
            .outerjoin(
                Inventory,
                Inventory.product_id
                == Product.id,
            )
        ).one()

        alert_condition = (
            Inventory.product_id.is_(None)
            | (
                Inventory.available_quantity
                <= threshold
            )
        )

        total_items = database.scalar(
            select(
                func.count(Product.id)
            )
            .select_from(Product)
            .outerjoin(
                Inventory,
                Inventory.product_id
                == Product.id,
            )
            .where(alert_condition)
        )

        status_priority = case(
            (
                Inventory.product_id
                .is_(None),
                0,
            ),
            (
                Inventory.available_quantity
                == 0,
                1,
            ),
            (
                Inventory.available_quantity
                <= 5,
                2,
            ),
            else_=3,
        )

        rows = database.execute(
            select(
                Product.id.label(
                    "product_id"
                ),
                Product.name.label(
                    "product_name"
                ),
                Product.sku.label("sku"),
                Product.brand.label(
                    "brand"
                ),
                Category.name.label(
                    "category_name"
                ),
                Inventory
                .available_quantity
                .label(
                    "available_quantity"
                ),
                Inventory
                .reserved_quantity
                .label(
                    "reserved_quantity"
                ),
            )
            .select_from(Product)
            .join(
                Category,
                Category.id
                == Product.category_id,
            )
            .outerjoin(
                Inventory,
                Inventory.product_id
                == Product.id,
            )
            .where(alert_condition)
            .order_by(
                status_priority.asc(),
                Inventory
                .available_quantity
                .asc()
                .nullsfirst(),
                Product.name.asc(),
            )
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
        ).all()

        return (
            summary,
            list(rows),
            int(total_items or 0),
        )
