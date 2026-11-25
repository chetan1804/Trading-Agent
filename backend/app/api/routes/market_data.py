from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pandas as pd
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from pydantic import BaseModel, Field, model_validator
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.data.validation import validate_ohlcv

from app.core.security import require_api_key
from app.repositories.market_data import MarketDataRepository


def _headline_batch(symbol: str, limit: int) -> list[dict[str, object]]:
    ticker = symbol.upper()
    templates = [
        (
            "bullish",
            f"{ticker} expands production and guides revenue higher after strong demand.",
        ),
        (
            "neutral",
            f"{ticker} management says operating conditions remain steady as markets "
            "assess policy shifts.",
        ),
        (
            "bearish",
            f"{ticker} warns of margin pressure as input costs rise and demand "
            "softens in key regions.",
        ),
        (
            "bullish",
            f"Analysts remain optimistic on {ticker} after the latest earnings "
            "beat and raised outlook.",
        ),
        (
            "neutral",
            f"{ticker} continues to monitor demand trends while investors wait "
            "for the next catalyst.",
        ),
        (
            "bearish",
            f"{ticker} faces fresh headwinds as supply chain volatility weighs on guidance.",
        ),
    ]
    items = []
    for idx, (sentiment, headline) in enumerate(templates[: max(limit, 1)]):
        items.append(
            {
                "id": f"news-{symbol.lower()}-{idx}",
                "headline": headline,
                "sentiment": sentiment,
                "source": "synthetic-market-feed",
            }
        )
    return items


router = APIRouter(prefix="/api", tags=["market-data"])


@router.websocket("/market-data/stream")
async def market_data_stream(
    websocket: WebSocket,
    symbol: str = "RELIANCE.NS",
    max_updates: int = Query(default=10, ge=1, le=60),
    interval_ms: int = Query(default=1000, ge=100, le=60000),
) -> None:
    """Stream a bounded set of local quote snapshots; it does not place orders."""
    await websocket.accept()
    symbol_upper = symbol.upper()
    store = getattr(websocket.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        data_source = "ingested"
        bars = list(stored_bars)[-max_updates:]
    else:
        data_source = "synthetic"
        bars = (
            generate_synthetic_ohlcv(
                symbol=symbol_upper,
                periods=max(max_updates, 1),
                seed=7,
            )
            .tail(max_updates)
            .to_dict(orient="records")
        )

    try:
        for bar in bars:
            timestamp = pd.to_datetime(bar["timestamp"], utc=True)
            await websocket.send_json(
                {
                    "symbol": symbol_upper,
                    "data_source": data_source,
                    "timestamp": timestamp.isoformat(),
                    "last_price": float(bar["close"]),
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "volume": int(bar["volume"]),
                }
            )
            await asyncio.sleep(interval_ms / 1000)
    except WebSocketDisconnect:
        return


@router.get("/market-data/quote")
async def market_data_quote(request: Request, symbol: str = "RELIANCE.NS") -> dict[str, object]:
    symbol_upper = symbol.upper()
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        data_source = "ingested"
        latest = stored_bars[-1]
        timestamp = pd.to_datetime(latest["timestamp"], utc=True)
        values = {name: float(latest[name]) for name in ("open", "high", "low", "close")}
    else:
        data_source = "synthetic"
        latest = generate_synthetic_ohlcv(symbol=symbol_upper, periods=50, seed=7).iloc[-1]
        timestamp = latest["timestamp"]
        values = {name: float(latest[name]) for name in ("open", "high", "low", "close")}
    return {
        "symbol": symbol_upper,
        "data_source": data_source,
        "timestamp": timestamp.isoformat(),
        "last_price": values["close"],
        **values,
    }


@router.get("/market-data/history")
async def market_data_history(
    request: Request,
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=20, ge=1, le=500),
) -> dict[str, object]:
    symbol_upper = symbol.upper()
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        data_source = "ingested"
        records = list(stored_bars)[-limit:]
    else:
        data_source = "synthetic"
        samples = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 1), seed=7)
        history = samples.tail(limit).reset_index(drop=True)
        records = [
            {
                "timestamp": row["timestamp"].isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
            for row in history.to_dict(orient="records")
        ]
    return {
        "symbol": symbol_upper,
        "data_source": data_source,
        "count": len(records),
        "data": records,
    }


@router.get("/market-data/news")
async def market_data_news(
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=5, ge=1, le=10),
) -> dict[str, object]:
    items = _headline_batch(symbol=symbol, limit=limit)
    return {
        "symbol": symbol.upper(),
        "count": len(items),
        "items": items,
    }


