from fastapi import APIRouter, Query
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
