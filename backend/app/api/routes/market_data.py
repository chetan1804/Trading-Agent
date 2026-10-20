from __future__ import annotations

from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field, model_validator
from trading.data.synthetic import generate_synthetic_ohlcv


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
        items.append({
            "id": f"news-{symbol.lower()}-{idx}",
            "headline": headline,
            "sentiment": sentiment,
            "source": "synthetic-market-feed",
        })
    return items

router = APIRouter(prefix="/api", tags=["market-data"])


@router.get("/market-data/quote")
async def market_data_quote(symbol: str = "DEMO") -> dict[str, object]:
    data = generate_synthetic_ohlcv(symbol=symbol, periods=50, seed=7)
    latest = data.iloc[-1]
    return {
        "symbol": str(latest["symbol"]),
        "timestamp": latest["timestamp"].isoformat(),
        "last_price": float(latest["close"]),
        "close": float(latest["close"]),
        "open": float(latest["open"]),
        "high": float(latest["high"]),
        "low": float(latest["low"]),
    }


@router.get("/market-data/history")
async def market_data_history(
    request: Request,
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=500),
) -> dict[str, object]:
    symbol_upper = symbol.upper()
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        records = list(stored_bars)[-limit:]
    else:
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
        "count": len(records),
        "data": records,
    }


@router.get("/market-data/news")
async def market_data_news(
    symbol: str = "DEMO",
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
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=500),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol.upper(), [])
    if stored_bars:
        frame = pd.DataFrame(stored_bars[-limit:])
    else:
        frame = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 1), seed=7)
    null_count = int(frame.isna().sum().sum())
    issues: list[str] = []

    if frame.empty:
        issues.append("No rows returned for the requested symbol")
    if null_count > 0:
        issues.append(f"Null values detected: {null_count}")
    if (frame["close"] <= 0).any():
        issues.append("Non-positive close prices detected")
    if (frame["volume"] <= 0).any():
        issues.append("Non-positive volume detected")

    return {
        "symbol": symbol.upper(),
        "rows": int(len(frame)),
        "null_count": null_count,
        "issues": issues,
        "valid": not issues,
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


class MarketDataIngestRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    bars: list[OHLCVBar] = Field(default_factory=list)


@router.post("/market-data/ingest")
async def market_data_ingest(
    request: Request,
    payload: MarketDataIngestRequest,
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", None)
    if store is None:
        store = {}
        request.app.state.market_data_store = store

    symbol = payload.symbol.upper()
    accepted = [bar.model_dump(mode="json") for bar in payload.bars]

    store.setdefault(symbol, []).extend(accepted)
    return {
        "status": "ok",
        "symbol": symbol,
        "stored": len(accepted),
        "total_records": len(store[symbol]),
    }


@router.get("/market-data/stored")
async def market_data_stored(
    request: Request,
    symbol: str = "DEMO",
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
