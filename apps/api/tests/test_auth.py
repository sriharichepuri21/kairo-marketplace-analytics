from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import User


client = TestClient(app)


@pytest.fixture
def registered_user() -> Generator[dict[str, object], None, None]:
    email = f"customer-{uuid4()}@example.com"
    password = "StrongTestPassword123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Kairo Test Customer",
            "password": password,
        },
    )

    assert response.status_code == 201

    try:
        yield {
            "email": email,
            "password": password,
            "response": response,
        }
    finally:
        database = SessionLocal()

        try:
            user = database.scalar(
                select(User).where(
                    User.email == email,
                )
            )

            if user is not None:
                database.delete(user)
                database.commit()
        finally:
            database.close()


def test_register_customer(
    registered_user: dict[str, object],
) -> None:
    response = registered_user["response"]

    assert hasattr(response, "json")

    payload = response.json()

    assert payload["email"] == registered_user["email"]
    assert payload["full_name"] == "Kairo Test Customer"
    assert payload["role"] == "customer"
    assert payload["is_active"] is True
    assert "password" not in payload
    assert "password_hash" not in payload


def test_duplicate_registration_returns_409(
    registered_user: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "full_name": "Duplicate Customer",
            "password": "AnotherStrongPassword123!",
        },
    )

    assert response.status_code == 409


def test_login_returns_access_token(
    registered_user: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["expires_in"] == 3600


def test_incorrect_password_returns_401(
    registered_user: dict[str, object],
) -> None:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 401


def test_authenticated_user_can_access_me(
    registered_user: dict[str, object],
) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": f"Bearer {token}",
        },
    )

    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]


def test_me_without_token_returns_401() -> None:
    response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_me_with_invalid_token_returns_401() -> None:
    response = client.get(
        "/api/v1/users/me",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
