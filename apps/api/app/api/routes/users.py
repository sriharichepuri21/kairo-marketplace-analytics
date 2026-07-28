from fastapi import APIRouter

from app.api.dependencies.auth import CurrentUser
from app.schemas import UserResponse


router = APIRouter(
    prefix="/api/v1/users",
    tags=["Users"],
)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user",
)
def get_me(
    current_user: CurrentUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)
