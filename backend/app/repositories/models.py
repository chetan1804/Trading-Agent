from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActiveModelRecord, ModelPredictionRecord, RegisteredModel


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
            "feature_baseline": summary["feature_baseline"],
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

    async def promote(self, model_version: str) -> RegisteredModel | None:
        model = await self.get(model_version)
        if model is None:
            return None
        statement = insert(ActiveModelRecord).values(
            slot="default",
            model_version=model_version,
            promoted_at=datetime.now(UTC),
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[ActiveModelRecord.slot],
                set_={
                    "model_version": statement.excluded.model_version,
                    "promoted_at": statement.excluded.promoted_at,
                },
            )
        )
        await self.session.commit()
        return model

    async def get_active(self) -> tuple[RegisteredModel, datetime] | None:
        result = await self.session.execute(
            select(RegisteredModel, ActiveModelRecord.promoted_at)
            .join(
                ActiveModelRecord,
                ActiveModelRecord.model_version == RegisteredModel.model_version,
            )
            .where(ActiveModelRecord.slot == "default")
        )
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def record_prediction(
        self, *, model_version: str, features: dict[str, float], prediction: int
    ) -> str:
        record_id = str(uuid4())
        self.session.add(
            ModelPredictionRecord(
                id=record_id,
                model_version=model_version,
                features=features,
                prediction=prediction,
                actual_label=None,
                predicted_at=datetime.now(UTC),
            )
        )
        await self.session.commit()
        return record_id

    async def record_outcome(self, prediction_id: str, actual_label: int) -> bool | None:
        record = await self.session.get(ModelPredictionRecord, prediction_id)
        if record is None:
            return None
        if record.actual_label is not None:
            return record.actual_label == actual_label
        record.actual_label = actual_label
        record.outcome_at = datetime.now(UTC)
        await self.session.commit()
        return True

    async def monitoring_data(
        self, model_version: str
    ) -> tuple[dict[str, float], list[ModelPredictionRecord]]:
        model = await self.get(model_version)
        result = await self.session.execute(
            select(ModelPredictionRecord)
            .where(ModelPredictionRecord.model_version == model_version)
            .order_by(ModelPredictionRecord.predicted_at.desc())
            .limit(500)
        )
        return (model.feature_baseline if model is not None else {}, list(result.scalars()))

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
            "feature_baseline": record.feature_baseline,
        }
