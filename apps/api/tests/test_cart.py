from collections.abc import Generator
from typing import TypedDict
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import User

client = TestClient(app)


class CustomerSession(TypedDict):
    email: str
    headers: dict[str, str]


@pytest.fixture
def customer_session() -> Generator[CustomerSession, None, None]:
    email = f"cart-customer-{uuid4()}@example.com"
    password = "StrongCartPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Cart Test Customer",
            "password": password,
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    try:
        yield {
            "email": email,
            "headers": {
                "Authorization": f"Bearer {token}",
            },
        }
    finally:
        database = SessionLocal()

        try:
            user = database.scalar(select(User).where(User.email == email))

            if user is not None:
                database.delete(user)
                database.commit()
        finally:
            database.close()


def get_products(
    count: int = 1,
) -> list[dict[str, object]]:
    response = client.get(
        "/api/v1/products",
        params={
            "in_stock": True,
            "page_size": count,
        },
    )

    assert response.status_code == 200

    return response.json()["items"]


def test_cart_requires_authentication() -> None:
    response = client.get("/api/v1/cart")

    assert response.status_code == 401


def test_get_empty_cart(
    customer_session: CustomerSession,
) -> None:
    response = client.get(
        "/api/v1/cart",
        headers=customer_session["headers"],
    )

    assert response.status_code == 200

    cart = response.json()

    assert cart["items"] == []
    assert cart["total_quantity"] == 0
    assert cart["subtotal"] == "0.00"


def test_add_product_to_cart(
    customer_session: CustomerSession,
) -> None:
    product = get_products()[0]

    response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert response.status_code == 201

    cart = response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["product"]["id"] == product["id"]
    assert cart["items"][0]["quantity"] == 2
    assert cart["total_quantity"] == 2


def test_adding_existing_product_increases_quantity(
    customer_session: CustomerSession,
) -> None:
    product = get_products()[0]

    first_response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert second_response.status_code == 201

    cart = second_response.json()

    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3
    assert cart["total_quantity"] == 3


def test_update_cart_item_quantity(
    customer_session: CustomerSession,
) -> None:
    product = get_products()[0]

    add_response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    item_id = add_response.json()["items"][0]["id"]

    update_response = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=customer_session["headers"],
        json={"quantity": 3},
    )

    assert update_response.status_code == 200
    assert update_response.json()["items"][0]["quantity"] == 3
    assert update_response.json()["total_quantity"] == 3


def test_remove_cart_item(
    customer_session: CustomerSession,
) -> None:
    product = get_products()[0]

    add_response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    item_id = add_response.json()["items"][0]["id"]

    delete_response = client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=customer_session["headers"],
    )

    assert delete_response.status_code == 204

    cart_response = client.get(
        "/api/v1/cart",
        headers=customer_session["headers"],
    )

    assert cart_response.json()["items"] == []
    assert cart_response.json()["total_quantity"] == 0


def test_clear_cart(
    customer_session: CustomerSession,
) -> None:
    products = get_products(2)

    for product in products:
        response = client.post(
            "/api/v1/cart/items",
            headers=customer_session["headers"],
            json={
                "product_id": product["id"],
                "quantity": 1,
            },
        )

        assert response.status_code == 201

    clear_response = client.delete(
        "/api/v1/cart",
        headers=customer_session["headers"],
    )

    assert clear_response.status_code == 204

    cart_response = client.get(
        "/api/v1/cart",
        headers=customer_session["headers"],
    )

    assert cart_response.json()["items"] == []
    assert cart_response.json()["total_quantity"] == 0


def test_quantity_cannot_exceed_inventory(
    customer_session: CustomerSession,
) -> None:
    product = get_products()[0]
    available_quantity = int(product["available_quantity"])

    response = client.post(
        "/api/v1/cart/items",
        headers=customer_session["headers"],
        json={
            "product_id": product["id"],
            "quantity": available_quantity + 1,
        },
    )

    assert response.status_code == 409
    assert "currently available" in response.json()["detail"]
