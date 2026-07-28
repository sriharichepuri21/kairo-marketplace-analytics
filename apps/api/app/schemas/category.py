from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategorySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class CategoryResponse(CategorySummary):
    product_count: int
