from pathlib import Path
from typing import Iterable

from .models import Chunk, Document


SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


def read_document(path: Path) -> Document:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Formato não suportado: {path.suffix}")

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as error:
            raise RuntimeError("Instale pypdf para processar arquivos PDF.") from error
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        text = path.read_text(encoding="utf-8")

    clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean_text:
        raise ValueError(f"O documento está vazio ou não contém texto extraível: {path.name}")
    return Document(source=path.name, text=clean_text)


def load_directory(directory: Path) -> list[Document]:
    paths = sorted(
        path for path in directory.iterdir() if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    return [read_document(path) for path in paths]


def split_document(document: Document, chunk_size: int = 900, overlap: int = 120) -> list[Chunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size deve ser maior que zero")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap deve ser maior ou igual a zero e menor que chunk_size")

    text = document.text
    chunks: list[Chunk] = []
    start = 0
    index = 1
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            paragraph_break = text.rfind("\n", start, end)
            sentence_break = text.rfind(". ", start, end)
            best_break = max(paragraph_break, sentence_break)
            if best_break > start + chunk_size // 2:
                end = best_break + (2 if best_break == sentence_break else 1)

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(Chunk(f"{document.source}:{index}", document.source, chunk_text))
            index += 1
        if end == len(text):
            break
        start = end - overlap
    return chunks


def split_documents(
    documents: Iterable[Document], chunk_size: int = 900, overlap: int = 120
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(split_document(document, chunk_size=chunk_size, overlap=overlap))
    return chunks
