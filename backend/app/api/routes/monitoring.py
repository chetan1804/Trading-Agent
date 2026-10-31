from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from trading.monitoring.execution import ExecutionMonitor

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/monitoring/overview")
async def monitoring_overview(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper broker is not initialized")
    execution = ExecutionMonitor(broker)
    execution_snapshot = execution.snapshot()

    # Model drift and quality require real, time-aligned prediction observations
    # and their eventual labels. The platform does not collect those yet, so do
    # not report metrics from synthetic examples as if they described a model.
    model_snapshot = {
        "status": "unavailable",
        "reason": "Production prediction and outcome observations are not being collected.",
        "feature_drift": None,
        "accuracy": None,
        "precision": None,
        "recall": None,
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
