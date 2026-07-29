from collections.abc import Generator
from decimal import Decimal
from typing import TypedDict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.models import Inventory, Order, User

client = TestClient(app)


class CustomerSession(TypedDict):
    email: str
    user_id: str
    headers: dict[str, str]


def create_customer() -> CustomerSession:
    email = f"checkout-customer-{uuid4()}@example.com"
    password = "StrongCheckoutPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Checkout Test Customer",
            "password": password,
        },
    )

    assert register_response.status_code == 201

    user_id = register_response.json()["id"]

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    return {
        "email": email,
        "user_id": user_id,
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def delete_customer(email: str) -> None:
    database = SessionLocal()

    try:
        user = database.scalar(select(User).where(User.email == email))

        if user is None:
            return

        database.execute(delete(Order).where(Order.user_id == user.id))

        database.flush()
        database.delete(user)
        database.commit()
    finally:
        database.close()


@pytest.fixture
def customer_session() -> Generator[
    CustomerSession,
    None,
    None,
]:
    session = create_customer()

    try:
        yield session
    finally:
        delete_customer(session["email"])


def address_payload(
    label: str,
) -> dict[str, object]:
    return {
        "full_name": "Checkout Test Customer",
        "phone": "+1 312 555 0188",
        "address_line_1": f"{label} 100 Main Street",
        "address_line_2": "Apartment 8A",
        "city": "Chicago",
        "state": "Illinois",
        "postal_code": "60601",
        "country_code": "US",
        "is_default": True,
    }


def create_address(
    customer: CustomerSession,
    label: str = "Shipping",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/addresses",
        headers=customer["headers"],
        json=address_payload(label),
    )

    assert response.status_code == 201

    return response.json()


def get_in_stock_product(
    minimum_quantity: int = 1,
) -> dict[str, object]:
    response = client.get(
        "/api/v1/products",
        params={
            "in_stock": True,
            "page_size": 100,
        },
    )

    assert response.status_code == 200

    products = response.json()["items"]

    product = next(
        (item for item in products if int(item["available_quantity"]) >= minimum_quantity),
        None,
    )

    assert product is not None

    return product


def add_product_to_cart(
    customer: CustomerSession,
    product_id: str,
    quantity: int = 1,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/cart/items",
        headers=customer["headers"],
        json={
            "product_id": product_id,
            "quantity": quantity,
        },
    )

    assert response.status_code == 201

    return response.json()


def inventory_quantity(
    product_id: str,
) -> int:
    database = SessionLocal()

    try:
        inventory = database.scalar(
            select(Inventory).where(Inventory.product_id == UUID(product_id))
        )

        assert inventory is not None

        return inventory.available_quantity
    finally:
        database.close()


def set_inventory_quantity(
    product_id: str,
    quantity: int,
) -> None:
    database = SessionLocal()

    try:
        inventory = database.scalar(
            select(Inventory).where(Inventory.product_id == UUID(product_id))
        )

        assert inventory is not None

        inventory.available_quantity = quantity
        database.commit()
    finally:
        database.close()


def checkout(
    customer: CustomerSession,
    address_id: str,
) -> object:
    return client.post(
        "/api/v1/checkout",
        headers=customer["headers"],
        json={
            "shipping_address_id": address_id,
            "customer_note": "Please handle with care.",
        },
    )


def test_checkout_requires_authentication() -> None:
    response = client.post(
        "/api/v1/checkout",
        json={
            "shipping_address_id": str(uuid4()),
        },
    )

    assert response.status_code == 401


def test_checkout_creates_order_deducts_inventory_and_clears_cart(
    customer_session: CustomerSession,
) -> None:
    address = create_address(customer_session)
    product = get_in_stock_product(2)

    product_id = str(product["id"])
    original_inventory = inventory_quantity(product_id)

    try:
        add_product_to_cart(
            customer_session,
            product_id,
            quantity=2,
        )

        response = checkout(
            customer_session,
            str(address["id"]),
        )

        assert response.status_code == 201

        order = response.json()

        assert order["order_number"].startswith("KAIRO-")
        assert order["status"] == "pending"
        assert order["payment_status"] == "pending"
        assert order["currency_code"] == "INR"
        assert len(order["items"]) == 1
        assert order["items"][0]["product_id"] == product_id
        assert order["items"][0]["quantity"] == 2

        unit_price = Decimal(order["items"][0]["unit_price"])

        line_total = Decimal(order["items"][0]["line_total"])

        assert line_total == unit_price * 2
        assert Decimal(order["subtotal"]) == line_total
        assert Decimal(order["shipping_amount"]) == Decimal("0.00")
        assert Decimal(order["tax_amount"]) == Decimal("0.00")
        assert Decimal(order["total_amount"]) == line_total

        assert len(order["status_history"]) == 1
        assert order["status_history"][0]["status"] == "pending"

        cart_response = client.get(
            "/api/v1/cart",
            headers=customer_session["headers"],
        )

        assert cart_response.status_code == 200
        assert cart_response.json()["items"] == []
        assert cart_response.json()["total_quantity"] == 0

        assert inventory_quantity(product_id) == (original_inventory - 2)
    finally:
        set_inventory_quantity(
            product_id,
            original_inventory,
        )


def test_checkout_with_empty_cart_returns_409(
    customer_session: CustomerSession,
) -> None:
    address = create_address(customer_session)

    response = checkout(
        customer_session,
        str(address["id"]),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Your cart is empty.")


def test_checkout_rejects_another_customers_address(
    customer_session: CustomerSession,
) -> None:
    product = get_in_stock_product()
    product_id = str(product["id"])
    original_inventory = inventory_quantity(product_id)

    other_customer = create_customer()

    try:
        other_address = create_address(
            other_customer,
            label="Private",
        )

        add_product_to_cart(
            customer_session,
            product_id,
        )

        response = checkout(
            customer_session,
            str(other_address["id"]),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == ("Shipping address not found.")

        cart_response = client.get(
            "/api/v1/cart",
            headers=customer_session["headers"],
        )

        assert len(cart_response.json()["items"]) == 1
        assert inventory_quantity(product_id) == (original_inventory)

        orders_response = client.get(
            "/api/v1/orders",
            headers=customer_session["headers"],
        )

        assert orders_response.json() == []
    finally:
        delete_customer(other_customer["email"])


def test_inventory_failure_rolls_back_checkout(
    customer_session: CustomerSession,
) -> None:
    address = create_address(customer_session)
    product = get_in_stock_product()

    product_id = str(product["id"])
    original_inventory = inventory_quantity(product_id)

    add_product_to_cart(
        customer_session,
        product_id,
    )

    try:
        set_inventory_quantity(product_id, 0)

        response = checkout(
            customer_session,
            str(address["id"]),
        )

        assert response.status_code == 409
        assert "currently available" in (response.json()["detail"])

        cart_response = client.get(
            "/api/v1/cart",
            headers=customer_session["headers"],
        )

        assert cart_response.status_code == 200
        assert len(cart_response.json()["items"]) == 1
        assert cart_response.json()["total_quantity"] == 1

        orders_response = client.get(
            "/api/v1/orders",
            headers=customer_session["headers"],
        )

        assert orders_response.status_code == 200
        assert orders_response.json() == []
    finally:
        set_inventory_quantity(
            product_id,
            original_inventory,
        )


def test_order_keeps_shipping_address_snapshot(
    customer_session: CustomerSession,
) -> None:
    address = create_address(customer_session)
    product = get_in_stock_product()

    product_id = str(product["id"])
    original_inventory = inventory_quantity(product_id)

    try:
        add_product_to_cart(
            customer_session,
            product_id,
        )

        checkout_response = checkout(
            customer_session,
            str(address["id"]),
        )

        assert checkout_response.status_code == 201

        order = checkout_response.json()

        update_response = client.patch(
            f"/api/v1/addresses/{address['id']}",
            headers=customer_session["headers"],
            json={
                "city": "Evanston",
                "postal_code": "60201",
            },
        )

        assert update_response.status_code == 200

        order_response = client.get(
            f"/api/v1/orders/{order['id']}",
            headers=customer_session["headers"],
        )

        assert order_response.status_code == 200

        saved_order = order_response.json()

        assert saved_order["shipping_address"]["city"] == "Chicago"

        assert saved_order["shipping_address"]["postal_code"] == "60601"
    finally:
        set_inventory_quantity(
            product_id,
            original_inventory,
        )


def test_customer_cannot_access_another_customers_order(
    customer_session: CustomerSession,
) -> None:
    address = create_address(customer_session)
    product = get_in_stock_product()

    product_id = str(product["id"])
    original_inventory = inventory_quantity(product_id)

    other_customer = create_customer()

    try:
        add_product_to_cart(
            customer_session,
            product_id,
        )

        checkout_response = checkout(
            customer_session,
            str(address["id"]),
        )

        assert checkout_response.status_code == 201

        order_id = checkout_response.json()["id"]

        response = client.get(
            f"/api/v1/orders/{order_id}",
            headers=other_customer["headers"],
        )

        assert response.status_code == 404
        assert response.json()["detail"] == ("Order not found.")

        owner_list_response = client.get(
            "/api/v1/orders",
            headers=customer_session["headers"],
        )

        assert owner_list_response.status_code == 200
        assert len(owner_list_response.json()) == 1

        other_list_response = client.get(
            "/api/v1/orders",
            headers=other_customer["headers"],
        )

        assert other_list_response.status_code == 200
        assert other_list_response.json() == []
    finally:
        set_inventory_quantity(
            product_id,
            original_inventory,
        )
        delete_customer(other_customer["email"])
