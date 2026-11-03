from functools import lru_cache
import json

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import Literal

from .config import ROOT, from_env
from .generation import ProviderError
from .retrieval import IndexUnavailable, Retriever
from .service import Service


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10, strict=True)
    mode: Literal["demo", "llm"] | None = None

    @field_validator("question")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("A pergunta nao pode estar vazia.")
        return value.strip()


def create_app(service=None, settings=None):
    settings = settings or from_env()
    app = FastAPI(title="AI Reliability Lab", version="1.0.0")

    @lru_cache(maxsize=1)
    def get_service():
        return service or Service(settings, Retriever(settings))

    @app.get("/health")
    def health():
        try:
            instance = get_service()
            return {"status": "ok", "index_ready": True, "mode": settings.mode,
                    "chunk_count": len(instance.retriever.manifest["chunks"])}
        except IndexUnavailable:
            raise HTTPException(503, "Execute python -m lab ingest antes de consultar.")

    @app.post("/ask")
    def ask(body: Question):
        try:
            return get_service().ask(body.question, body.top_k, body.mode)
        except IndexUnavailable as error:
            raise HTTPException(503, str(error)) from error
        except ProviderError as error:
            raise HTTPException(502, str(error)) from error
        except Exception as error:
            raise HTTPException(503, "Falha local ao consultar o indice ou carregar embeddings.") from error

    @app.get("/evaluations")
    def evaluations():
        report = settings.reports_dir / "latest.json"
        return json.loads(report.read_text(encoding="utf-8")) if report.exists() else {
            "status": "not_run", "message": "Execute python -m lab evaluate para gerar resultados reais."
        }

    @app.get("/")
    def home():
        return FileResponse(ROOT / "web" / "index.html")

    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    return app


app = create_app()
