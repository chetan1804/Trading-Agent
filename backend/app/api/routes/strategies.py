import pandas as pd
from fastapi import APIRouter, Query, Request
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

router = APIRouter(prefix="/api", tags=["strategies"])


@router.get("/strategies/generate")
async def generate_strategy_signals(
    request: Request,
    symbol: str = "DEMO",
    limit: int = Query(default=20, ge=1, le=200),
) -> dict[str, object]:
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol.upper(), [])
    if stored_bars:
        market_data = pd.DataFrame(stored_bars)
        market_data["symbol"] = symbol.upper()
    else:
        market_data = generate_synthetic_ohlcv(
            symbol=symbol,
            periods=max(limit, 50),
            seed=7,
        )
    feature_frame = engineer_features(market_data)
    strategy = MovingAverageCrossoverStrategy(fast_window=20, slow_window=50)
    signals = strategy.generate_signals(feature_frame)
    latest = signals[-limit:]

    return {
        "symbol": symbol.upper(),
        "count": int(len(latest)),
        "strategy_id": strategy.strategy_id,
        "signals": [
            {
                "timestamp": signal.timestamp.isoformat(),
                "action": signal.action,
                "confidence": float(signal.confidence),
                "reason": signal.reason,
            }
            for signal in latest
        ],
    }
