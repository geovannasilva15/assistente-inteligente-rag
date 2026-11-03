import hashlib
import json
from pathlib import Path


def fingerprint(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.json")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_documents(directory: Path) -> list[dict]:
    documents = []
    for path in sorted(directory.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for key in ("id", "title", "organization", "url", "accessed", "license", "sections"):
            if not doc.get(key):
                raise ValueError(f"Documento {path.name}: campo ausente {key}.")
        for section in doc["sections"]:
            section["text"] = " ".join(section["text"].split())
            if not section.get("id") or not section.get("title") or not section["text"]:
                raise ValueError(f"Secao vazia em {path.name}.")
        documents.append(doc)
    if not documents or len({d["id"] for d in documents}) != len(documents):
        raise ValueError("Base vazia ou IDs de documento duplicados.")
    return documents


def split_documents(documents: list[dict], size: int = 90, overlap: int = 15) -> list[dict]:
    if not 0 <= overlap < size:
        raise ValueError("Use 0 <= overlap < size.")
    chunks = []
    for doc in documents:
        metadata = {k: v for k, v in doc.items() if k != "sections"}
        for section in doc["sections"]:
            words = section["text"].split()
            for start in range(0, len(words), size - overlap):
                chunks.append({
                    "id": f"{doc['id']}:{section['id']}:{start}",
                    "document_id": doc["id"], "section_id": section["id"],
                    "section": section["title"], "text": " ".join(words[start:start + size]),
                    "source": metadata,
                })
                if start + size >= len(words):
                    break
    if len({c['id'] for c in chunks}) != len(chunks):
        raise ValueError("IDs de trecho duplicados.")
    return chunks
