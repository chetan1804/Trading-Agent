import pandas as pd
from fastapi import APIRouter, Query, Request
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features

router = APIRouter(prefix="/api", tags=["features"])


@router.get("/features/engineer")
async def engineer_feature_snapshot(
    request: Request,
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol.upper(), [])
    if stored_bars:
        samples = pd.DataFrame(stored_bars)
        samples["symbol"] = symbol.upper()
    else:
        samples = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 50), seed=7)
    engineered = engineer_features(samples)
    latest = engineered.tail(limit).reset_index(drop=True)
    excluded = {
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "data_source",
    }
    feature_columns = [column for column in latest.columns if column not in excluded]

    return {
        "symbol": symbol.upper(),
        "count": int(len(latest)),
        "feature_columns": feature_columns,
        "rows": [
            {
                "timestamp": row["timestamp"].isoformat(),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"]),
                **{
                    name: float(row[name]) if isinstance(row[name], (int, float)) else row[name]
                    for name in feature_columns
                    if name in row
                },
            }
            for row in latest.to_dict(orient="records")
        ],
    }
