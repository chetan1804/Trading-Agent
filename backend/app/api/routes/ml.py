from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from trading.ml.trainer import SignalModelTrainer

from app.repositories.models import ModelRegistryRepository

router = APIRouter(prefix="/api", tags=["ml"])


class MLTrainRequest(BaseModel):
    features: dict[str, list[float]] = Field(default_factory=dict)
    labels: list[int] = Field(default_factory=list)
    train_fraction: float = Field(default=0.6, gt=0, lt=1)
    validation_fraction: float = Field(default=0.2, gt=0, lt=1)


class MLPredictRequest(BaseModel):
    features: dict[str, float]


@router.post("/ml/train")
async def train_ml(request: MLTrainRequest, http_request: Request) -> dict[str, object]:
    trainer = SignalModelTrainer()
    try:
        summary, artifact = trainer.train_with_artifact(
            features=request.features,
            labels=request.labels,
            train_fraction=request.train_fraction,
            validation_fraction=request.validation_fraction,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    async with http_request.app.state.database_session_factory() as session:
        await ModelRegistryRepository(session).save(summary, artifact)
    return summary


@router.get("/models")
async def list_models(http_request: Request) -> list[dict[str, object]]:
    async with http_request.app.state.database_session_factory() as session:
        models = await ModelRegistryRepository(session).list()
    return models


@router.post("/models/{model_version}/predict")
async def predict_ml(
    model_version: str, request: MLPredictRequest, http_request: Request
) -> dict[str, object]:
    async with http_request.app.state.database_session_factory() as session:
        model = await ModelRegistryRepository(session).get(model_version)
    if model is None:
        raise HTTPException(status_code=404, detail="registered model not found")
    try:
        prediction = SignalModelTrainer.predict(
            model.artifact,
            feature_names=model.feature_names,
            features=request.features,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"model_version": model_version, "prediction": prediction}


@router.post("/models/{model_version}/promote")
async def promote_ml(model_version: str, http_request: Request) -> dict[str, object]:
    async with http_request.app.state.database_session_factory() as session:
        model = await ModelRegistryRepository(session).promote(model_version)
    if model is None:
        raise HTTPException(status_code=404, detail="registered model not found")
    return {"model_version": model_version, "status": "active"}


@router.get("/models/active")
async def get_active_ml(http_request: Request) -> dict[str, object]:
    async with http_request.app.state.database_session_factory() as session:
        active = await ModelRegistryRepository(session).get_active()
    if active is None:
        raise HTTPException(status_code=404, detail="no active model has been promoted")
    model, promoted_at = active
    return {
        "model_version": model.model_version,
        "model_type": model.model_type,
        "promoted_at": promoted_at.isoformat(),
        "metrics": model.metrics,
    }


@router.post("/models/predict")
async def predict_active_ml(request: MLPredictRequest, http_request: Request) -> dict[str, object]:
    async with http_request.app.state.database_session_factory() as session:
        active = await ModelRegistryRepository(session).get_active()
    if active is None:
        raise HTTPException(status_code=404, detail="no active model has been promoted")
    model, _ = active
    try:
        prediction = SignalModelTrainer.predict(
            model.artifact,
            feature_names=model.feature_names,
            features=request.features,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"model_version": model.model_version, "prediction": prediction}
