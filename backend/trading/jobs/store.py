from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis


class InMemoryJobStore:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    async def enqueue(self, job_id: str, payload: dict[str, Any]) -> None:
        self.records[job_id] = {"id": job_id, "status": "queued", "payload": payload}

    async def set_running(self, job_id: str) -> None:
        if job_id in self.records:
            self.records[job_id]["status"] = "running"

    async def set_succeeded(self, job_id: str, result: dict[str, Any]) -> None:
        if job_id in self.records:
            self.records[job_id]["status"] = "succeeded"
            self.records[job_id]["result"] = result

    async def set_failed(self, job_id: str, error: str) -> None:
        if job_id in self.records:
            self.records[job_id]["status"] = "failed"
            self.records[job_id]["error"] = error

    async def get(self, job_id: str) -> dict[str, Any] | None:
        record = self.records.get(job_id)
        return dict(record) if record else None


class RedisJobStore:
    def __init__(self, redis: Redis, *, ttl_seconds: int = 86400) -> None:
        self.redis = redis
        self.ttl_seconds = ttl_seconds
        self.queue_key = "trading-agent:jobs:queue"

    async def enqueue(self, job_id: str, payload: dict[str, Any]) -> None:
        record = {"id": job_id, "status": "queued", "payload": payload}
        await self.redis.set(
            self.status_key(job_id),
            json.dumps(record),
            ex=self.ttl_seconds,
        )
        await self.redis.rpush(self.queue_key, json.dumps({"id": job_id, "payload": payload}))

    async def claim(self) -> dict[str, Any] | None:
        item = await self.redis.blpop(self.queue_key, timeout=5)
        if item is None:
            return None
        return json.loads(item[1])

    async def set_running(self, job_id: str) -> None:
        await self._update(job_id, "running")

    async def set_succeeded(self, job_id: str, result: dict[str, Any]) -> None:
        await self._update(job_id, "succeeded", result=result)

    async def set_failed(self, job_id: str, error: str) -> None:
        await self._update(job_id, "failed", error=error)

    async def get(self, job_id: str) -> dict[str, Any] | None:
        raw = await self.redis.get(self.status_key(job_id))
        return json.loads(raw) if raw else None

    async def _update(
        self,
        job_id: str,
        status: str,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        record = await self.get(job_id)
        if record is None:
            return
        record["status"] = status
        if result is not None:
            record["result"] = result
        if error is not None:
            record["error"] = error
        await self.redis.set(
            self.status_key(job_id),
            json.dumps(record),
            ex=self.ttl_seconds,
        )

    @staticmethod
    def status_key(job_id: str) -> str:
        return f"trading-agent:jobs:{job_id}"
