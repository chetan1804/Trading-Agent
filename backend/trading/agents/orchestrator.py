from __future__ import annotations

from datetime import UTC, datetime
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
        bar_interval_seconds = self._finite_number(snapshot.get("bar_interval_seconds"))
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
        if (
            snapshot.get("bar_interval_seconds") is not None
            and (bar_interval_seconds is None or bar_interval_seconds <= 0)
        ):
            data_gaps.append("Bar interval is invalid; using the default freshness review window.")
            bar_interval_seconds = None
        freshness = self._assess_freshness(
            snapshot.get("timestamp"), bar_interval_seconds=bar_interval_seconds
        )
        if freshness["status"] == "missing":
            data_gaps.append(
                "Market data timestamp is missing; its freshness cannot be assessed."
            )
        elif freshness["status"] == "unknown":
            data_gaps.append(
                "Market data timestamp is invalid or lacks a timezone; freshness is unknown."
            )
        elif freshness["status"] == "older_than_threshold":
            data_gaps.append(
                "Market data timestamp exceeds the freshness review window for the inferred bar interval."
            )
        elif freshness["status"] == "future_timestamp":
            data_gaps.append(
                "Market data timestamp is in the future; verify the source clock and data."
            )
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
        technical_read = self._interpret_indicators(indicators, price)
        observations.extend(technical_read["observations"])
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
                "market_data_freshness": freshness,
                "indicators": indicators,
                "headline_count": headline_count,
                "research_source_count": len(sources),
            },
            "indicators": indicators,
            "technical_read": technical_read,
            "observations": observations,
            "risks": technical_read["risks"] + [
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
    def _interpret_indicators(
        indicators: dict[str, float], price: float | None
    ) -> dict[str, list[str]]:
        """Describe common indicator thresholds as heuristics, without producing a trade signal."""
        observations: list[str] = []
        risks: list[str] = []
        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi >= 70:
                observations.append("RSI is in the conventional overbought zone (70 or higher).")
                risks.append("Elevated RSI can reflect strong momentum as well as a stretched move.")
            elif rsi <= 30:
                observations.append("RSI is in the conventional oversold zone (30 or lower).")
                risks.append("Low RSI does not establish that a decline has ended.")
            else:
                observations.append("RSI is between the conventional 30 and 70 thresholds.")

        fast_sma, slow_sma = indicators.get("sma_20"), indicators.get("sma_50")
        if fast_sma is not None and slow_sma is not None:
            if fast_sma > slow_sma:
                observations.append("SMA 20 is above SMA 50, a positive moving-average alignment.")
            elif fast_sma < slow_sma:
                observations.append("SMA 20 is below SMA 50, a negative moving-average alignment.")
            else:
                observations.append("SMA 20 and SMA 50 are equal.")

        macd = indicators.get("macd")
        if macd is not None:
            observations.append(
                f"MACD is {'above' if macd > 0 else 'below' if macd < 0 else 'at'} its zero line."
            )

        atr = indicators.get("atr")
        if atr is not None and price is not None and price > 0:
            atr_pct = atr / price * 100
            observations.append(f"ATR is {atr_pct:.2f}% of the supplied price.")
            risks.append("ATR describes recent price range; it does not predict the next move.")

        if indicators:
            observations.append(
                "These threshold readings are descriptive heuristics; they are not a validated "
                "forecast or a standalone trading rule."
            )
        return {"observations": observations, "risks": risks}

    @staticmethod
    def _assess_freshness(
        timestamp: object, *, bar_interval_seconds: float | None = None
    ) -> dict[str, Any]:
        """Report age against three inferred intervals, or a 24-hour fallback window."""
        threshold_hours = (
            3 * bar_interval_seconds / 3600 if bar_interval_seconds is not None else 24.0
        )
        if timestamp is None or timestamp == "":
            return {
                "timestamp": None,
                "age_hours": None,
                "threshold_hours": round(threshold_hours, 2),
                "status": "missing",
            }
        if not isinstance(timestamp, str):
            return {
                "timestamp": str(timestamp),
                "age_hours": None,
                "threshold_hours": round(threshold_hours, 2),
                "status": "unknown",
            }
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError:
            return {
                "timestamp": timestamp,
                "age_hours": None,
                "threshold_hours": round(threshold_hours, 2),
                "status": "unknown",
            }
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return {
                "timestamp": timestamp,
                "age_hours": None,
                "threshold_hours": round(threshold_hours, 2),
                "status": "unknown",
            }
        age_hours = (datetime.now(UTC) - parsed.astimezone(UTC)).total_seconds() / 3600
        if age_hours < 0:
            status = "future_timestamp"
        elif age_hours > threshold_hours:
            status = "older_than_threshold"
        else:
            status = "within_threshold"
        return {
            "timestamp": timestamp,
            "age_hours": round(age_hours, 2),
            "threshold_hours": round(threshold_hours, 2),
            "status": status,
        }

    @staticmethod
    def _finite_number(value: object) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        return number if math.isfinite(number) else None
