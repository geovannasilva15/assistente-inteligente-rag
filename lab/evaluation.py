import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from importlib.metadata import version

from .config import ROOT
from .generation import cited_ids
from .retrieval import Retriever
from .service import Service


def retrieval_metrics(expected, retrieved):
    expected, retrieved = set(expected), set(retrieved)
    if not expected:
        return None, None
    found = expected & retrieved
    return int(bool(found)), len(found) / len(expected)


def average(values):
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def evaluate(service, cases, top_k):
    started = time.perf_counter()
    rows = []
    for case in cases:
        response = service.ask(case["question"], top_k=top_k, mode="demo")
        retrieved = {f"{c['document_id']}:{c['section_id']}" for c in response["retrieved"]}
        hit, recall = retrieval_metrics(case["expected_sources"], retrieved)
        ids = response["cited_ids"]
        context_ids = {c["id"] for c in response["retrieved"]
                       if c["similarity"] >= service.settings.min_similarity}
        valid = bool(ids) and set(ids) <= context_ids and set(cited_ids(response["answer"])) == set(ids)
        rows.append({
            "id": case["id"], "question": case["question"],
            "expected_answerable": case["answerable"], "actual_answerable": response["answerable"],
            "expected_sources": case["expected_sources"], "retrieved_sources": sorted(retrieved),
            "hit_at_k": hit, "recall_at_k": recall,
            "citations_valid": valid if response["answerable"] else None,
            "expected_points_present": [point for point in case["expected_points"]
                                        if point.casefold() in response["answer"].casefold()],
            "latency_ms": response["metrics"]["latency_ms"],
            "answer": response["answer"], "cited_ids": ids,
        })
    return {
        "top_k": top_k, "case_count": len(rows),
        "answerable_count": sum(r["expected_answerable"] for r in rows),
        "unanswerable_count": sum(not r["expected_answerable"] for r in rows),
        "hit_rate_at_k": average([r["hit_at_k"] for r in rows]),
        "mean_recall_at_k": average([r["recall_at_k"] for r in rows]),
        "unanswerable_abstention_rate": average([not r["actual_answerable"] for r in rows if not r["expected_answerable"]]),
        "answerable_response_rate": average([r["actual_answerable"] for r in rows if r["expected_answerable"]]),
        "citation_validity_rate": average([r["citations_valid"] for r in rows]),
        "mean_latency_ms": average([r["latency_ms"] for r in rows]),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3), "cases": rows,
    }


def run_evaluation(settings):
    source = ROOT / "data" / "evaluation.json"
    cases = json.loads(source.read_text(encoding="utf-8"))
    service = Service(settings, Retriever(settings))
    # Aquecimento explicito: comparacao nao cobra download/carga do modelo so do primeiro k.
    warmup_start = time.perf_counter()
    service.retriever.search("aquecimento da busca", 1)
    warmup_ms = (time.perf_counter() - warmup_start) * 1000
    now = datetime.now(timezone.utc)
    report = {
        "executed_at": now.isoformat(), "mode": "demo", "warmup_ms": warmup_ms,
        "config": {"embedding_model": settings.model, "min_similarity": settings.min_similarity,
                   "chunk_words": settings.chunk_words, "overlap": settings.overlap,
                   "corpus_sha256": service.retriever.manifest["corpus_sha256"],
                   "index_created_at": service.retriever.manifest["created_at"],
                   "evaluation_sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "environment": {"python": platform.python_version(), "platform": platform.system(),
                        "fastembed": version("fastembed"), "numpy": version("numpy")},
        "runs": [evaluate(service, cases, k) for k in (3, 5)],
        "limitations": "16 casos didáticos, uma execução por configuração, ordem fixa 3 depois 5, modelo aquecido. "
                       "Sem avaliação de correção semântica por juiz LLM. Citações válidas e recuperação não provam "
                       "veracidade. Pontos esperados são apenas busca literal diagnóstica. Tempos variam por máquina.",
    }
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    content = json.dumps(report, ensure_ascii=False, indent=2)
    (settings.reports_dir / f"evaluation-{now.strftime('%Y%m%dT%H%M%S%fZ')}.json").write_text(content, encoding="utf-8")
    (settings.reports_dir / "latest.json").write_text(content, encoding="utf-8")
    return report
