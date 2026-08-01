from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_categories() -> None:
    response = client.get("/api/v1/categories")

    assert response.status_code == 200

    categories = response.json()

    assert categories
    assert len({category["id"] for category in categories}) == len(categories)
    assert len({category["slug"] for category in categories}) == len(categories)
    assert all(category["product_count"] >= 0 for category in categories)

    category_slugs = {category["slug"] for category in categories}

    assert "laptops" in category_slugs
    assert "smartphones" in category_slugs
    assert "headphones" in category_slugs

    laptops = next(category for category in categories if category["slug"] == "laptops")

    assert laptops["name"] == "Laptops"
    assert laptops["product_count"] == 4


def test_list_products_with_pagination() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "page": 1,
            "page_size": 5,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert len(payload["items"]) == 5
    assert payload["page"] == 1
    assert payload["page_size"] == 5
    assert payload["total_items"] >= len(payload["items"])
    assert (
        payload["total_pages"]
        == (payload["total_items"] + payload["page_size"] - 1) // payload["page_size"]
    )


def test_product_pages_do_not_repeat_items() -> None:
    first_response = client.get(
        "/api/v1/products",
        params={
            "page": 1,
            "page_size": 5,
            "sort": "name_asc",
        },
    )
    second_response = client.get(
        "/api/v1/products",
        params={
            "page": 2,
            "page_size": 5,
            "sort": "name_asc",
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_ids = {item["id"] for item in first_response.json()["items"]}
    second_ids = {item["id"] for item in second_response.json()["items"]}

    assert first_ids.isdisjoint(second_ids)


def test_filter_products_by_category() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "category": "laptops",
            "page_size": 20,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total_items"] == 4
    assert len(payload["items"]) == 4

    assert all(item["category"]["slug"] == "laptops" for item in payload["items"])


def test_search_products() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "search": "Kairo",
            "page_size": 50,
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total_items"] > 0

    assert all(
        ("kairo" in item["name"].lower() or "kairo" in item["brand"].lower())
        for item in payload["items"]
    )


def test_filter_products_by_brand() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "brand": "Kairo",
            "page_size": 50,
        },
    )

    assert response.status_code == 200

    items = response.json()["items"]

    assert len(items) > 0

    assert all(item["brand"] == "Kairo" for item in items)


def test_filter_products_by_price_range() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "min_price": 3000,
            "max_price": 5000,
            "page_size": 50,
            "sort": "price_asc",
        },
    )

    assert response.status_code == 200

    items = response.json()["items"]

    assert len(items) > 0

    for item in items:
        effective_price = Decimal(item["effective_price"])

        assert Decimal(3000) <= effective_price <= Decimal(5000)


def test_sort_products_by_effective_price() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "sort": "price_asc",
            "page_size": 32,
        },
    )

    assert response.status_code == 200

    prices = [Decimal(item["effective_price"]) for item in response.json()["items"]]

    assert prices == sorted(prices)


def test_filter_products_in_stock() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "in_stock": True,
            "page_size": 50,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    items = payload["items"]

    assert len(items) == min(
        50,
        payload["total_items"],
    )
    assert all(item["available_quantity"] > 0 for item in items)

    assert all(item["in_stock"] is True and item["available_quantity"] > 0 for item in items)


def test_get_product_details() -> None:
    list_response = client.get(
        "/api/v1/products",
        params={"page_size": 1},
    )

    assert list_response.status_code == 200

    list_item = list_response.json()["items"][0]
    product_id = list_item["id"]

    detail_response = client.get(f"/api/v1/products/{product_id}")

    assert detail_response.status_code == 200

    product = detail_response.json()

    assert product["id"] == product_id
    assert product["name"] == list_item["name"]
    assert product["category"]["id"] == list_item["category"]["id"]
    assert len(product["images"]) >= 1
    assert product["inventory"]["available_quantity"] >= 0
    assert product["inventory"]["in_stock"] is True


def test_unknown_product_returns_404() -> None:
    response = client.get("/api/v1/products/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found."}


def test_invalid_product_id_returns_422() -> None:
    response = client.get("/api/v1/products/not-a-valid-uuid")

    assert response.status_code == 422


def test_invalid_price_range_returns_422() -> None:
    response = client.get(
        "/api/v1/products",
        params={
            "min_price": 100000,
            "max_price": 50000,
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "min_price cannot be greater than max_price."}


def test_page_size_above_limit_returns_422() -> None:
    response = client.get(
        "/api/v1/products",
        params={"page_size": 101},
    )

    assert response.status_code == 422
