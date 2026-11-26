from __future__ import annotations

import asyncio

from redis.asyncio import Redis
from trading.jobs.service import execute_job
from trading.jobs.store import RedisJobStore


async def main() -> None:
    import os

    redis = Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:56379/0"),
        decode_responses=True,
    )
    store = RedisJobStore(redis)
    try:
        while True:
            item = await store.claim()
            if item is None:
                continue
            job_id = str(item["id"])
            await store.set_running(job_id)
            try:
                result = execute_job(item["payload"])
                await store.set_succeeded(job_id, result)
            except (TypeError, ValueError, OverflowError) as error:
                await store.set_failed(job_id, str(error))
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
