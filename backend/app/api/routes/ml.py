from fastapi import APIRouter
from pydantic import BaseModel, Field
from trading.ml.trainer import SignalModelTrainer

router = APIRouter(prefix="/api", tags=["ml"])


class MLTrainRequest(BaseModel):
    features: dict[str, list[float]] = Field(default_factory=dict)
    labels: list[int] = Field(default_factory=list)


@router.post("/ml/train")
async def train_ml(request: MLTrainRequest) -> dict[str, object]:
    trainer = SignalModelTrainer()
    return trainer.train(features=request.features, labels=request.labels)
