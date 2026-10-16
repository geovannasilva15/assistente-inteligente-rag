from pathlib import Path

from .generation import generate_local_answer, generate_openai_answer
from .ingestion import load_directory, split_documents
from .models import SearchResult
from .retrieval import LocalRetriever


class RagAssistant:
    def __init__(self, knowledge_dir: Path, chunk_size: int = 900, overlap: int = 120):
        documents = load_directory(knowledge_dir)
        self.chunks = split_documents(documents, chunk_size=chunk_size, overlap=overlap)
        self.retriever = LocalRetriever(self.chunks)

    def ask(self, query: str, top_k: int = 4, use_openai: bool = True) -> tuple[str, list[SearchResult]]:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("A pergunta não pode estar vazia")
        results = self.retriever.search(clean_query, top_k=top_k)
        answer = generate_openai_answer(clean_query, results) if use_openai else None
        return answer or generate_local_answer(clean_query, results), results
