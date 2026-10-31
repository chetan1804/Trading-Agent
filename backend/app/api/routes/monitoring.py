from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from trading.model_monitoring.monitor import ModelMonitor
from trading.monitoring.execution import ExecutionMonitor

from app.repositories.models import ModelRegistryRepository

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/monitoring/overview")
async def monitoring_overview(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper broker is not initialized")
    execution = ExecutionMonitor(broker)
    execution_snapshot = execution.snapshot()

    model_snapshot: dict[str, object]
    # Test mode intentionally has no external database; production and local
    # development use the persisted registry and prediction observations.
    if request.app.state.app_env == "test":
        model_snapshot = ModelMonitor().evaluate_observations({}, [])
    else:
        async with request.app.state.database_session_factory() as session:
            registry = ModelRegistryRepository(session)
            active = await registry.get_active()
            if active is None:
                model_snapshot = {
                    **ModelMonitor().evaluate_observations({}, []),
                    "reason": "No active registered model is available for monitoring.",
                }
            else:
                model, _ = active
                baseline, records = await registry.monitoring_data(model.model_version)
                observations = [
                    {
                        "features": record.features,
                        "prediction": record.prediction,
                        "actual_label": record.actual_label,
                    }
                    for record in records
                ]
                model_snapshot = {
                    "model_version": model.model_version,
                    **ModelMonitor().evaluate_observations(baseline, observations),
                }

    alerts: list[str] = []
    if execution_snapshot["stale_orders"]:
        alerts.append("A stale order is present in the execution queue.")
    if model_snapshot["status"] == "critical":
        alerts.append("Model health is critical.")
    elif model_snapshot["status"] == "warning":
        alerts.append("Model health is degraded.")
    if not alerts:
        alerts.append("No active monitoring alerts.")

    return {
        "status": "ok",
        "execution": execution_snapshot,
        "model": model_snapshot,
        "alerts": alerts,
    }
