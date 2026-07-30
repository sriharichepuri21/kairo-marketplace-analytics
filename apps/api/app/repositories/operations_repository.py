from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import (
    and_,
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from app.models import Order

eligible_order_condition = and_(
    Order.payment_status == "paid",
    Order.status != "cancelled",
)


class OperationsRepository:
    @staticmethod
    def get_summary(
        database: Session,
    ) -> tuple[Any, list[Any]]:
        summary = database.execute(
            select(
                func.max(
                    func.date(Order.created_at)
                ).label(
                    "snapshot_date"
                ),
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
                    func.avg(Order.total_amount),
                    0,
                ).label(
                    "average_order_value"
                ),
            )
            .where(
                eligible_order_condition
            )
            .group_by(
                Order.currency_code
            )
            .order_by(
                gross_sales.desc(),
                Order.currency_code.asc(),
            )
        ).all()

        return summary, list(currency_rows)

    @staticmethod
    def get_revenue_trend(
        database: Session,
        *,
        days: int,
    ) -> tuple[Any, Any, list[Any]]:
        end_date = database.scalar(
            select(
                func.max(
                    func.date(Order.created_at)
                )
            )
        )

        if end_date is None:
            return None, None, []

        start_date = (
            end_date
            - timedelta(days=days - 1)
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
                    func.avg(Order.total_amount),
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

    @staticmethod
    def get_order_statuses(
        database: Session,
        *,
        days: int,
    ) -> tuple[Any, Any, list[Any]]:
        end_date = database.scalar(
            select(
                func.max(
                    func.date(Order.created_at)
                )
            )
        )

        if end_date is None:
            return None, None, []

        start_date = (
            end_date
            - timedelta(days=days - 1)
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
