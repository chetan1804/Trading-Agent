from __future__ import annotations

import re
from typing import Any


class RAGResearchAssistant:
    def answer(self, *, query: str, documents: list[str]) -> dict[str, Any]:
        if not query:
            raise ValueError("query must not be empty")

        normalized_documents = [doc.strip() for doc in documents if doc and doc.strip()]
        if not normalized_documents:
            return {
                "status": "ok",
                "query": query,
                "answer": "No source documents were provided for this query.",
                "top_hits": [],
            }

        query_tokens = self._tokenize(query)
        scored = []
        for doc in normalized_documents:
            doc_tokens = self._tokenize(doc)
            overlap = len(query_tokens.intersection(doc_tokens))
            keyword_bonus = sum(
                1
                for token in {
                    "management",
                    "demand",
                    "guidance",
                    "outlook",
                    "cash",
                    "execution",
                    "margins",
                    "growth",
                }
                if token in query_tokens and token in doc_tokens
            )
            scored.append((doc, overlap + keyword_bonus))

        top_hits = [doc for doc, _ in sorted(scored, key=lambda item: item[1], reverse=True)[:3]]
        answer = top_hits[0]
        if len(top_hits) > 1:
            answer = (
                "The most relevant context suggests: "
                f"{top_hits[0]} Additional context also points to {top_hits[1]}."
            )

        return {
            "status": "ok",
            "query": query,
            "answer": answer,
            "top_hits": top_hits,
        }

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z]+", value.lower()) if token}
