from fastapi import FastAPI
from pydantic import BaseModel

from app.api.routes.health import router as health_router
from app.api.routes.products import router as products_router
from app.core.config import get_settings


settings = get_settings()


class RootResponse(BaseModel):
    service: str
    version: str
    documentation: str


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for the Kairo marketplace shopping application."
    ),
)

app.include_router(health_router)
app.include_router(products_router)


@app.get(
    "/",
    response_model=RootResponse,
    tags=["Root"],
    summary="Get API information",
)
def root() -> RootResponse:
    return RootResponse(
        service=settings.app_name,
        version=settings.app_version,
        documentation="/docs",
    )
