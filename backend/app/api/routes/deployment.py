from fastapi import APIRouter
from trading.deployment.status import DeploymentStatus

from app.config import get_settings

router = APIRouter(prefix="/api", tags=["deployment"])


@router.get("/deployment/status")
async def deployment_status() -> dict[str, object]:
    return DeploymentStatus(get_settings()).snapshot()
