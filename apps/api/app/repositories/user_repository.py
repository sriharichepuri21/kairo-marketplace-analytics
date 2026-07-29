from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class UserRepository:
    @staticmethod
    def get_by_email(
        database: Session,
        email: str,
    ) -> User | None:
        statement = select(User).where(
            User.email == email,
        )

        return database.scalar(statement)

    @staticmethod
    def get_by_id(
        database: Session,
        user_id: UUID,
    ) -> User | None:
        return database.get(User, user_id)

    @staticmethod
    def create(
        database: Session,
        user: User,
    ) -> User:
        database.add(user)
        database.commit()
        database.refresh(user)

        return user
