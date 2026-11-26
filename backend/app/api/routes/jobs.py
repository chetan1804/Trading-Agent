from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from trading.jobs.service import execute_job

router = APIRouter(prefix="/api", tags=["jobs"])


class JobRequest(BaseModel):
    type: Literal["ai_research", "backtest"]
    symbol: str = Field(default="RELIANCE.NS", min_length=1, max_length=32)
    market_snapshot: dict[str, object] = Field(default_factory=dict)
    news: list[str] = Field(default_factory=list, max_length=100)
    documents: list[str] = Field(default_factory=list, max_length=100)
    limit: int = Field(default=120, ge=20, le=10000)
    initial_cash: float = Field(default=100000.0, gt=0)


async def _run_job(store: object, job_id: str, payload: dict[str, object]) -> None:
    await store.set_running(job_id)  # type: ignore[attr-defined]
    try:
        result = execute_job(payload)
        await store.set_succeeded(job_id, result)  # type: ignore[attr-defined]
    except (TypeError, ValueError, OverflowError) as error:
        await store.set_failed(job_id, str(error))  # type: ignore[attr-defined]


@router.post("/jobs")
async def create_job(
    payload: JobRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, object]:
    store = request.app.state.job_store
    job_id = str(uuid4())
    body = payload.model_dump()
    try:
        await store.enqueue(job_id, body)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="job queue is unavailable") from error
    if request.app.state.app_env == "test":
        background_tasks.add_task(_run_job, store, job_id, body)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> dict[str, object]:
    store = request.app.state.job_store
    try:
        record = await store.get(job_id)
    except RedisError as error:
        raise HTTPException(status_code=503, detail="job queue is unavailable") from error
    if record is None:
        raise HTTPException(status_code=404, detail="job not found")
    return record
