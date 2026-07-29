from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Cart, CartItem, Product, User
from app.repositories import CartRepository
from app.schemas import (
    CartItemCreate,
    CartItemResponse,
    CartItemUpdate,
    CartProductResponse,
    CartResponse,
)


class CartService:
    @staticmethod
    def _effective_price(product: Product) -> Decimal:
        if product.discount_price is not None:
            return product.discount_price

        return product.price

    @staticmethod
    def _available_quantity(product: Product) -> int:
        if product.inventory is None:
            return 0

        return product.inventory.available_quantity

    @staticmethod
    def _primary_image(product: Product) -> str | None:
        if not product.images:
            return None

        return product.images[0].image_url

    @staticmethod
    def _touch(cart: Cart) -> None:
        cart.updated_at = datetime.now(UTC)

    @classmethod
    def _validate_quantity(
        cls,
        product: Product,
        quantity: int,
    ) -> None:
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product is no longer available.",
            )

        available_quantity = cls._available_quantity(product)

        if available_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product is currently out of stock.",
            )

        if quantity > available_quantity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(f"Only {available_quantity} units are currently available."),
            )

    @staticmethod
    def _find_item(
        cart: Cart,
        item_id: UUID,
    ) -> CartItem:
        item = next(
            (cart_item for cart_item in cart.items if cart_item.id == item_id),
            None,
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        return item

    @classmethod
    def _to_response(
        cls,
        cart: Cart,
    ) -> CartResponse:
        response_items: list[CartItemResponse] = []
        subtotal = Decimal("0.00")
        total_quantity = 0

        for item in cart.items:
            product = item.product
            unit_price = cls._effective_price(product)
            line_total = unit_price * item.quantity
            subtotal += line_total
            total_quantity += item.quantity

            response_items.append(
                CartItemResponse(
                    id=item.id,
                    product=CartProductResponse(
                        id=product.id,
                        name=product.name,
                        slug=product.slug,
                        brand=product.brand,
                        image_url=cls._primary_image(product),
                    ),
                    quantity=item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                    available_quantity=(cls._available_quantity(product)),
                )
            )

        return CartResponse(
            id=cart.id,
            user_id=cart.user_id,
            items=response_items,
            total_quantity=total_quantity,
            subtotal=subtotal,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
        )

    @classmethod
    def get_cart(
        cls,
        database: Session,
        current_user: User,
    ) -> CartResponse:
        cart = CartRepository.get_or_create(
            database,
            current_user.id,
        )

        return cls._to_response(cart)

    @classmethod
    def add_item(
        cls,
        database: Session,
        current_user: User,
        item_data: CartItemCreate,
    ) -> CartResponse:
        cart = CartRepository.get_or_create(
            database,
            current_user.id,
        )

        product = CartRepository.get_active_product(
            database,
            item_data.product_id,
        )

        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found.",
            )

        existing_item = next(
            (item for item in cart.items if item.product_id == product.id),
            None,
        )

        new_quantity = item_data.quantity

        if existing_item is not None:
            new_quantity += existing_item.quantity

        cls._validate_quantity(product, new_quantity)

        if existing_item is None:
            database.add(
                CartItem(
                    cart_id=cart.id,
                    product_id=product.id,
                    quantity=new_quantity,
                )
            )
        else:
            existing_item.quantity = new_quantity

        cls._touch(cart)

        saved_cart = CartRepository.save_cart(
            database,
            cart,
        )

        return cls._to_response(saved_cart)

    @classmethod
    def update_item(
        cls,
        database: Session,
        current_user: User,
        item_id: UUID,
        item_data: CartItemUpdate,
    ) -> CartResponse:
        cart = CartRepository.get_by_user_id(
            database,
            current_user.id,
        )

        if cart is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        item = cls._find_item(cart, item_id)

        cls._validate_quantity(
            item.product,
            item_data.quantity,
        )

        item.quantity = item_data.quantity
        cls._touch(cart)

        saved_cart = CartRepository.save_cart(
            database,
            cart,
        )

        return cls._to_response(saved_cart)

    @classmethod
    def remove_item(
        cls,
        database: Session,
        current_user: User,
        item_id: UUID,
    ) -> None:
        cart = CartRepository.get_by_user_id(
            database,
            current_user.id,
        )

        if cart is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found.",
            )

        item = cls._find_item(cart, item_id)

        database.delete(item)
        cls._touch(cart)
        CartRepository.commit(database)

    @classmethod
    def clear_cart(
        cls,
        database: Session,
        current_user: User,
    ) -> None:
        cart = CartRepository.get_by_user_id(
            database,
            current_user.id,
        )

        if cart is None:
            return

        for item in list(cart.items):
            database.delete(item)

        cls._touch(cart)
        CartRepository.commit(database)
