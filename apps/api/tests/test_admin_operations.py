from collections.abc import Generator
from decimal import (
    ROUND_HALF_UP,
    Decimal,
)
from typing import (
    Any,
    TypedDict,
)
from uuid import (
    UUID,
    uuid4,
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (
    delete,
    select,
)

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    Order,
    User,
)
from app.services.operations_service import (
    OperationsService,
)

client = TestClient(app)

MONEY_PRECISION = Decimal("0.01")


class AuthenticatedUser(TypedDict):
    user_id: UUID
    email: str
    headers: dict[str, str]


class OperationsContext(TypedDict):
    admin: AuthenticatedUser
    customer: AuthenticatedUser
    baseline: dict[str, Any]
    order_ids: list[UUID]


def create_authenticated_user(
    role: str,
) -> AuthenticatedUser:
    email = (
        f"operations-{role}-{uuid4()}"
        "@example.com"
    )
    password = (
        "StrongOperationsPassword123!"
    )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": (
                f"Operations {role.title()}"
            ),
            "password": password,
        },
    )

    assert response.status_code == 201

    database = SessionLocal()

    try:
        user = database.scalar(
            select(User).where(
                User.email == email
            )
        )

        assert user is not None

        user.role = role
        database.commit()

        user_id = user.id

    finally:
        database.close()

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()[
        "access_token"
    ]

    return {
        "user_id": user_id,
        "email": email,
        "headers": {
            "Authorization": (
                f"Bearer {token}"
            ),
        },
    }


def create_test_order(
    *,
    user_id: UUID,
    status: str,
    payment_status: str,
    currency_code: str,
    subtotal: Decimal,
    shipping_amount: Decimal,
    tax_amount: Decimal,
) -> Order:
    total_amount = (
        subtotal
        + shipping_amount
        + tax_amount
    )

    return Order(
        order_number=(
            f"OPS-TEST-{uuid4().hex[:20]}"
        ),
        user_id=user_id,
        status=status,
        payment_status=payment_status,
        currency_code=currency_code,
        subtotal=subtotal,
        shipping_amount=shipping_amount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        shipping_full_name=(
            "Operations Test Customer"
        ),
        shipping_phone="+1-555-0100",
        shipping_address_line_1=(
            "100 Test Market Street"
        ),
        shipping_address_line_2=None,
        shipping_city="Seattle",
        shipping_state="Washington",
        shipping_postal_code="98101",
        shipping_country_code="US",
        customer_note=None,
    )


def delete_test_records(
    order_ids: list[UUID],
    emails: list[str],
) -> None:
    database = SessionLocal()

    try:
        if order_ids:
            database.execute(
                delete(Order).where(
                    Order.id.in_(order_ids)
                )
            )

        users = database.scalars(
            select(User).where(
                User.email.in_(emails)
            )
        ).all()

        for user in users:
            database.delete(user)

        database.commit()

    finally:
        database.close()


def currency_map(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return {
        row["currency_code"]: row
        for row in rows
    }


def money(
    value: object,
) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        MONEY_PRECISION,
        rounding=ROUND_HALF_UP,
    )


