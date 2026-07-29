from collections.abc import Generator
from typing import TypedDict
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.main import app
from app.models import (
    CustomerEvent,
    Product,
    User,
)


client = TestClient(app)


class CustomerSession(TypedDict):
    email: str
    user_id: str
    headers: dict[str, str]


def create_customer() -> CustomerSession:
    email = (
        f"event-customer-{uuid4()}@example.com"
    )
    password = "StrongEventPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Event Test Customer",
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

    me_response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert me_response.status_code == 200

    return {
        "email": email,
        "user_id": me_response.json()["id"],
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def delete_customer(
    email: str,
) -> None:
    database = SessionLocal()

    try:
        user = database.scalar(
            select(User).where(
                User.email == email,
            )
        )

        if user is not None:
            database.execute(
                delete(CustomerEvent).where(
                    CustomerEvent.user_id
                    == user.id,
                )
            )

            database.delete(user)
            database.commit()
    finally:
        database.close()


def delete_session_events(
    session_id: str,
) -> None:
    database = SessionLocal()

    try:
        database.execute(
            delete(CustomerEvent).where(
                CustomerEvent.session_id
                == session_id,
            )
        )

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


@pytest.fixture
def product_id() -> str:
    database = SessionLocal()

    try:
        value = database.scalar(
            select(Product.id).limit(1)
        )

        assert value is not None

        return str(value)
    finally:
        database.close()


def test_my_events_require_authentication() -> None:
    response = client.get(
        "/api/v1/events/me"
    )

    assert response.status_code == 401


def test_anonymous_event_requires_session_id(
    product_id: str,
) -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "event_type": "product_view",
            "product_id": product_id,
            "properties": {
                "source": "catalogue",
            },
        },
    )

    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Anonymous events require a session_id."
    )


def test_anonymous_product_view_is_recorded(
    product_id: str,
) -> None:
    session_id = f"anonymous-{uuid4()}"

    try:
        response = client.post(
            "/api/v1/events",
            json={
                "event_type": "product_view",
                "session_id": session_id,
                "product_id": product_id,
                "properties": {
                    "source": "catalogue",
                    "position": 1,
                },
            },
        )

        assert response.status_code == 201

        event = response.json()

        assert event["user_id"] is None
        assert event["session_id"] == session_id
        assert event["event_type"] == (
            "product_view"
        )
        assert event["product_id"] == product_id
        assert event["properties"] == {
            "source": "catalogue",
            "position": 1,
        }
    finally:
        delete_session_events(session_id)


def test_authenticated_event_uses_current_user(
    customer_session: CustomerSession,
) -> None:
    response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "product_search",
            "properties": {
                "query": "wireless headphones",
                "result_count": 8,
            },
        },
    )

    assert response.status_code == 201

    event = response.json()

    assert (
        event["user_id"]
        == customer_session["user_id"]
    )
    assert event["session_id"] is None
    assert event["event_type"] == (
        "product_search"
    )


def test_authenticated_user_can_list_events(
    customer_session: CustomerSession,
    product_id: str,
) -> None:
    first_response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "product_view",
            "product_id": product_id,
            "properties": {
                "source": "product_page",
            },
        },
    )

    second_response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "add_to_cart",
            "product_id": product_id,
            "properties": {
                "quantity": 2,
            },
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = client.get(
        "/api/v1/events/me",
        headers=customer_session["headers"],
    )

    assert response.status_code == 200

    events = response.json()

    assert len(events) >= 2

    event_types = {
        event["event_type"]
        for event in events
    }

    assert "product_view" in event_types
    assert "add_to_cart" in event_types

    assert all(
        event["user_id"]
        == customer_session["user_id"]
        for event in events
    )


def test_customer_cannot_see_other_users_events(
    customer_session: CustomerSession,
    product_id: str,
) -> None:
    other_customer = create_customer()

    try:
        create_response = client.post(
            "/api/v1/events",
            headers=other_customer["headers"],
            json={
                "event_type": "product_view",
                "product_id": product_id,
                "properties": {
                    "source": "private-test",
                },
            },
        )

        assert create_response.status_code == 201

        private_event_id = (
            create_response.json()["id"]
        )

        list_response = client.get(
            "/api/v1/events/me",
            headers=customer_session["headers"],
        )

        assert list_response.status_code == 200

        visible_ids = {
            event["id"]
            for event in list_response.json()
        }

        assert private_event_id not in visible_ids
    finally:
        delete_customer(other_customer["email"])


def test_product_event_requires_product_id() -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "event_type": "product_view",
            "session_id": f"session-{uuid4()}",
            "properties": {},
        },
    )

    assert response.status_code == 422


def test_unknown_product_returns_not_found() -> None:
    session_id = f"unknown-product-{uuid4()}"

    response = client.post(
        "/api/v1/events",
        json={
            "event_type": "product_view",
            "session_id": session_id,
            "product_id": str(uuid4()),
            "properties": {},
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Product not found."
    )


def test_product_search_requires_query(
    customer_session: CustomerSession,
) -> None:
    response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "product_search",
            "properties": {
                "result_count": 0,
            },
        },
    )

    assert response.status_code == 422


def test_invalid_event_type_returns_422() -> None:
    response = client.post(
        "/api/v1/events",
        json={
            "event_type": "clicked_random_button",
            "session_id": f"session-{uuid4()}",
            "properties": {},
        },
    )

    assert response.status_code == 422


def test_anonymous_order_event_is_rejected() -> None:
    session_id = f"order-session-{uuid4()}"

    response = client.post(
        "/api/v1/events",
        json={
            "event_type": "order_placed",
            "session_id": session_id,
            "order_id": str(uuid4()),
            "properties": {},
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Authentication is required "
        "for order events."
    )


def test_unowned_order_returns_not_found(
    customer_session: CustomerSession,
) -> None:
    response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "order_placed",
            "order_id": str(uuid4()),
            "properties": {},
        },
    )

    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == "Order not found."
    )


def test_event_limit_validation(
    customer_session: CustomerSession,
) -> None:
    response = client.get(
        "/api/v1/events/me?limit=501",
        headers=customer_session["headers"],
    )

    assert response.status_code == 422


def test_event_is_persisted_in_database(
    customer_session: CustomerSession,
    product_id: str,
) -> None:
    response = client.post(
        "/api/v1/events",
        headers=customer_session["headers"],
        json={
            "event_type": "add_to_cart",
            "product_id": product_id,
            "properties": {
                "quantity": 3,
                "source": "product_detail",
            },
        },
    )

    assert response.status_code == 201

    event_id = UUID(response.json()["id"])

    database = SessionLocal()

    try:
        event = database.get(
            CustomerEvent,
            event_id,
        )

        assert event is not None
        assert event.event_type == "add_to_cart"
        assert event.properties["quantity"] == 3
        assert (
            event.properties["source"]
            == "product_detail"
        )
    finally:
        database.close()
