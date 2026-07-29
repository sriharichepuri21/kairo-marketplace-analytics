from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)


class AddressCreate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    full_name: str = Field(
        min_length=2,
        max_length=160,
    )
    phone: str = Field(
        min_length=7,
        max_length=32,
    )
    address_line_1: str = Field(
        min_length=3,
        max_length=255,
    )
    address_line_2: str | None = Field(
        default=None,
        max_length=255,
    )
    city: str = Field(
        min_length=2,
        max_length=120,
    )
    state: str = Field(
        min_length=2,
        max_length=120,
    )
    postal_code: str = Field(
        min_length=3,
        max_length=20,
    )
    country_code: str = Field(
        default="US",
        pattern=r"^[A-Za-z]{2}$",
    )
    is_default: bool = False


class AddressUpdate(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=160,
    )
    phone: str | None = Field(
        default=None,
        min_length=7,
        max_length=32,
    )
    address_line_1: str | None = Field(
        default=None,
        min_length=3,
        max_length=255,
    )
    address_line_2: str | None = Field(
        default=None,
        max_length=255,
    )
    city: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )
    state: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )
    postal_code: str | None = Field(
        default=None,
        min_length=3,
        max_length=20,
    )
    country_code: str | None = Field(
        default=None,
        pattern=r"^[A-Za-z]{2}$",
    )
    is_default: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "AddressUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one address field must be provided.")

        nullable_fields = {
            "address_line_2",
        }

        for field_name in self.model_fields_set:
            if field_name not in nullable_fields and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null.")

        return self


class AddressResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    user_id: UUID
    full_name: str
    phone: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    postal_code: str
    country_code: str
    is_default: bool
    created_at: datetime
    updated_at: datetime