@pytest.fixture
def operations_context() -> Generator[
    OperationsContext,
    None,
    None,
]:
    admin = create_authenticated_user(
        "admin"
    )
    customer = create_authenticated_user(
        "customer"
    )
    order_customer = (
        create_authenticated_user(
            "customer"
        )
    )

    database = SessionLocal()
    order_ids: list[UUID] = []

    try:
        baseline = (
            OperationsService.get_summary(
                database
            ).model_dump()
        )

        orders = [
            create_test_order(
                user_id=(
                    order_customer["user_id"]
                ),
                status="delivered",
                payment_status="paid",
                currency_code="USD",
                subtotal=Decimal("100.00"),
                shipping_amount=Decimal(
                    "10.00"
                ),
                tax_amount=Decimal("5.00"),
            ),
            create_test_order(
                user_id=(
                    order_customer["user_id"]
                ),
                status="cancelled",
                payment_status="paid",
                currency_code="USD",
                subtotal=Decimal("55.00"),
                shipping_amount=Decimal(
                    "10.00"
                ),
                tax_amount=Decimal("5.00"),
            ),
            create_test_order(
                user_id=(
                    order_customer["user_id"]
                ),
                status="confirmed",
                payment_status="pending",
                currency_code="EUR",
                subtotal=Decimal("35.00"),
                shipping_amount=Decimal(
                    "10.00"
                ),
                tax_amount=Decimal("5.00"),
            ),
            create_test_order(
                user_id=(
                    order_customer["user_id"]
                ),
                status="processing",
                payment_status="paid",
                currency_code="EUR",
                subtotal=Decimal("200.00"),
                shipping_amount=Decimal(
                    "20.00"
                ),
                tax_amount=Decimal("10.00"),
            ),
        ]

        database.add_all(orders)
        database.commit()

        order_ids = [
            order.id
            for order in orders
        ]

    finally:
        database.close()

    try:
        yield {
            "admin": admin,
            "customer": customer,
            "baseline": baseline,
            "order_ids": order_ids,
        }

    finally:
        delete_test_records(
            order_ids,
            [
                admin["email"],
                customer["email"],
                order_customer["email"],
            ],
        )


def test_operations_summary_requires_authentication(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/summary"
    )

    assert response.status_code == 401


def test_customer_cannot_access_operations_summary(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/summary",
        headers=(
            operations_context[
                "customer"
            ]["headers"]
        ),
    )

    assert response.status_code == 403


