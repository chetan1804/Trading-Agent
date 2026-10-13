from __future__ import annotations

from typing import Any


class MarketResearchAssistant:
    def __init__(self, provider: str = "local") -> None:
        self.provider = provider

    @classmethod
    def default(cls) -> MarketResearchAssistant:
        return cls(provider="local")

    def generate_report(
        self,
        *,
        symbol: str,
        market_snapshot: dict[str, Any] | None = None,
        news: list[str] | None = None,
        documents: list[str] | None = None,
    ) -> dict[str, Any]:
        snapshot = market_snapshot or {}
        price = float(snapshot.get("price", 0.0) or 0.0)
        change_pct = float(snapshot.get("change_pct", 0.0) or 0.0)
        volume = float(snapshot.get("volume", 0.0) or 0.0)

        news_items = [item for item in (news or []) if item]
        doc_items = [item for item in (documents or []) if item]

        if change_pct > 0:
            momentum = "bullish"
            direction = "uptrend"
        elif change_pct < 0:
            momentum = "bearish"
            direction = "downtrend"
        else:
            momentum = "neutral"
            direction = "sideways"

        summary_parts = [
            f"{symbol.upper()} is showing {momentum} momentum with a {direction} bias.",
            f"The latest price is ${price:,.2f} on volume of {volume:,.0f}.",
        ]
        if news_items:
            summary_parts.append(f"News flow supports: {news_items[0]}")
        if doc_items:
            summary_parts.append(f"Research context: {doc_items[0]}")

        summary = " ".join(summary_parts)

        risks = []
        if change_pct > 3.0:
            risks.append("Extended momentum can reverse quickly if volume fades.")
        elif change_pct < -3.0:
            risks.append("Downside pressure may accelerate without support from volume.")
        else:
            risks.append("Price action remains mixed; watch confirmation before adding exposure.")

        if not news_items:
            risks.append(
                "No fresh headline catalysts are available, so sentiment remains "
                "less certain."
            )

        highlights = [
            f"Price: ${price:,.2f}",
            f"Change: {change_pct:+.2f}%",
            f"Volume: {volume:,.0f}",
        ]
        if news_items:
            highlights.append(f"Headline: {news_items[0]}")
        if doc_items:
            highlights.append(f"Context: {doc_items[0]}")

        return {
            "symbol": symbol.upper(),
            "provider": self.provider,
            "summary": summary,
            "risks": risks,
            "highlights": highlights[:5],
            "confidence": "medium" if summary else "low",
            "market_snapshot": snapshot,
        }
