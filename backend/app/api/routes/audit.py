from fastapi import APIRouter, Depends, Query, Request

from app.core.security import require_api_key
from app.repositories.audit_logs import AuditLogRepository

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit-logs")
async def list_audit_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    _auth: None = Depends(require_api_key),
) -> dict[str, object]:
    if request.app.state.app_env == "test":
        events = list(request.app.state.audit_events)
        return {"count": len(events[-limit:]), "events": events[-limit:]}
    async with request.app.state.database_session_factory() as session:
        events = await AuditLogRepository(session).list_recent(limit)
    return {"count": len(events), "events": events}
