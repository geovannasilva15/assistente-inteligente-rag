import os
import re

from .models import SearchResult
from .retrieval import tokenize


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def generate_local_answer(query: str, results: list[SearchResult]) -> str:
    if not results:
        return "Não encontrei informações suficientes nos documentos para responder com segurança."

    query_tokens = set(tokenize(query))
    candidates: list[tuple[int, str, str]] = []
    for result in results:
        for sentence in _sentences(result.chunk.text):
            overlap = len(query_tokens.intersection(tokenize(sentence)))
            if overlap:
                candidates.append((overlap, sentence, result.chunk.source))

    if not candidates:
        top = results[0].chunk
        return f"{top.text}\n\nFonte: [{top.source}]"

    selected: list[str] = []
    seen = set()
    for _, sentence, source in sorted(candidates, key=lambda item: item[0], reverse=True):
        key = sentence.lower()
        if key in seen:
            continue
        selected.append(f"{sentence} [{source}]")
        seen.add(key)
        if len(selected) == 3:
            break
    return " ".join(selected)


def generate_openai_answer(query: str, results: list[SearchResult]) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not results:
        return None

    try:
        from openai import OpenAI

        context = "\n\n".join(
            f"Fonte [{result.chunk.source}]\n{result.chunk.text}" for result in results
        )
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            instructions=(
                "Responda somente com base no contexto fornecido. Cite as fontes entre colchetes. "
                "Se o contexto não for suficiente, informe isso claramente."
            ),
            input=f"Contexto:\n{context}\n\nPergunta: {query}",
        )
        return response.output_text.strip()
    except Exception as error:
        print(f"Aviso: resposta externa indisponível ({error}). Usando modo local.")
        return None
