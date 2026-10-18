from __future__ import annotations

from typing import Any

from trading.ai.sentiment import SentimentAnalyzer


class MarketAgent:
    def __init__(self, name: str = "market-research-agent") -> None:
        self.name = name

    def run(
        self,
        *,
        symbol: str,
        objective: str,
        market_snapshot: dict[str, Any] | None = None,
        news: list[str] | None = None,
    ) -> dict[str, Any]:
        snapshot = market_snapshot or {}
        price = float(snapshot.get("price", 0.0) or 0.0)
        change_pct = float(snapshot.get("change_pct", 0.0) or 0.0)
        volume = float(snapshot.get("volume", 0.0) or 0.0)
        headline_count = len(news or [])

        if change_pct > 0:
            trend = "bullish"
        elif change_pct < 0:
            trend = "bearish"
        else:
            trend = "neutral"

        plan = [
            f"Review the latest price action for {symbol.upper()}.",
            "Check trend strength and relative participation in volume.",
            "Compare fresh headlines against the technical setup.",
            "Flag risk triggers before recommending any exposure.",
        ]

        actions = [
            "confirm trend direction",
            "check volume confirmation",
            "review headline catalysts",
            "validate risk limits",
        ]

        if headline_count == 0:
            actions.append("request additional market context")

        sentiment = SentimentAnalyzer().analyze(news or [])

        return {
            "symbol": symbol.upper(),
            "agent": self.name,
            "status": "ok",
            "objective": objective,
            "plan": plan,
            "actions": actions,
            "sentiment": {
                "score": sentiment["score"],
                "sentiment": sentiment["sentiment"],
                "headline_count": sentiment["headline_count"],
                "signals": sentiment["signals"],
            },
            "signal": {
                "trend": trend,
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "news_count": headline_count,
            },
        }
