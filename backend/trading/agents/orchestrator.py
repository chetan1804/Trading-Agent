from __future__ import annotations

import math
from typing import Any

from trading.ai.rag import RAGResearchAssistant
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
        documents: list[str] | None = None,
        research_sources: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        snapshot = market_snapshot or {}
        indicator_fields = ("rsi", "macd", "sma_20", "sma_50", "ema_20", "atr", "volatility")
        numeric_fields = ("price", "change_pct", "volume", *indicator_fields)
        parsed = {key: self._finite_number(snapshot.get(key)) for key in numeric_fields}
        invalid_fields = [
            key
            for key in numeric_fields
            if key in snapshot and snapshot[key] is not None and parsed[key] is None
        ]
        price = parsed["price"]
        change_pct = parsed["change_pct"]
        volume = parsed["volume"]
        headline_count = len(news or [])

        if change_pct is None:
            trend = "undetermined"
        elif change_pct > 0:
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
        research_context = RAGResearchAssistant().answer(
            query=objective,
            documents=documents or [],
            sources=research_sources or [],
        )
        data_gaps = []
        if not snapshot:
            data_gaps.append("No market snapshot was supplied.")
        if not news:
            data_gaps.append("No headlines were supplied; news sentiment is unavailable.")
        if not research_context["sources"]:
            data_gaps.append("No relevant research-document excerpts were found.")

        if invalid_fields:
            data_gaps.append(
                "Ignored non-numeric or non-finite market fields: "
                + ", ".join(sorted(invalid_fields))
                + "."
            )
        if "price" not in snapshot or parsed["price"] is None:
            data_gaps.append("A valid market price was not supplied.")
        indicators = {key: parsed[key] for key in indicator_fields if parsed[key] is not None}
        if parsed["change_pct"] is None:
            observations = [
                "No valid price-change field was supplied; no trend direction is inferred."
            ]
            data_gaps.append("A valid price-change percentage was not supplied.")
        else:
            observations = [
                f"Supplied price change is {change_pct:g}%; the snapshot suggests a "
                f"{trend} short-term direction."
            ]
        if indicators:
            observations.append(
                "Supplied indicators: "
                + ", ".join(f"{key}={value:g}" for key, value in sorted(indicators.items()))
                + "."
            )
        if headline_count:
            observations.append(
                f"The supplied headlines have {sentiment['sentiment']} lexical sentiment "
                f"(score {sentiment['score']})."
            )
        if research_context["sources"]:
            observations.append(
                f"Retrieved {len(research_context['sources'])} relevant research excerpt(s)."
            )

        sources = research_context["sources"]
        uncertainties = data_gaps + [
            "Input accuracy and freshness were not independently verified.",
            "Account state and configured risk limits were not evaluated by this "
            "research workflow.",
        ]
        final_analysis = (
            f"{symbol.upper()} short-term direction is {trend} in the supplied snapshot, with "
            f"{sentiment['sentiment']} headline sentiment. Treat these observations as "
            "preliminary; verify the cited sources and run the separate risk checks before "
            "considering any paper order."
        )

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
            "research_context": research_context,
            "data_used": {
                "market_snapshot": {
                    key: value for key, value in parsed.items() if value is not None
                },
                "indicators": indicators,
                "headline_count": headline_count,
                "research_source_count": len(sources),
            },
            "indicators": indicators,
            "observations": observations,
            "risks": [
                "This workflow does not execute account-level risk checks.",
                "This analysis is informational and does not approve or submit an order.",
            ],
            "uncertainties": uncertainties,
            "sources": sources,
            "final_analysis": final_analysis,
            "risks_and_uncertainties": uncertainties
            + ["This analysis is informational and does not approve or submit an order."],
            "signal": {
                "trend": trend,
                "price": price,
                "change_pct": change_pct,
                "volume": volume,
                "news_count": headline_count,
            },
        }

    @staticmethod
    def _finite_number(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
