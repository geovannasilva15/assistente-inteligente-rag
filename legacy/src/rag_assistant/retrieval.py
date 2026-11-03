import math
import re
from collections import Counter
from typing import Iterable

from .models import Chunk, SearchResult


TOKEN_PATTERN = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
STOPWORDS = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do", "dos",
    "e", "em", "é", "na", "nas", "no", "nos", "o", "os", "para", "por", "que",
    "se", "um", "uma",
}


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


class LocalRetriever:
    def __init__(self, chunks: Iterable[Chunk]):
        self.chunks = list(chunks)
        self._vectors = [Counter(tokenize(chunk.text)) for chunk in self.chunks]
        self._document_frequency = Counter()
        for vector in self._vectors:
            self._document_frequency.update(vector.keys())

    def _idf(self, token: str) -> float:
        total = len(self.chunks)
        frequency = self._document_frequency.get(token, 0)
        return math.log((total + 1) / (frequency + 1)) + 1

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        if top_k <= 0:
            raise ValueError("top_k deve ser maior que zero")
        query_vector = Counter(tokenize(query))
        if not query_vector or not self.chunks:
            return []

        weighted_query = {token: count * self._idf(token) for token, count in query_vector.items()}
        query_norm = math.sqrt(sum(value * value for value in weighted_query.values()))
        results: list[SearchResult] = []
        for chunk, vector in zip(self.chunks, self._vectors):
            weighted_chunk = {token: count * self._idf(token) for token, count in vector.items()}
            chunk_norm = math.sqrt(sum(value * value for value in weighted_chunk.values()))
            if not chunk_norm:
                continue
            dot_product = sum(
                weighted_query.get(token, 0.0) * value for token, value in weighted_chunk.items()
            )
            score = dot_product / (query_norm * chunk_norm)
            if score > 0:
                results.append(SearchResult(chunk=chunk, score=score))
        return sorted(results, key=lambda result: result.score, reverse=True)[:top_k]
