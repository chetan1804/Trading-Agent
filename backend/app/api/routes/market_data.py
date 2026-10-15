from fastapi import APIRouter, Query
from trading.data.synthetic import generate_synthetic_ohlcv

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
