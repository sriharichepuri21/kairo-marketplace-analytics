from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


EventType = Literal[
    "product_view",
    "product_search",
    "add_to_cart",
    "remove_from_cart",
    "checkout_started",
    "order_placed",
]


class CustomerEventCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    event_type: EventType

    session_id: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    product_id: UUID | None = None
    order_id: UUID | None = None

    properties: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(mode="after")
    def validate_event_fields(
        self,
    ) -> "CustomerEventCreate":
        product_events = {
            "product_view",
            "add_to_cart",
            "remove_from_cart",
        }

        if (
            self.event_type in product_events
            and self.product_id is None
        ):
            raise ValueError(
                "product_id is required for this event type."
            )

        if (
            self.event_type not in product_events
            and self.product_id is not None
        ):
            raise ValueError(
                "product_id is not allowed for this event type."
            )

        if (
            self.event_type == "order_placed"
            and self.order_id is None
        ):
            raise ValueError(
                "order_id is required for order_placed."
            )

        if (
            self.event_type != "order_placed"
            and self.order_id is not None
        ):
            raise ValueError(
                "order_id is only allowed for order_placed."
            )

        if self.event_type == "product_search":
            query = self.properties.get("query")

            if (
                not isinstance(query, str)
                or not query.strip()
            ):
                raise ValueError(
                    "properties.query is required for product_search."
                )

        if len(self.properties) > 50:
            raise ValueError(
                "properties cannot contain more than 50 keys."
            )

        return self


class CustomerEventResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID | None
    session_id: str | None
    event_type: EventType
    product_id: UUID | None
    order_id: UUID | None
    properties: dict[str, Any]
    occurred_at: datetime