@router.get("/market-data/validate")
async def market_data_validate(
    request: Request,
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=20, ge=1, le=500),
    expected_interval: str | None = Query(default=None, min_length=1, max_length=32),
    max_abs_close_return: float | None = Query(default=1.0, gt=0),
    check_outliers: bool = True,
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol.upper(), [])
    if stored_bars:
        data_source = "ingested"
        frame = pd.DataFrame(stored_bars[-limit:])
    else:
        data_source = "synthetic"
        frame = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 1), seed=7)
    try:
        report = validate_ohlcv(
            frame,
            expected_interval=expected_interval,
            max_abs_close_return=max_abs_close_return if check_outliers else None,
        )
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    null_count = int(report.data.isna().sum().sum())
    quality_issues = [
        {
            "code": issue.code,
            "severity": issue.severity,
            "message": issue.message,
            "row_count": issue.row_count,
        }
        for issue in report.issues
    ]

    return {
        "symbol": symbol.upper(),
        "data_source": data_source,
        "rows": int(len(report.data)),
        "null_count": null_count,
        "issues": [issue.message for issue in report.issues],
        "quality_issues": quality_issues,
        "expected_interval": expected_interval,
        "max_abs_close_return": max_abs_close_return if check_outliers else None,
        "outlier_check_enabled": check_outliers,
        "missing_intervals": sum(
            issue.row_count for issue in report.issues if issue.code == "data_gaps"
        ),
        "valid": not report.has_errors,
    }


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_price_range(self) -> OHLCVBar:
        if self.high < max(self.open, self.close):
            raise ValueError("high must be greater than or equal to open and close")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be less than or equal to open and close")
        return self

    @model_validator(mode="after")
    def normalize_timestamp(self) -> OHLCVBar:
        if self.timestamp.tzinfo is None:
            object.__setattr__(self, "timestamp", self.timestamp.replace(tzinfo=UTC))
        else:
            object.__setattr__(self, "timestamp", self.timestamp.astimezone(UTC))
        return self


class MarketDataIngestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    bars: list[OHLCVBar] = Field(default_factory=list, max_length=10_000)

    @model_validator(mode="after")
    def reject_duplicate_timestamps(self) -> MarketDataIngestRequest:
        timestamps = [bar.timestamp for bar in self.bars]
        if len(timestamps) != len(set(timestamps)):
            raise ValueError("bars must not contain duplicate timestamps after UTC normalization")
        return self


@router.post("/market-data/ingest")
async def market_data_ingest(
    request: Request,
    payload: MarketDataIngestRequest,
    _auth: None = Depends(require_api_key),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", None)
    if store is None:
        store = {}
        request.app.state.market_data_store = store

    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(status_code=422, detail="symbol cannot be blank")
    by_timestamp: dict[pd.Timestamp, dict[str, object]] = {}
    for bar in payload.bars:
        record = bar.model_dump()
        record["symbol"] = symbol
        by_timestamp[pd.Timestamp(bar.timestamp)] = record
    accepted = sorted(by_timestamp.values(), key=lambda bar: bar["timestamp"])

    session_factory = getattr(request.app.state, "database_session_factory", None)
    if session_factory is None:
        raise HTTPException(status_code=503, detail="market data storage is unavailable")
    async with session_factory() as session:
        await MarketDataRepository(session).upsert_many(accepted)

    bars_by_timestamp = {
        pd.to_datetime(bar["timestamp"], utc=True): bar for bar in store.get(symbol, [])
    }
    for bar in accepted:
        timestamp = pd.to_datetime(bar["timestamp"], utc=True)
        bars_by_timestamp[timestamp] = {
            "timestamp": timestamp.isoformat(),
            "symbol": symbol,
            "open": float(bar["open"]),
            "high": float(bar["high"]),
            "low": float(bar["low"]),
            "close": float(bar["close"]),
            "volume": int(bar["volume"]),
        }

    store[symbol] = sorted(
        bars_by_timestamp.values(),
        key=lambda bar: pd.to_datetime(bar["timestamp"], utc=True),
    )
    return {
        "status": "ok",
        "symbol": symbol,
        "stored": len(accepted),
        "total_records": len(store[symbol]),
    }


@router.get("/market-data/stored")
async def market_data_stored(
    request: Request,
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    symbol_upper = symbol.upper()
    records = list(store.get(symbol_upper, []))[-limit:]
    return {
        "symbol": symbol_upper,
        "count": len(records),
        "data": records,
    }
