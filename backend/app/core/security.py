from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request, status


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    settings = request.app.state.settings
    if not settings.api_auth_enabled:
        return
    expected = settings.api_key.get_secret_value() if settings.api_key is not None else ""
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
