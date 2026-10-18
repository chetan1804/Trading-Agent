from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SentimentAnalyzer:
    positive_keywords: set[str] = field(
        default_factory=lambda: {
            "beat",
            "beats",
            "beating",
            "growth",
            "guidance",
            "optimistic",
            "upbeat",
            "rally",
            "expands",
            "expansion",
            "strong",
            "surge",
            "improve",
            "improves",
            "higher",
            "demand",
            "confidence",
            "outperform",
            "upgrade",
            "raised",
            "raise",
            "bullish",
        }
    )
    negative_keywords: set[str] = field(
        default_factory=lambda: {
            "miss",
            "misses",
            "missing",
            "down",
            "decline",
            "declines",
            "drop",
            "drops",
            "weak",
            "slump",
            "slumps",
            "slow",
            "warn",
            "warning",
            "pessimistic",
            "cut",
            "cuts",
            "recession",
            "risk",
            "bearish",
            "concern",
            "concerns",
        }
    )

    def analyze(self, headlines: list[str] | None = None) -> dict[str, object]:
        items = [headline.strip() for headline in (headlines or []) if headline and headline.strip()]
        if not items:
            return {"score": 0.0, "sentiment": "neutral", "signals": []}

        score = 0.0
        signals: list[str] = []
        for headline in items:
            normalized = headline.lower()
            headline_score = 0.0
            for keyword in self.positive_keywords:
                if keyword in normalized:
                    headline_score += 0.2
                    signals.append(f"positive:{keyword}")
            for keyword in self.negative_keywords:
                if keyword in normalized:
                    headline_score -= 0.2
                    signals.append(f"negative:{keyword}")
            score += headline_score

        total_score = max(-1.0, min(1.0, score / max(len(items), 1)))
        if total_score > 0.2:
            sentiment = "bullish"
        elif total_score < -0.2:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "score": round(float(total_score), 4),
            "sentiment": sentiment,
            "signals": signals[:10],
            "headline_count": len(items),
        }
