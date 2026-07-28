from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Category, Inventory, Product, ProductImage


CATALOG: list[dict[str, Any]] = [
    {
        "category": "Laptops",
        "products": [
            {
                "name": "KairoBook Air 13",
                "brand": "Kairo",
                "price": "74999.00",
                "discount_price": "69999.00",
                "rating": "4.40",
                "stock": 24,
                "description": (
                    "Lightweight 13-inch laptop with 16 GB memory, fast solid-state "
                    "storage, and all-day battery life."
                ),
            },
            {
                "name": "KairoBook Pro 14",
                "brand": "Kairo",
                "price": "99999.00",
                "discount_price": "92999.00",
                "rating": "4.70",
                "stock": 16,
                "description": (
                    "Professional 14-inch laptop designed for development, analytics, "
                    "creative work, and demanding productivity."
                ),
            },
            {
                "name": "NovaCore Studio 15",
                "brand": "NovaCore",
                "price": "114999.00",
                "discount_price": None,
                "rating": "4.50",
                "stock": 11,
                "description": (
                    "High-performance creator laptop with a color-accurate display "
                    "and dedicated graphics."
                ),
            },
            {
                "name": "Vertex Gaming 16",
                "brand": "Vertex",
                "price": "139999.00",
                "discount_price": "129999.00",
                "rating": "4.60",
                "stock": 8,
                "description": (
                    "Gaming laptop with a high-refresh display, advanced cooling, "
                    "and dedicated graphics."
                ),
            },
        ],
    },
    {
        "category": "Smartphones",
        "products": [
            {
                "name": "Kairo One",
                "brand": "Kairo",
                "price": "44999.00",
                "discount_price": "41999.00",
                "rating": "4.30",
                "stock": 42,
                "description": (
                    "Balanced 5G smartphone with an OLED display, dual camera system, "
                    "and fast charging."
                ),
            },
            {
                "name": "Nova X1",
                "brand": "Nova",
                "price": "59999.00",
                "discount_price": "54999.00",
                "rating": "4.50",
                "stock": 31,
                "description": (
                    "Premium smartphone with a high-resolution camera, bright display, "
                    "and long-lasting battery."
                ),
            },
            {
                "name": "PixelWave Mini",
                "brand": "PixelWave",
                "price": "32999.00",
                "discount_price": None,
                "rating": "4.20",
                "stock": 37,
                "description": (
                    "Compact smartphone with reliable performance, clean software, "
                    "and a pocket-friendly design."
                ),
            },
            {
                "name": "Orbit Pro Max",
                "brand": "Orbit",
                "price": "79999.00",
                "discount_price": "74999.00",
                "rating": "4.70",
                "stock": 19,
                "description": (
                    "Flagship smartphone with a large display, advanced camera system, "
                    "and premium build quality."
                ),
            },
        ],
    },
    {
        "category": "Headphones",
        "products": [
            {
                "name": "EchoPods Lite",
                "brand": "Echo",
                "price": "4999.00",
                "discount_price": "3999.00",
                "rating": "4.10",
                "stock": 85,
                "description": (
                    "Compact wireless earbuds with clear calling, touch controls, "
                    "and dependable battery life."
                ),
            },
            {
                "name": "EchoPods Pro",
                "brand": "Echo",
                "price": "9999.00",
                "discount_price": "8499.00",
                "rating": "4.50",
                "stock": 57,
                "description": (
                    "Wireless earbuds with active noise cancellation, transparency "
                    "mode, and wireless charging."
                ),
            },
            {
                "name": "SoundArc Studio",
                "brand": "SoundArc",
                "price": "18999.00",
                "discount_price": None,
                "rating": "4.60",
                "stock": 22,
                "description": (
                    "Over-ear studio headphones with balanced sound, soft memory-foam "
                    "earcups, and wired listening support."
                ),
            },
            {
                "name": "BassCore 700",
                "brand": "BassCore",
                "price": "12999.00",
                "discount_price": "10999.00",
                "rating": "4.40",
                "stock": 34,
                "description": (
                    "Wireless over-ear headphones with deep bass, active noise "
                    "cancellation, and extended battery life."
                ),
            },
        ],
    },
    {
        "category": "Cameras",
        "products": [
            {
                "name": "Lumina Mirrorless X",
                "brand": "Lumina",
                "price": "84999.00",
                "discount_price": "79999.00",
                "rating": "4.60",
                "stock": 13,
                "description": (
                    "Mirrorless camera with interchangeable lenses, fast autofocus, "
                    "and high-resolution 4K video."
                ),
            },
            {
                "name": "Lumina Travel Z",
                "brand": "Lumina",
                "price": "49999.00",
                "discount_price": None,
                "rating": "4.30",
                "stock": 18,
                "description": (
                    "Compact travel camera with optical zoom, image stabilization, "
                    "and lightweight construction."
                ),
            },
            {
                "name": "FramePro Creator",
                "brand": "FramePro",
                "price": "109999.00",
                "discount_price": "102999.00",
                "rating": "4.70",
                "stock": 7,
                "description": (
                    "Creator-focused camera with advanced video tools, microphone "
                    "input, and a fully articulating display."
                ),
            },
            {
                "name": "SnapGo Action 5",
                "brand": "SnapGo",
                "price": "29999.00",
                "discount_price": "26999.00",
                "rating": "4.40",
                "stock": 29,
                "description": (
                    "Water-resistant action camera with stabilized video, voice "
                    "controls, and multiple mounting options."
                ),
            },
        ],
    },
    {
        "category": "Gaming",
        "products": [
            {
                "name": "PulseBox Wireless Controller",
                "brand": "PulseBox",
                "price": "5999.00",
                "discount_price": "4999.00",
                "rating": "4.40",
                "stock": 61,
                "description": (
                    "Wireless gaming controller with programmable buttons, vibration, "
                    "and multi-device support."
                ),
            },
            {
                "name": "Vertex Mechanical Keyboard",
                "brand": "Vertex",
                "price": "7499.00",
                "discount_price": "6499.00",
                "rating": "4.50",
                "stock": 43,
                "description": (
                    "Mechanical gaming keyboard with hot-swappable switches, "
                    "programmable lighting, and a compact layout."
                ),
            },
            {
                "name": "Orbit Gaming Mouse",
                "brand": "Orbit",
                "price": "3499.00",
                "discount_price": None,
                "rating": "4.30",
                "stock": 72,
                "description": (
                    "Lightweight gaming mouse with an adjustable sensor, programmable "
                    "buttons, and onboard profiles."
                ),
            },
            {
                "name": "NovaVision 27 Gaming Monitor",
                "brand": "NovaVision",
                "price": "27999.00",
                "discount_price": "24999.00",
                "rating": "4.60",
                "stock": 17,
                "description": (
                    "27-inch high-refresh gaming monitor with adaptive synchronization "
                    "and a low-response-time panel."
                ),
            },
        ],
    },
    {
        "category": "Wearables",
        "products": [
            {
                "name": "Kairo Watch S",
                "brand": "Kairo",
                "price": "14999.00",
                "discount_price": "12999.00",
                "rating": "4.30",
                "stock": 46,
                "description": (
                    "Everyday smartwatch with activity tracking, notifications, "
                    "sleep monitoring, and GPS."
                ),
            },
            {
                "name": "Kairo Watch Pro",
                "brand": "Kairo",
                "price": "24999.00",
                "discount_price": "22999.00",
                "rating": "4.60",
                "stock": 28,
                "description": (
                    "Premium smartwatch with advanced health tracking, offline maps, "
                    "and a durable metal case."
                ),
            },
            {
                "name": "PulseFit Band 3",
                "brand": "PulseFit",
                "price": "3999.00",
                "discount_price": "3499.00",
                "rating": "4.20",
                "stock": 93,
                "description": (
                    "Slim fitness band with heart-rate monitoring, workout tracking, "
                    "and multi-day battery life."
                ),
            },
            {
                "name": "Orbit Active Ring",
                "brand": "Orbit",
                "price": "18999.00",
                "discount_price": None,
                "rating": "4.40",
                "stock": 21,
                "description": (
                    "Compact smart ring for sleep, recovery, heart-rate, and daily "
                    "activity tracking."
                ),
            },
        ],
    },
    {
        "category": "Home Appliances",
        "products": [
            {
                "name": "AirPure Mini",
                "brand": "AirPure",
                "price": "11999.00",
                "discount_price": "9999.00",
                "rating": "4.30",
                "stock": 36,
                "description": (
                    "Compact air purifier with HEPA filtration, quiet operation, "
                    "and automatic air-quality sensing."
                ),
            },
            {
                "name": "BrewMate Coffee Maker",
                "brand": "BrewMate",
                "price": "8999.00",
                "discount_price": "7499.00",
                "rating": "4.40",
                "stock": 31,
                "description": (
                    "Programmable coffee maker with adjustable brew strength, "
                    "automatic scheduling, and a reusable filter."
                ),
            },
            {
                "name": "SmartBlend 900",
                "brand": "SmartBlend",
                "price": "6999.00",
                "discount_price": None,
                "rating": "4.20",
                "stock": 44,
                "description": (
                    "High-speed kitchen blender with multiple presets and "
                    "a durable glass blending jar."
                ),
            },
            {
                "name": "CleanBot S2",
                "brand": "CleanBot",
                "price": "29999.00",
                "discount_price": "26999.00",
                "rating": "4.50",
                "stock": 20,
                "description": (
                    "Robot vacuum with room mapping, scheduled cleaning, "
                    "and automatic charging."
                ),
            },
        ],
    },
    {
        "category": "Accessories",
        "products": [
            {
                "name": "Kairo GaN Charger 65W",
                "brand": "Kairo",
                "price": "3499.00",
                "discount_price": "2999.00",
                "rating": "4.50",
                "stock": 104,
                "description": (
                    "Compact multi-port gallium-nitride charger for laptops, "
                    "tablets, and smartphones."
                ),
            },
            {
                "name": "Kairo USB-C Hub 8-in-1",
                "brand": "Kairo",
                "price": "4999.00",
                "discount_price": "4299.00",
                "rating": "4.40",
                "stock": 76,
                "description": (
                    "USB-C hub with HDMI, card reader, Ethernet, USB ports, "
                    "and pass-through charging."
                ),
            },
            {
                "name": "UrbanShield Laptop Sleeve 14",
                "brand": "UrbanShield",
                "price": "1999.00",
                "discount_price": None,
                "rating": "4.20",
                "stock": 88,
                "description": (
                    "Padded water-resistant laptop sleeve with a soft interior "
                    "and accessory pocket."
                ),
            },
            {
                "name": "VoltMax Power Bank 20000",
                "brand": "VoltMax",
                "price": "3999.00",
                "discount_price": "3499.00",
                "rating": "4.30",
                "stock": 69,
                "description": (
                    "High-capacity power bank with fast charging, USB-C input/output, "
                    "and battery-level display."
                ),
            },
        ],
    },
]


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace('"', "")
        .replace("'", "")
        .replace(" ", "-")
        .replace("/", "-")
    )


