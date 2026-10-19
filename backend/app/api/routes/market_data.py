from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from trading.data.synthetic import generate_synthetic_ohlcv


def _headline_batch(symbol: str, limit: int) -> list[dict[str, object]]:
    templates = [
        ("bullish", f"{symbol.upper()} expands production and guides revenue higher after strong demand.") ,
        ("neutral", f"{symbol.upper()} management says operating conditions remain steady as markets assess policy shifts.") ,
        ("bearish", f"{symbol.upper()} warns of margin pressure as input costs rise and demand softens in key regions.") ,
        ("bullish", f"Analysts remain optimistic on {symbol.upper()} after the latest earnings beat and raised outlook."),
        ("neutral", f"{symbol.upper()} continues to monitor demand trends while investors wait for the next catalyst."),
        ("bearish", f"{symbol.upper()} faces fresh headwinds as supply chain volatility weighs on guidance."),
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
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=500),
) -> dict[str, object]:
    samples = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 1), seed=7)
    history = samples.tail(limit).reset_index(drop=True)
    return {
        "symbol": symbol.upper(),
        "count": int(len(history)),
        "data": [
            {
                "timestamp": row["timestamp"].isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
            }
            for row in history.to_dict(orient="records")
        ],
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
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=500),
) -> dict[str, object]:
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


class MarketDataIngestRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    bars: list[dict[str, object]] = Field(default_factory=list)


@router.post("/market-data/ingest")
async def market_data_ingest(request: Request, payload: MarketDataIngestRequest) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", None)
    if store is None:
        store = {}
        request.app.state.market_data_store = store

    symbol = payload.symbol.upper()
    accepted = []
    for bar in payload.bars:
        normalized = {
            "timestamp": str(bar.get("timestamp", "")),
            "open": float(bar.get("open", 0.0)),
            "high": float(bar.get("high", 0.0)),
            "low": float(bar.get("low", 0.0)),
            "close": float(bar.get("close", 0.0)),
            "volume": int(bar.get("volume", 0)),
        }
        accepted.append(normalized)

    store.setdefault(symbol, []).extend(accepted)
    return {
        "status": "ok",
        "symbol": symbol,
        "stored": len(accepted),
        "total_records": len(store[symbol]),
    }
