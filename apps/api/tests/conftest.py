from collections.abc import Generator

import pytest

from app.core.database import SessionLocal
from scripts.seed_catalog import seed_catalog


@pytest.fixture(scope="session", autouse=True)
def ensure_catalog_is_seeded() -> Generator[None, None, None]:
    """
    Ensure catalogue integration tests always have the expected records.

    The seed function is idempotent, so running it repeatedly does not
    create duplicate categories or products.
    """
    database = SessionLocal()

    try:
        seed_catalog(database)
        yield
    finally:
        database.close()
