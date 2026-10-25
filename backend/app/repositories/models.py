from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RegisteredModel


class ModelRegistryRepository:
    """Persist model metadata and its serialized estimator in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, summary: dict[str, Any], artifact: bytes) -> None:
        values = {
            "model_version": summary["model_version"],
            "model_type": summary["model_type"],
            "dataset_version": summary["dataset_version"],
            "training_date": datetime.fromisoformat(summary["training_date"]),
            "feature_names": summary["feature_names"],
            "hyperparameters": summary["hyperparameters"],
            "metrics": summary["metrics"],
            "validation_metrics": summary["validation_metrics"],
            "split_rows": summary["split_rows"],
            "artifact": artifact,
        }
        statement = insert(RegisteredModel).values(**values)
        await self.session.execute(
            statement.on_conflict_do_nothing(index_elements=[RegisteredModel.model_version])
        )
        await self.session.commit()

    async def list(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(RegisteredModel).order_by(RegisteredModel.training_date.desc())
        )
        return [self._metadata(record) for record in result.scalars()]

    async def get(self, model_version: str) -> RegisteredModel | None:
        result = await self.session.execute(
            select(RegisteredModel).where(RegisteredModel.model_version == model_version)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _metadata(record: RegisteredModel) -> dict[str, Any]:
        return {
            "model_version": record.model_version,
            "model_type": record.model_type,
            "dataset_version": record.dataset_version,
            "training_date": record.training_date.isoformat(),
            "feature_names": record.feature_names,
            "hyperparameters": record.hyperparameters,
            "metrics": record.metrics,
            "validation_metrics": record.validation_metrics,
            "split_rows": record.split_rows,
        }
