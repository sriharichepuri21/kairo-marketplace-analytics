from uuid import UUID

from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models import (
    DataQualityRun,
)


class DataQualityRepository:
    @staticmethod
    def get_latest_run(
        database: Session,
    ) -> DataQualityRun | None:
        return database.scalar(
            select(DataQualityRun)
            .options(selectinload(DataQualityRun.checks))
            .order_by(
                DataQualityRun.started_at.desc(),
                DataQualityRun.created_at.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def get_run_by_id(
        database: Session,
        run_id: UUID,
    ) -> DataQualityRun | None:
        return database.scalar(
            select(DataQualityRun)
            .options(selectinload(DataQualityRun.checks))
            .where(DataQualityRun.id == run_id)
        )

    @staticmethod
    def list_runs(
        database: Session,
        *,
        page: int,
        page_size: int,
    ) -> tuple[
        list[DataQualityRun],
        int,
    ]:
        total_items = int(database.scalar(select(func.count(DataQualityRun.id))) or 0)

        runs = list(
            database.scalars(
                select(DataQualityRun)
                .order_by(
                    DataQualityRun.started_at.desc(),
                    DataQualityRun.created_at.desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
        )

        return runs, total_items
