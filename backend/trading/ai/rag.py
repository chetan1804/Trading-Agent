from __future__ import annotations

import re
from typing import Any


class RAGResearchAssistant:
    def answer(self, *, query: str, documents: list[str]) -> dict[str, Any]:
        if not query:
            raise ValueError("query must not be empty")

        normalized_documents = [
            {"source_id": f"document-{index}", "text": doc.strip(), "source_index": index}
            for index, doc in enumerate(documents, start=1)
            if doc and doc.strip()
        ]
        if not normalized_documents:
            return {
                "status": "ok",
                "query": query,
                "answer": "No source documents were provided for this query.",
                "top_hits": [],
                "sources": [],
                "citations": [],
            }

        query_tokens = self._tokenize(query)
        scored = []
        for document in normalized_documents:
            doc_tokens = self._tokenize(document["text"])
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
            score = overlap + keyword_bonus
            if score:
                scored.append({**document, "score": score})

        ranked = sorted(scored, key=lambda item: (-item["score"], item["source_index"]))[:3]
        if not ranked:
            return {
                "status": "no_relevant_sources",
                "query": query,
                "answer": "No supplied source contained terms relevant to this query.",
                "top_hits": [],
                "sources": [],
                "citations": [],
            }

        top_hits = [item["text"] for item in ranked]
        cited_sources = ranked[:2]
        citations = [item["source_id"] for item in cited_sources]
        answer = " ".join(
            f'{item["text"]} [{item["source_id"]}]' for item in ranked[:2]
        )
        sources = [
            {
                "source_id": item["source_id"],
                "document_index": item["source_index"],
                "excerpt": item["text"],
                "relevance_score": item["score"],
            }
            for item in ranked
        ]

        return {
            "status": "ok",
            "query": query,
            "answer": answer,
            "top_hits": top_hits,
            "sources": sources,
            "citations": citations,
        }

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z]+", value.lower()) if token}
