from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    source: str
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source: str
    text: str


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float
