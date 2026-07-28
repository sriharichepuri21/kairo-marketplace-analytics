from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas import (
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services import AuthService


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)

settings = get_settings()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer account",
)
def register(
    user_data: UserCreate,
    database: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    user = AuthService.register_user(
        database,
        user_data,
    )

    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and receive an access token",
)
def login(
    form_data: Annotated[
        OAuth2PasswordRequestForm,
        Depends(),
    ],
    database: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    user = AuthService.authenticate_user(
        database,
        email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(user.id)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=(settings.access_token_expire_minutes * 60),
    )
