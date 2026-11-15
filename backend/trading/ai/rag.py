from __future__ import annotations

import math
import re
from typing import Any

_CHUNK_WORDS = 160
_CHUNK_OVERLAP = 30
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


class RAGResearchAssistant:
    def answer(
        self,
        *,
        query: str,
        documents: list[str] | None = None,
        sources: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not query:
            raise ValueError("query must not be empty")

        source_documents = [
            {"source_id": f"document-{index}", "text": doc}
            for index, doc in enumerate(documents or [], start=1)
        ]
        source_documents.extend(sources or [])
        chunks = []
        for source_index, document in enumerate(source_documents, start=1):
            text = document.get("text", "").strip()
            if not text:
                continue
            source_id = document.get("source_id", f"document-{source_index}")
            words = text.split()
            step = _CHUNK_WORDS - _CHUNK_OVERLAP
            for chunk_index, offset in enumerate(range(0, len(words), step)):
                chunk_words = words[offset : offset + _CHUNK_WORDS]
                if not chunk_words:
                    continue
                chunks.append(
                    {
                        "source_id": source_id,
                        "text": " ".join(chunk_words),
                        "source_index": source_index,
                        "chunk_index": chunk_index,
                    }
                )
                if offset + _CHUNK_WORDS >= len(words):
                    break

        if not chunks:
            return {
                "status": "ok",
                "query": query,
                "answer": "No source documents were provided for this query.",
                "top_hits": [],
                "sources": [],
                "citations": [],
            }

        query_tokens = self._tokenize(query)
        tokenized_chunks = [self._tokenize(chunk["text"]) for chunk in chunks]
        document_frequency = {
            token: sum(token in tokens for tokens in tokenized_chunks) for token in query_tokens
        }
        scored = []
        for chunk, tokens in zip(chunks, tokenized_chunks, strict=True):
            score = sum(
                (1 + math.log((len(chunks) + 1) / (document_frequency[token] + 1)))
                for token in query_tokens
                if token in tokens
            )
            if score > 0:
                scored.append({**chunk, "score": score})

        ranked = sorted(
            scored,
            key=lambda item: (-item["score"], item["source_index"], item["chunk_index"]),
        )[:3]
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
        citations = list(dict.fromkeys(item["source_id"] for item in ranked[:2]))
        answer = " ".join(f"{item['text']} [{item['source_id']}]" for item in ranked[:2])
        sources = [
            {
                "source_id": item["source_id"],
                "document_index": item["source_index"],
                "chunk_index": item["chunk_index"],
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
        return {
            token
            for token in re.findall(r"[a-zA-Z]+", value.lower())
            if token and token not in _STOPWORDS
        }
