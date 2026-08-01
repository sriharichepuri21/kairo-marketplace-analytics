from decimal import (
    ROUND_HALF_UP,
    Decimal,
)
from math import ceil

from sqlalchemy.orm import Session

from app.repositories.operations_repository import (
    OperationsRepository,
)
from app.schemas.admin_operations import (
    OperationsCategoryCurrencySummary,
    OperationsCategoryPerformanceItem,
    OperationsCategoryPerformanceResponse,
    OperationsConversionFunnelResponse,
    OperationsCurrencySummary,
    OperationsInventoryAlertItem,
    OperationsInventoryAlertsResponse,
    OperationsOrderStatusItem,
    OperationsOrderStatusResponse,
    OperationsRevenueTrendPoint,
    OperationsRevenueTrendResponse,
    OperationsSummaryResponse,
)

MONEY_PRECISION = Decimal("0.01")


def decimal_value(
    value: object,
) -> Decimal:
    if value is None:
        return Decimal("0.00")

    return Decimal(
        str(value)
    ).quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP,
    )


def string_value(
    value: object,
) -> str:
    enum_value = getattr(
        value,
        "value",
        value,
    )

    return str(enum_value)


def conversion_rate(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0

    return round(
        numerator / denominator,
        4,
    )


class OperationsService:
    @staticmethod
    def get_summary(
        database: Session,
        *,
        days: int,
    ) -> OperationsSummaryResponse:
        (
            start_date,
            end_date,
            summary,
            currency_rows,
        ) = OperationsRepository.get_summary(
            database,
            days=days,
        )

        if summary is None:
            return OperationsSummaryResponse(
                days=days,
                start_date=start_date,
                end_date=end_date,
                snapshot_date=end_date,
                total_orders=0,
                eligible_orders=0,
                delivered_orders=0,
                cancelled_orders=0,
                active_customers=0,
                revenue_by_currency=[],
            )

        return OperationsSummaryResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            snapshot_date=end_date,
            total_orders=int(
                summary.total_orders or 0
            ),
            eligible_orders=int(
                summary.eligible_orders or 0
            ),
            delivered_orders=int(
                summary.delivered_orders or 0
            ),
            cancelled_orders=int(
                summary.cancelled_orders or 0
            ),
            active_customers=int(
                summary.active_customers or 0
            ),
            revenue_by_currency=[
                OperationsCurrencySummary(
                    currency_code=(
                        row.currency_code
                    ),
                    eligible_orders=int(
                        row.eligible_orders or 0
                    ),
                    gross_sales=decimal_value(
                        row.gross_sales
                    ),
                    average_order_value=(
                        decimal_value(
                            row.average_order_value
                        )
                    ),
                )
                for row in currency_rows
            ],
        )

    @staticmethod
    def get_revenue_trend(
        database: Session,
        *,
        days: int,
    ) -> OperationsRevenueTrendResponse:
        (
            start_date,
            end_date,
            rows,
        ) = OperationsRepository.get_revenue_trend(
            database,
            days=days,
        )

        return OperationsRevenueTrendResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            items=[
                OperationsRevenueTrendPoint(
                    order_date=row.order_date,
                    currency_code=(
                        row.currency_code
                    ),
                    eligible_orders=int(
                        row.eligible_orders or 0
                    ),
                    gross_sales=decimal_value(
                        row.gross_sales
                    ),
                    average_order_value=(
                        decimal_value(
                            row.average_order_value
                        )
                    ),
                )
                for row in rows
            ],
        )

    @staticmethod
    def get_order_statuses(
        database: Session,
        *,
        days: int,
    ) -> OperationsOrderStatusResponse:
        (
            start_date,
            end_date,
            rows,
        ) = OperationsRepository.get_order_statuses(
            database,
            days=days,
        )

        total_orders = sum(
            int(row.order_count or 0)
            for row in rows
        )

        return OperationsOrderStatusResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            items=[
                OperationsOrderStatusItem(
                    status=string_value(
                        row.status
                    ),
                    order_count=int(
                        row.order_count or 0
                    ),
                    order_percentage=(
                        round(
                            int(
                                row.order_count
                                or 0
                            )
                            / total_orders,
                            4,
                        )
                        if total_orders
                        else 0
                    ),
                )
                for row in rows
            ],
        )

    @staticmethod
    def get_category_performance(
        database: Session,
        *,
        days: int,
    ) -> OperationsCategoryPerformanceResponse:
        (
            start_date,
            end_date,
            category_rows,
            currency_rows,
        ) = (
            OperationsRepository
            .get_category_performance(
                database,
                days=days,
            )
        )

        revenue_totals: dict[
            str,
            Decimal,
        ] = {}

        category_revenue: dict[
            object,
            list[object],
        ] = {}

        for row in currency_rows:
            currency_code = str(
                row.currency_code
            )

            gross_sales = decimal_value(
                row.gross_sales
            )

            revenue_totals[
                currency_code
            ] = (
                revenue_totals.get(
                    currency_code,
                    Decimal("0.00"),
                )
                + gross_sales
            )

            category_revenue.setdefault(
                row.category_id,
                [],
            ).append(row)

        items = []

        for row in category_rows:
            revenue_items = []

            for currency_row in (
                category_revenue.get(
                    row.category_id,
                    [],
                )
            ):
                currency_code = str(
                    currency_row.currency_code
                )

                gross_sales = decimal_value(
                    currency_row.gross_sales
                )

                units_sold = int(
                    currency_row.units_sold
                    or 0
                )

                currency_total = (
                    revenue_totals.get(
                        currency_code,
                        Decimal("0.00"),
                    )
                )

                revenue_share = (
                    float(
                        gross_sales
                        / currency_total
                    )
                    if currency_total
                    else 0
                )

                average_unit_revenue = (
                    gross_sales
                    / Decimal(units_sold)
                    if units_sold
                    else Decimal("0.00")
                )

                revenue_items.append(
                    OperationsCategoryCurrencySummary(
                        currency_code=(
                            currency_code
                        ),
                        units_sold=units_sold,
                        gross_sales=gross_sales,
                        average_unit_revenue=(
                            decimal_value(
                                average_unit_revenue
                            )
                        ),
                        revenue_share=round(
                            revenue_share,
                            4,
                        ),
                    )
                )

            items.append(
                OperationsCategoryPerformanceItem(
                    category_id=(
                        row.category_id
                    ),
                    category_name=(
                        row.category_name
                    ),
                    products_sold=int(
                        row.products_sold or 0
                    ),
                    eligible_orders=int(
                        row.eligible_orders or 0
                    ),
                    units_sold=int(
                        row.units_sold or 0
                    ),
                    revenue_by_currency=(
                        revenue_items
                    ),
                )
            )

        return (
            OperationsCategoryPerformanceResponse(
                days=days,
                start_date=start_date,
                end_date=end_date,
                items=items,
            )
        )

    @staticmethod
    def get_inventory_alerts(
        database: Session,
        *,
        threshold: int,
        page: int,
        page_size: int,
    ) -> OperationsInventoryAlertsResponse:
        (
            summary,
            rows,
            total_items,
        ) = (
            OperationsRepository
            .get_inventory_alerts(
                database,
                threshold=threshold,
                page=page,
                page_size=page_size,
            )
        )

        items = []

        for row in rows:
            available = (
                row.available_quantity
            )

            if available is None:
                status = "untracked"
            elif available == 0:
                status = "out_of_stock"
            elif available <= 5:
                status = "critical_stock"
            else:
                status = "low_stock"

            items.append(
                OperationsInventoryAlertItem(
                    product_id=row.product_id,
                    product_name=(
                        row.product_name
                    ),
                    sku=row.sku,
                    brand=row.brand,
                    category_name=(
                        row.category_name
                    ),
                    available_quantity=(
                        available
                    ),
                    reserved_quantity=(
                        row.reserved_quantity
                    ),
                    inventory_status=status,
                )
            )

        return OperationsInventoryAlertsResponse(
            low_stock_threshold=threshold,
            total_products=int(
                summary.total_products or 0
            ),
            tracked_products=int(
                summary.tracked_products or 0
            ),
            untracked_products=int(
                summary.untracked_products or 0
            ),
            out_of_stock_products=int(
                summary.out_of_stock_products
                or 0
            ),
            critical_stock_products=int(
                summary.critical_stock_products
                or 0
            ),
            low_stock_products=int(
                summary.low_stock_products or 0
            ),
            healthy_stock_products=int(
                summary.healthy_stock_products
                or 0
            ),
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=(
                ceil(total_items / page_size)
                if total_items
                else 0
            ),
            items=items,
        )

    @staticmethod
    def get_conversion_funnel(
        database: Session,
        *,
        days: int,
    ) -> OperationsConversionFunnelResponse:
        (
            start_date,
            end_date,
            summary,
        ) = (
            OperationsRepository
            .get_conversion_funnel(
                database,
                days=days,
            )
        )

        if summary is None:
            return (
                OperationsConversionFunnelResponse(
                    days=days,
                    start_date=start_date,
                    end_date=end_date,
                    total_sessions=0,
                    product_view_sessions=0,
                    add_to_cart_sessions=0,
                    checkout_started_sessions=0,
                    order_placed_sessions=0,
                    view_dropoffs=0,
                    cart_dropoffs=0,
                    checkout_dropoffs=0,
                    view_to_cart_rate=0,
                    cart_to_checkout_rate=0,
                    checkout_to_order_rate=0,
                    overall_conversion_rate=0,
                )
            )

        product_views = int(
            summary.product_view_sessions
            or 0
        )

        cart_sessions = int(
            summary.add_to_cart_sessions
            or 0
        )

        checkout_sessions = int(
            summary.checkout_started_sessions
            or 0
        )

        order_sessions = int(
            summary.order_placed_sessions
            or 0
        )

        return OperationsConversionFunnelResponse(
            days=days,
            start_date=start_date,
            end_date=end_date,
            total_sessions=int(
                summary.total_sessions or 0
            ),
            product_view_sessions=(
                product_views
            ),
            add_to_cart_sessions=(
                cart_sessions
            ),
            checkout_started_sessions=(
                checkout_sessions
            ),
            order_placed_sessions=(
                order_sessions
            ),
            view_dropoffs=int(
                summary.view_dropoffs or 0
            ),
            cart_dropoffs=int(
                summary.cart_dropoffs or 0
            ),
            checkout_dropoffs=int(
                summary.checkout_dropoffs or 0
            ),
            view_to_cart_rate=(
                conversion_rate(
                    cart_sessions,
                    product_views,
                )
            ),
            cart_to_checkout_rate=(
                conversion_rate(
                    checkout_sessions,
                    cart_sessions,
                )
            ),
            checkout_to_order_rate=(
                conversion_rate(
                    order_sessions,
                    checkout_sessions,
                )
            ),
            overall_conversion_rate=(
                conversion_rate(
                    order_sessions,
                    product_views,
                )
            ),
        )
