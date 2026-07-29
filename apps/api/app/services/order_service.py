from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    CartItem,
    Inventory,
    Order,
    OrderItem,
    OrderStatusHistory,
    Product,
    User,
)
from app.repositories import OrderRepository
from app.schemas import (
    CheckoutRequest,
    OrderItemResponse,
    OrderResponse,
    OrderShippingAddressResponse,
    OrderStatusHistoryResponse,
)

MONEY_QUANTUM = Decimal("0.01")


class OrderService:
    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(MONEY_QUANTUM)

    @classmethod
    def _effective_price(
        cls,
        product: Product,
    ) -> Decimal:
        price = product.discount_price if product.discount_price is not None else product.price

        return cls._money(price)

    @staticmethod
    def _generate_order_number() -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%d")

        suffix = uuid4().hex[:12].upper()

        return f"KAIRO-{timestamp}-{suffix}"

    @classmethod
    def _to_response(
        cls,
        order: Order,
    ) -> OrderResponse:
        return OrderResponse(
            id=order.id,
            order_number=order.order_number,
            user_id=order.user_id,
            status=order.status,
            payment_status=(order.payment_status),
            currency_code=order.currency_code,
            subtotal=order.subtotal,
            shipping_amount=(order.shipping_amount),
            tax_amount=order.tax_amount,
            total_amount=order.total_amount,
            shipping_address=(
                OrderShippingAddressResponse(
                    full_name=(order.shipping_full_name),
                    phone=order.shipping_phone,
                    address_line_1=(order.shipping_address_line_1),
                    address_line_2=(order.shipping_address_line_2),
                    city=order.shipping_city,
                    state=order.shipping_state,
                    postal_code=(order.shipping_postal_code),
                    country_code=(order.shipping_country_code),
                )
            ),
            customer_note=order.customer_note,
            items=[
                OrderItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=(item.product_name),
                    product_slug=(item.product_slug),
                    product_brand=(item.product_brand),
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    created_at=item.created_at,
                )
                for item in order.items
            ],
            status_history=[
                OrderStatusHistoryResponse(
                    id=history.id,
                    status=history.status,
                    note=history.note,
                    created_at=(history.created_at),
                )
                for history in (order.status_history)
            ],
            created_at=order.created_at,
            updated_at=order.updated_at,
        )

    @staticmethod
    def _validate_product(
        product: Product | None,
        inventory: Inventory | None,
        quantity: int,
    ) -> None:
        if product is None:
            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=("A product in your cart no longer exists."),
            )

        if not product.is_active:
            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=(f"{product.name} is no longer available."),
            )

        if inventory is None:
            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=(f"{product.name} has no inventory record."),
            )

        if inventory.available_quantity < quantity:
            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=(
                    f"Only "
                    f"{inventory.available_quantity} "
                    f"units of {product.name} "
                    "are currently available."
                ),
            )

    @classmethod
    def checkout(
        cls,
        database: Session,
        current_user: User,
        checkout_data: CheckoutRequest,
    ) -> OrderResponse:
        try:
            address = OrderRepository.lock_address(
                database,
                current_user.id,
                checkout_data.shipping_address_id,
            )

            if address is None:
                raise HTTPException(
                    status_code=(status.HTTP_404_NOT_FOUND),
                    detail=("Shipping address not found."),
                )

            cart = OrderRepository.lock_cart(
                database,
                current_user.id,
            )

            if cart is None:
                raise HTTPException(
                    status_code=(status.HTTP_409_CONFLICT),
                    detail="Your cart is empty.",
                )

            cart_items = OrderRepository.lock_cart_items(
                database,
                cart.id,
            )

            if not cart_items:
                raise HTTPException(
                    status_code=(status.HTTP_409_CONFLICT),
                    detail="Your cart is empty.",
                )

            product_ids = sorted(
                {item.product_id for item in cart_items},
                key=str,
            )

            products = OrderRepository.lock_products(
                database,
                product_ids,
            )

            inventories = OrderRepository.lock_inventory(
                database,
                product_ids,
            )

            products_by_id = {product.id: product for product in products}

            inventory_by_product_id = {inventory.product_id: inventory for inventory in inventories}

            subtotal = Decimal("0.00")

            item_snapshots: list[
                tuple[
                    CartItem,
                    Product,
                    Inventory,
                    Decimal,
                    Decimal,
                ]
            ] = []

            for cart_item in cart_items:
                product = products_by_id.get(cart_item.product_id)

                inventory = inventory_by_product_id.get(cart_item.product_id)

                cls._validate_product(
                    product,
                    inventory,
                    cart_item.quantity,
                )

                assert product is not None
                assert inventory is not None

                unit_price = cls._effective_price(product)

                line_total = cls._money(unit_price * cart_item.quantity)

                subtotal += line_total

                item_snapshots.append(
                    (
                        cart_item,
                        product,
                        inventory,
                        unit_price,
                        line_total,
                    )
                )

            subtotal = cls._money(subtotal)

            shipping_amount = Decimal("0.00")
            tax_amount = Decimal("0.00")

            total_amount = cls._money(subtotal + shipping_amount + tax_amount)

            customer_note = checkout_data.customer_note

            if customer_note == "":
                customer_note = None

            order = Order(
                order_number=(cls._generate_order_number()),
                user_id=current_user.id,
                shipping_address_id=address.id,
                status="pending",
                payment_status="pending",
                currency_code="INR",
                subtotal=subtotal,
                shipping_amount=shipping_amount,
                tax_amount=tax_amount,
                total_amount=total_amount,
                shipping_full_name=(address.full_name),
                shipping_phone=address.phone,
                shipping_address_line_1=(address.address_line_1),
                shipping_address_line_2=(address.address_line_2),
                shipping_city=address.city,
                shipping_state=address.state,
                shipping_postal_code=(address.postal_code),
                shipping_country_code=(address.country_code),
                customer_note=customer_note,
            )

            database.add(order)
            database.flush()

            order_items = [
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    product_name=product.name,
                    product_slug=product.slug,
                    product_brand=product.brand,
                    quantity=cart_item.quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
                for (
                    cart_item,
                    product,
                    _inventory,
                    unit_price,
                    line_total,
                ) in item_snapshots
            ]

            status_history = OrderStatusHistory(
                order_id=order.id,
                status="pending",
                note="Order created.",
                created_by_user_id=(current_user.id),
            )

            database.add_all(
                [
                    *order_items,
                    status_history,
                ]
            )

            for (
                cart_item,
                _product,
                inventory,
                _unit_price,
                _line_total,
            ) in item_snapshots:
                inventory.available_quantity -= cart_item.quantity

            database.execute(delete(CartItem).where(CartItem.cart_id == cart.id))

            cart.updated_at = datetime.now(UTC)

            database.commit()

        except HTTPException:
            database.rollback()
            raise

        except IntegrityError:
            database.rollback()

            raise HTTPException(
                status_code=(status.HTTP_409_CONFLICT),
                detail=("Checkout could not be completed because of a conflicting update."),
            ) from None

        except Exception:
            database.rollback()
            raise

        saved_order = OrderRepository.get_for_user(
            database,
            current_user.id,
            order.id,
        )

        if saved_order is None:
            raise RuntimeError("Unable to reload the order.")

        return cls._to_response(saved_order)

    @classmethod
    def list_orders(
        cls,
        database: Session,
        current_user: User,
    ) -> list[OrderResponse]:
        orders = OrderRepository.list_for_user(
            database,
            current_user.id,
        )

        return [cls._to_response(order) for order in orders]

    @classmethod
    def get_order(
        cls,
        database: Session,
        current_user: User,
        order_id: UUID,
    ) -> OrderResponse:
        order = OrderRepository.get_for_user(
            database,
            current_user.id,
            order_id,
        )

        if order is None:
            raise HTTPException(
                status_code=(status.HTTP_404_NOT_FOUND),
                detail="Order not found.",
            )

        return cls._to_response(order)
