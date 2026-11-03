import json
import os
import uuid
from datetime import datetime, timezone

import numpy as np

from .config import ROOT, Settings
from .ingestion import fingerprint, load_documents, split_documents


class IndexUnavailable(RuntimeError):
    pass


class Encoder:
    """Embeddings ONNX locais; modelos e cache nao entram no Git."""
    def __init__(self, model: str):
        from fastembed import TextEmbedding
        self.model = TextEmbedding(model_name=model, cache_dir=str(ROOT / ".cache"), threads=2)

    def documents(self, texts):
        return np.array(list(self.model.passage_embed(texts)), dtype=np.float32)

    def query(self, text):
        return np.array(list(self.model.query_embed(text)), dtype=np.float32)[0]


def normalize(vectors):
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=-1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def build_index(settings: Settings, encoder=None) -> dict:
    chunks = split_documents(load_documents(settings.data_dir), settings.chunk_words, settings.overlap)
    encoder = encoder or Encoder(settings.model)
    vectors = normalize(encoder.documents([c["text"] for c in chunks]))
    if vectors.ndim != 2 or len(vectors) != len(chunks) or not np.isfinite(vectors).all():
        raise ValueError("Embeddings invalidos.")
    manifest = {
        "version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
        "model": settings.model, "chunk_words": settings.chunk_words, "overlap": settings.overlap,
        "corpus_sha256": fingerprint(settings.data_dir), "chunks": chunks,
    }
    # Um arquivo contem metadados e vetores: troca atomica evita misturar duas versoes.
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    temp = settings.index_dir / f".{uuid.uuid4().hex}.npz"
    try:
        np.savez_compressed(temp, vectors=vectors, manifest=json.dumps(manifest, ensure_ascii=False))
        os.replace(temp, settings.index_dir / "index.npz")
    finally:
        temp.unlink(missing_ok=True)
    return {k: v for k, v in manifest.items() if k != "chunks"} | {"chunk_count": len(chunks)}


class Retriever:
    def __init__(self, settings: Settings, encoder=None):
        self.settings, self.encoder = settings, encoder
        try:
            with np.load(settings.index_dir / "index.npz", allow_pickle=False) as saved:
                self.vectors = saved["vectors"].copy()
                self.manifest = json.loads(str(saved["manifest"]))
            expected = (settings.model, settings.chunk_words, settings.overlap, fingerprint(settings.data_dir))
            actual = tuple(self.manifest[k] for k in ("model", "chunk_words", "overlap", "corpus_sha256"))
            if actual != expected or len(self.vectors) != len(self.manifest["chunks"]):
                raise ValueError("Indice desatualizado.")
        except (OSError, ValueError, KeyError) as error:
            raise IndexUnavailable("Indice ausente, invalido ou desatualizado. Execute python -m lab ingest.") from error

    def search(self, question: str, top_k: int):
        if not 1 <= top_k <= 10:
            raise ValueError("top-k deve estar entre 1 e 10.")
        if self.encoder is None:
            self.encoder = Encoder(self.settings.model)
        query = normalize(self.encoder.query(question))
        scores = self.vectors @ query
        if not np.isfinite(scores).all():
            raise ValueError("Similaridades invalidas.")
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [self.manifest["chunks"][int(i)] | {"similarity": round(float(scores[i]), 6)} for i in order]
