from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLogRecord


class AuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, event: dict[str, object]) -> None:
        self.session.add(AuditLogRecord(**event))
        await self.session.commit()

    async def list_recent(self, limit: int = 100) -> list[dict[str, object]]:
        result = await self.session.execute(
            select(AuditLogRecord).order_by(AuditLogRecord.created_at.desc()).limit(limit)
        )
        return [
            {
                "id": row.id,
                "request_id": row.request_id,
                "actor": row.actor,
                "method": row.method,
                "path": row.path,
                "status_code": row.status_code,
                "created_at": row.created_at.isoformat(),
            }
            for row in result.scalars()
        ]
