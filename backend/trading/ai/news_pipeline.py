from __future__ import annotations

import hashlib
import html
import re
from datetime import UTC, datetime

from trading.ai.sentiment import SentimentAnalyzer


def process_article(article: dict[str, object]) -> dict[str, object]:
    """Normalize a supplied headline and derive an explainable lexical sentiment."""
    symbol = str(article["symbol"]).strip().upper()
    source = str(article["source"]).strip()
    raw_headline = re.sub(r"<[^>]*>", " ", str(article["headline"]))
    headline = re.sub(r"\s+", " ", html.unescape(raw_headline)).strip()
    if not symbol or not source or not headline:
        raise ValueError("symbol, source, and headline must contain text")
    published_at = article["published_at"]
    if not isinstance(published_at, datetime):
        raise TypeError("published_at must be a datetime")
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=UTC)
    else:
        published_at = published_at.astimezone(UTC)

    analysis = SentimentAnalyzer().analyze([headline])
    digest_input = "|".join((symbol, source.casefold(), headline.casefold()))
    content_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()
    score = float(analysis["score"])
    return {
        "id": content_hash,
        "content_hash": content_hash,
        "symbol": symbol,
        "source": source[:128],
        "headline": headline[:1000],
        "published_at": published_at,
        "sentiment": str(analysis["sentiment"]),
        "sentiment_score": score,
        "confidence": abs(score),
        "created_at": datetime.now(UTC),
    }
