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


def create_customer() -> CustomerSession:
    email = f"address-customer-{uuid4()}@example.com"
    password = "StrongAddressPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Address Test Customer",
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

    return {
        "email": email,
        "headers": {
            "Authorization": f"Bearer {token}",
        },
    }


def delete_customer(email: str) -> None:
    database = SessionLocal()

    try:
        user = database.scalar(select(User).where(User.email == email))

        if user is not None:
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
    *,
    is_default: bool = False,
) -> dict[str, object]:
    return {
        "full_name": "Address Test Customer",
        "phone": "+1 312 555 0199",
        "address_line_1": f"{label} 100 Main Street",
        "address_line_2": "Apartment 4B",
        "city": "Chicago",
        "state": "Illinois",
        "postal_code": "60601",
        "country_code": "us",
        "is_default": is_default,
    }


def test_addresses_require_authentication() -> None:
    response = client.get("/api/v1/addresses")

    assert response.status_code == 401


def test_first_address_becomes_default(
    customer_session: CustomerSession,
) -> None:
    response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload(
            "First",
            is_default=False,
        ),
    )

    assert response.status_code == 201

    address = response.json()

    assert address["is_default"] is True
    assert address["country_code"] == "US"


def test_creating_new_default_switches_default(
    customer_session: CustomerSession,
) -> None:
    first_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("First"),
    )

    second_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload(
            "Second",
            is_default=True,
        ),
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_id = first_response.json()["id"]
    second_id = second_response.json()["id"]

    list_response = client.get(
        "/api/v1/addresses",
        headers=customer_session["headers"],
    )

    addresses = {address["id"]: address for address in list_response.json()}

    assert addresses[first_id]["is_default"] is False
    assert addresses[second_id]["is_default"] is True


def test_update_address(
    customer_session: CustomerSession,
) -> None:
    create_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("Update"),
    )

    address_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/addresses/{address_id}",
        headers=customer_session["headers"],
        json={
            "city": "Evanston",
            "postal_code": "60201",
            "address_line_2": None,
        },
    )

    assert response.status_code == 200

    address = response.json()

    assert address["city"] == "Evanston"
    assert address["postal_code"] == "60201"
    assert address["address_line_2"] is None


def test_cannot_unset_current_default(
    customer_session: CustomerSession,
) -> None:
    create_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("Default"),
    )

    address_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/addresses/{address_id}",
        headers=customer_session["headers"],
        json={
            "is_default": False,
        },
    )

    assert response.status_code == 409


def test_delete_default_promotes_remaining_address(
    customer_session: CustomerSession,
) -> None:
    first_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("First"),
    )

    second_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("Second"),
    )

    first_id = first_response.json()["id"]
    second_id = second_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/addresses/{first_id}",
        headers=customer_session["headers"],
    )

    assert delete_response.status_code == 204

    get_response = client.get(
        f"/api/v1/addresses/{second_id}",
        headers=customer_session["headers"],
    )

    assert get_response.status_code == 200
    assert get_response.json()["is_default"] is True


def test_other_customer_cannot_access_address(
    customer_session: CustomerSession,
) -> None:
    create_response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=address_payload("Private"),
    )

    address_id = create_response.json()["id"]
    other_customer = create_customer()

    try:
        response = client.get(
            f"/api/v1/addresses/{address_id}",
            headers=other_customer["headers"],
        )

        assert response.status_code == 404
    finally:
        delete_customer(other_customer["email"])


def test_invalid_country_code_returns_422(
    customer_session: CustomerSession,
) -> None:
    payload = address_payload("Invalid")
    payload["country_code"] = "USA"

    response = client.post(
        "/api/v1/addresses",
        headers=customer_session["headers"],
        json=payload,
    )

    assert response.status_code == 422
