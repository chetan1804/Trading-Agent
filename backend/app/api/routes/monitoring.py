from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from trading.model_monitoring.monitor import ModelMonitor
from trading.monitoring.execution import ExecutionMonitor

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/monitoring/overview")
async def monitoring_overview(request: Request) -> dict[str, object]:
    broker = getattr(request.app.state, "paper_broker", None)
    if broker is None:
        raise HTTPException(status_code=503, detail="paper broker is not initialized")
    execution = ExecutionMonitor(broker)
    execution_snapshot = execution.snapshot()

    baseline = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 4.0],
            "feature_b": [10.0, 12.0, 14.0, 16.0],
            "label": [1, 0, 1, 0],
        }
    )
    live = pd.DataFrame(
        {
            "feature_a": [1.5, 2.5, 3.5, 4.5],
            "feature_b": [11.0, 13.0, 15.0, 17.0],
            "label": [1, 1, 0, 0],
        }
    )

    model_snapshot = ModelMonitor().evaluate(baseline, live)
    model_status = (
        "degraded" if model_snapshot["status"] == "critical" else model_snapshot["status"]
    )
    model_snapshot["status"] = model_status

    alerts: list[str] = []
    if execution_snapshot["stale_orders"]:
        alerts.append("A stale order is present in the execution queue.")
    if model_snapshot["status"] != "healthy":
        alerts.append(f"Model health is {model_snapshot['status']}.")
    if not alerts:
        alerts.append("No active monitoring alerts.")

    return {
        "status": "ok",
        "execution": execution_snapshot,
        "model": model_snapshot,
        "alerts": alerts,
    }
