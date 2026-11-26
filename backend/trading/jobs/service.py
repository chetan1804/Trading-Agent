from __future__ import annotations

from typing import Any

from trading.ai.research import MarketResearchAssistant
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.moving_average import MovingAverageCrossoverStrategy


def execute_job(payload: dict[str, Any]) -> dict[str, Any]:
    job_type = payload.get("type")
    if job_type == "ai_research":
        assistant = MarketResearchAssistant.default()
        return assistant.generate_report(
            symbol=str(payload.get("symbol", "RELIANCE.NS")).upper(),
            market_snapshot=dict(payload.get("market_snapshot") or {}),
            news=list(payload.get("news") or []),
            documents=list(payload.get("documents") or []),
        )
    if job_type == "backtest":
        symbol = str(payload.get("symbol", "RELIANCE.NS")).upper()
        limit = int(payload.get("limit", 120))
        bars = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 120), seed=7)
        features = engineer_features(bars).tail(limit).reset_index(drop=True)
        result = BacktestEngine(
            BacktestConfig(initial_cash=float(payload.get("initial_cash", 100000)))
        ).run(features, MovingAverageCrossoverStrategy())
        metrics = calculate_performance_metrics(
            result.equity_curve,
            result.trades,
            turnover_value=result.turnover,
        )
        return {
            "symbol": symbol,
            "data_source": "synthetic",
            "strategy_id": "moving_average",
            "ending_equity": result.ending_equity,
            "trade_count": len(result.trades),
            "metrics": metrics,
        }
    raise ValueError(f"unsupported job type: {job_type}")
