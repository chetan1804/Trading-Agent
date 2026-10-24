from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from trading.ml.trainer import SignalModelTrainer

router = APIRouter(prefix="/api", tags=["ml"])


class MLTrainRequest(BaseModel):
    features: dict[str, list[float]] = Field(default_factory=dict)
    labels: list[int] = Field(default_factory=list)
    train_fraction: float = Field(default=0.6, gt=0, lt=1)
    validation_fraction: float = Field(default=0.2, gt=0, lt=1)


@router.post("/ml/train")
async def train_ml(request: MLTrainRequest) -> dict[str, object]:
    trainer = SignalModelTrainer()
    try:
        return trainer.train(
            features=request.features,
            labels=request.labels,
            train_fraction=request.train_fraction,
            validation_fraction=request.validation_fraction,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
