from __future__ import annotations

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
