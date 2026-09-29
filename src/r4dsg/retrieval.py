"""Deterministic BM25 retrieval. The query boundary accepts only question text."""

from __future__ import annotations

import math
import re
from collections import Counter


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise TypeError("Retrieval requires a question string, not a QA record")
    return re.findall(r"\w+", text.casefold())


class Index:
    def __init__(self, documents: list[dict]):
        if not isinstance(documents, list):
            raise ValueError("Expected memory documents")
        self.documents = documents
        ids = [d["doc_id"] for d in documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate document IDs")
        self.counts = [Counter(tokenize(d["text"])) for d in documents]
        self.lengths = [sum(count.values()) for count in self.counts]
        self.average = sum(self.lengths) / max(len(documents), 1) or 1.0
        frequency = Counter(term for count in self.counts for term in count)
        n = len(documents)
        self.idf = {
            term: math.log(1 + (n - df + 0.5) / (df + 0.5)) for term, df in frequency.items()
        }

    def search(self, question: str, top_k: int = 8) -> list[dict]:
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be a positive integer")
        query = sorted(set(tokenize(question)))
        hits = []
        for doc, counts, length in zip(self.documents, self.counts, self.lengths):
            score = 0.0
            for term in query:
                frequency = counts.get(term, 0)
                if frequency:
                    score += (
                        self.idf[term]
                        * frequency
                        * 2.2
                        / (frequency + 1.2 * (0.25 + 0.75 * length / self.average))
                    )
            if score > 0:
                hits.append(
                    {
                        "doc_id": doc["doc_id"],
                        "score": score,
                        "stream_id": doc["stream_id"],
                        "start": doc["start"],
                        "end": doc["end"],
                    }
                )
        hits.sort(key=lambda h: (-h["score"], h["doc_id"]))
        return [{"rank": rank, **hit} for rank, hit in enumerate(hits[:top_k], 1)]
