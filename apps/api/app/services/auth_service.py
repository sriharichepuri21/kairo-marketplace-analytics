from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
)
from app.models import User
from app.repositories import UserRepository
from app.schemas import UserCreate


class AuthService:
    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @classmethod
    def register_user(
        cls,
        database: Session,
        user_data: UserCreate,
    ) -> User:
        normalized_email = cls.normalize_email(
            str(user_data.email),
        )

        existing_user = UserRepository.get_by_email(
            database,
            normalized_email,
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=normalized_email,
            full_name=user_data.full_name.strip(),
            password_hash=hash_password(
                user_data.password.get_secret_value(),
            ),
            role="customer",
            is_active=True,
        )

        try:
            return UserRepository.create(
                database,
                user,
            )
        except IntegrityError:
            database.rollback()

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            ) from None

    @classmethod
    def authenticate_user(
        cls,
        database: Session,
        email: str,
        password: str,
    ) -> User | None:
        normalized_email = cls.normalize_email(email)

        user = UserRepository.get_by_email(
            database,
            normalized_email,
        )

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        return user
