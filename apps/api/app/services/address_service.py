from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Address, User
from app.repositories import AddressRepository
from app.schemas import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
)


class AddressService:
    @staticmethod
    def _normalize_values(
        values: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = values.copy()

        country_code = normalized.get("country_code")

        if isinstance(country_code, str):
            normalized["country_code"] = country_code.upper()

        if "address_line_2" in normalized and normalized["address_line_2"] == "":
            normalized["address_line_2"] = None

        return normalized

    @staticmethod
    def _get_owned_address(
        database: Session,
        current_user: User,
        address_id: UUID,
    ) -> Address:
        address = AddressRepository.get_for_user(
            database,
            current_user.id,
            address_id,
        )

        if address is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found.",
            )

        return address

    @staticmethod
    def _commit(
        database: Session,
    ) -> None:
        try:
            database.commit()
        except IntegrityError:
            database.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("The address could not be saved because of a conflicting update."),
            ) from None

    @staticmethod
    def _to_response(
        address: Address,
    ) -> AddressResponse:
        return AddressResponse.model_validate(address)

    @classmethod
    def list_addresses(
        cls,
        database: Session,
        current_user: User,
    ) -> list[AddressResponse]:
        addresses = AddressRepository.list_for_user(
            database,
            current_user.id,
        )

        return [cls._to_response(address) for address in addresses]

    @classmethod
    def get_address(
        cls,
        database: Session,
        current_user: User,
        address_id: UUID,
    ) -> AddressResponse:
        address = cls._get_owned_address(
            database,
            current_user,
            address_id,
        )

        return cls._to_response(address)

    @classmethod
    def create_address(
        cls,
        database: Session,
        current_user: User,
        address_data: AddressCreate,
    ) -> AddressResponse:
        has_existing_addresses = AddressRepository.has_any(
            database,
            current_user.id,
        )

        should_be_default = not has_existing_addresses or address_data.is_default

        if should_be_default:
            AddressRepository.clear_defaults(
                database,
                current_user.id,
            )

        values = cls._normalize_values(address_data.model_dump())

        values["is_default"] = should_be_default

        address = Address(
            user_id=current_user.id,
            **values,
        )

        AddressRepository.add(
            database,
            address,
        )

        cls._commit(database)
        database.refresh(address)

        return cls._to_response(address)

    @classmethod
    def update_address(
        cls,
        database: Session,
        current_user: User,
        address_id: UUID,
        address_data: AddressUpdate,
    ) -> AddressResponse:
        address = cls._get_owned_address(
            database,
            current_user,
            address_id,
        )

        values = cls._normalize_values(
            address_data.model_dump(
                exclude_unset=True,
            )
        )

        default_was_supplied = "is_default" in values

        requested_default = values.pop(
            "is_default",
            None,
        )

        if default_was_supplied and requested_default is False and address.is_default:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=("Set another address as default before unsetting this address."),
            )

        if requested_default is True:
            AddressRepository.clear_defaults(
                database,
                current_user.id,
                exclude_address_id=address.id,
            )

            address.is_default = True

        elif requested_default is False:
            address.is_default = False

        for field_name, value in values.items():
            setattr(
                address,
                field_name,
                value,
            )

        cls._commit(database)
        database.refresh(address)

        return cls._to_response(address)

    @classmethod
    def delete_address(
        cls,
        database: Session,
        current_user: User,
        address_id: UUID,
    ) -> None:
        address = cls._get_owned_address(
            database,
            current_user,
            address_id,
        )

        was_default = address.is_default

        AddressRepository.delete(
            database,
            address,
        )

        if was_default:
            replacement = AddressRepository.first_for_user(
                database,
                current_user.id,
            )

            if replacement is not None:
                replacement.is_default = True

        cls._commit(database)