def placeholder_image(product_name: str) -> str:
    label = product_name.replace(" ", "+")
    return f"https://placehold.co/800x600/png?text={label}"


def seed_catalog(session: Session) -> tuple[int, int]:
    category_count = 0
    product_count = 0

    for category_data in CATALOG:
        category_name = category_data["category"]
        category_slug = slugify(category_name)

        category = session.scalar(
            select(Category).where(Category.slug == category_slug)
        )

        if category is None:
            category = Category(
                name=category_name,
                slug=category_slug,
            )
            session.add(category)
            session.flush()
            category_count += 1
        else:
            category.name = category_name

        for product_data in category_data["products"]:
            product_slug = slugify(product_data["name"])

            product = session.scalar(
                select(Product).where(Product.slug == product_slug)
            )

            if product is None:
                product = Product(
                    category_id=category.id,
                    name=product_data["name"],
                    slug=product_slug,
                    description=product_data["description"],
                    brand=product_data["brand"],
                    price=Decimal(product_data["price"]),
                    discount_price=(
                        Decimal(product_data["discount_price"])
                        if product_data["discount_price"] is not None
                        else None
                    ),
                    average_rating=Decimal(product_data["rating"]),
                    is_active=True,
                )
                session.add(product)
                session.flush()
                product_count += 1
            else:
                product.category_id = category.id
                product.name = product_data["name"]
                product.description = product_data["description"]
                product.brand = product_data["brand"]
                product.price = Decimal(product_data["price"])
                product.discount_price = (
                    Decimal(product_data["discount_price"])
                    if product_data["discount_price"] is not None
                    else None
                )
                product.average_rating = Decimal(product_data["rating"])
                product.is_active = True

            inventory = session.get(Inventory, product.id)

            if inventory is None:
                inventory = Inventory(
                    product_id=product.id,
                    available_quantity=product_data["stock"],
                    reserved_quantity=0,
                )
                session.add(inventory)
            else:
                inventory.available_quantity = product_data["stock"]
                inventory.reserved_quantity = 0

            image = session.scalar(
                select(ProductImage).where(
                    ProductImage.product_id == product.id,
                    ProductImage.display_order == 0,
                )
            )

            if image is None:
                image = ProductImage(
                    product_id=product.id,
                    image_url=placeholder_image(product.name),
                    alt_text=product.name,
                    display_order=0,
                )
                session.add(image)
            else:
                image.image_url = placeholder_image(product.name)
                image.alt_text = product.name

    session.commit()
    return category_count, product_count


def main() -> None:
    session = SessionLocal()

    try:
        categories_created, products_created = seed_catalog(session)

        print("Kairo catalogue seed completed.")
        print(f"Categories created: {categories_created}")
        print(f"Products created: {products_created}")
        print("Expected catalogue totals: 8 categories and 32 products")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