def test_admin_can_get_operations_summary(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/summary",
        headers=(
            operations_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    payload = response.json()
    baseline = operations_context[
        "baseline"
    ]

    assert payload["snapshot_date"] is not None

    assert (
        payload["total_orders"]
        == baseline["total_orders"] + 4
    )

    assert (
        payload["eligible_orders"]
        == baseline["eligible_orders"] + 2
    )

    assert (
        payload["delivered_orders"]
        == baseline["delivered_orders"] + 1
    )

    assert (
        payload["cancelled_orders"]
        == baseline["cancelled_orders"] + 1
    )

    assert (
        payload["active_customers"]
        == baseline["active_customers"] + 1
    )


def test_cancelled_and_unpaid_orders_are_excluded(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/summary",
        headers=(
            operations_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    payload = response.json()
    baseline = operations_context[
        "baseline"
    ]

    current_currencies = currency_map(
        payload["revenue_by_currency"]
    )
    baseline_currencies = currency_map(
        baseline["revenue_by_currency"]
    )

    usd = current_currencies["USD"]
    baseline_usd = (
        baseline_currencies["USD"]
    )

    assert (
        usd["eligible_orders"]
        == baseline_usd[
            "eligible_orders"
        ] + 1
    )

    assert (
        money(usd["gross_sales"])
        == money(
            baseline_usd["gross_sales"]
        )
        + Decimal("115.00")
    )

    eur = current_currencies["EUR"]
    baseline_eur = (
        baseline_currencies["EUR"]
    )

    assert (
        eur["eligible_orders"]
        == baseline_eur[
            "eligible_orders"
        ] + 1
    )

    assert (
        money(eur["gross_sales"])
        == money(
            baseline_eur["gross_sales"]
        )
        + Decimal("230.00")
    )


def test_currency_average_order_values_reconcile(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/summary",
        headers=(
            operations_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 200

    for row in response.json()[
        "revenue_by_currency"
    ]:
        eligible_orders = int(
            row["eligible_orders"]
        )

        assert eligible_orders > 0

        expected_average = (
            money(row["gross_sales"])
            / Decimal(eligible_orders)
        ).quantize(
            MONEY_PRECISION,
            rounding=ROUND_HALF_UP,
        )

        assert (
            money(
                row[
                    "average_order_value"
                ]
            )
            == expected_average
        )


def test_revenue_trend_requires_authentication(
    operations_context: OperationsContext,
) -> None:
    response = client.get(
        "/api/v1/admin/operations/revenue-trend"
    )

    assert response.status_code == 401


def test_customer_cannot_access_operations_analytics(
    operations_context: OperationsContext,
) -> None:
    headers = operations_context[
        "customer"
    ]["headers"]

    revenue_response = client.get(
        "/api/v1/admin/operations/revenue-trend",
        headers=headers,
    )

    status_response = client.get(
        "/api/v1/admin/operations/order-statuses",
        headers=headers,
    )

    assert revenue_response.status_code == 403
    assert status_response.status_code == 403


def test_admin_can_get_revenue_trend(
    operations_context: OperationsContext,
) -> None:
    headers = operations_context[
        "admin"
    ]["headers"]

    response = client.get(
        (
            "/api/v1/admin/operations/"
            "revenue-trend?days=3650"
        ),
        headers=headers,
    )

    summary_response = client.get(
        "/api/v1/admin/operations/summary",
        headers=headers,
    )

    assert response.status_code == 200
    assert summary_response.status_code == 200

    payload = response.json()
    summary = summary_response.json()

    assert payload["days"] == 3650
    assert payload["start_date"] is not None
    assert payload["end_date"] is not None
    assert payload["items"]

    trend_by_currency: dict[
        str,
        dict[str, Decimal | int],
    ] = {}

    for item in payload["items"]:
        currency_code = item[
            "currency_code"
        ]

        values = trend_by_currency.setdefault(
            currency_code,
            {
                "eligible_orders": 0,
                "gross_sales": Decimal(
                    "0.00"
                ),
            },
        )

        values["eligible_orders"] = (
            int(values["eligible_orders"])
            + int(item["eligible_orders"])
        )

        values["gross_sales"] = (
            money(values["gross_sales"])
            + money(item["gross_sales"])
        )

    for currency in summary[
        "revenue_by_currency"
    ]:
        trend_values = trend_by_currency[
            currency["currency_code"]
        ]

        assert (
            int(
                trend_values[
                    "eligible_orders"
                ]
            )
            == currency["eligible_orders"]
        )

        assert (
            money(
                trend_values[
                    "gross_sales"
                ]
            )
            == money(
                currency["gross_sales"]
            )
        )


def test_admin_can_get_order_statuses(
    operations_context: OperationsContext,
) -> None:
    headers = operations_context[
        "admin"
    ]["headers"]

    response = client.get(
        (
            "/api/v1/admin/operations/"
            "order-statuses?days=3650"
        ),
        headers=headers,
    )

    summary_response = client.get(
        "/api/v1/admin/operations/summary",
        headers=headers,
    )

    assert response.status_code == 200
    assert summary_response.status_code == 200

    payload = response.json()
    summary = summary_response.json()

    assert payload["days"] == 3650
    assert payload["start_date"] is not None
    assert payload["end_date"] is not None
    assert payload["items"]

    counted_orders = sum(
        item["order_count"]
        for item in payload["items"]
    )

    assert counted_orders == payload[
        "total_orders"
    ]

    assert payload[
        "total_orders"
    ] == summary["total_orders"]

    percentage_total = sum(
        item["order_percentage"]
        for item in payload["items"]
    )

    assert percentage_total == pytest.approx(
        1.0,
        abs=0.001,
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        (
            "/api/v1/admin/operations/"
            "revenue-trend?days=0"
        ),
        (
            "/api/v1/admin/operations/"
            "revenue-trend?days=3651"
        ),
        (
            "/api/v1/admin/operations/"
            "order-statuses?days=0"
        ),
        (
            "/api/v1/admin/operations/"
            "order-statuses?days=3651"
        ),
    ],
)
def test_operations_days_validation(
    operations_context: OperationsContext,
    endpoint: str,
) -> None:
    response = client.get(
        endpoint,
        headers=(
            operations_context[
                "admin"
            ]["headers"]
        ),
    )

    assert response.status_code == 422
