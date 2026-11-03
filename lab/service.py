import time
from datetime import datetime, timezone

from .generation import LLM, estimate_cost

NO_EVIDENCE = "Não encontrei evidência suficiente nos documentos disponíveis para responder a esta pergunta."


class Service:
    def __init__(self, settings, retriever, llm=None):
        self.settings, self.retriever = settings, retriever
        self.llm = llm or LLM(settings)

    def ask(self, question, top_k=None, mode=None):
        started = time.perf_counter()
        s = self.settings
        question = question.strip()
        if not question or len(question) > 1000:
            raise ValueError("Use uma pergunta entre 1 e 1000 caracteres.")
        mode = mode or s.mode
        if mode not in {"demo", "llm"}:
            raise ValueError("Modo invalido.")
        k = s.top_k if top_k is None else top_k
        retrieved = self.retriever.search(question, k)
        context = [c for c in retrieved if c["similarity"] >= s.min_similarity]
        answer, ids, usage = NO_EVIDENCE, [], {}
        if context:
            if mode == "demo":
                # Extracao literal: sem fingir que houve geracao por LLM.
                answer = "\n\n".join(f"{c['text']} [{c['id']}]" for c in context)
                ids = [c["id"] for c in context]
            else:
                generated, ids, usage = self.llm.answer(question, context)
                answer = generated or NO_EVIDENCE
        def tokens(key):
            value = usage.get(key)
            return value if type(value) is int and value >= 0 else None
        input_tokens, output_tokens = tokens("prompt_tokens"), tokens("completion_tokens")
        return {
            "answer": answer, "mode": mode, "answerable": bool(ids), "cited_ids": ids,
            "sources": [c for c in context if c["id"] in ids], "retrieved": retrieved,
            "metrics": {
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "retrieved_count": len(retrieved), "context_count": len(context),
                "input_tokens": input_tokens, "output_tokens": output_tokens,
                "estimated_cost": estimate_cost(input_tokens, output_tokens, s),
            },
            "config": {"top_k": k, "min_similarity": s.min_similarity, "embedding_model": s.model,
                       "chunk_words": s.chunk_words, "overlap": s.overlap,
                       "llm_model": s.llm_model if mode == "llm" else None,
                       "corpus_sha256": self.retriever.manifest["corpus_sha256"],
                       "index_created_at": self.retriever.manifest["created_at"]},
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
