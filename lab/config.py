import math
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_dir: Path = ROOT / "data" / "documents"
    index_dir: Path = ROOT / "storage"
    reports_dir: Path = ROOT / "reports"
    model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    chunk_words: int = 90
    overlap: int = 15
    top_k: int = 3
    min_similarity: float = 0.45
    mode: str = "demo"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    llm_model: str = ""
    input_price: float | None = None
    output_price: float | None = None
    currency: str = "USD"

    def __post_init__(self):
        if not 0 <= self.overlap < self.chunk_words or not 1 <= self.top_k <= 10:
            raise ValueError("Configuracao de trechos ou top-k invalida.")
        if not -1 <= self.min_similarity <= 1 or self.mode not in {"demo", "llm"}:
            raise ValueError("Modo ou limiar invalido.")
        for price in (self.input_price, self.output_price):
            if price is not None and (price < 0 or not math.isfinite(price)):
                raise ValueError("Preco deve ser finito e nao negativo.")


def from_env() -> Settings:
    load_dotenv(ROOT / ".env")
    def price(name):
        value = os.getenv(name, "").strip()
        return float(value) if value else None
    return Settings(
        model=os.getenv("EMBEDDING_MODEL", Settings.model),
        chunk_words=int(os.getenv("CHUNK_WORDS", "90")),
        overlap=int(os.getenv("CHUNK_OVERLAP", "15")),
        top_k=int(os.getenv("TOP_K", "3")),
        min_similarity=float(os.getenv("MIN_SIMILARITY", "0.45")),
        mode=os.getenv("RESPONSE_MODE", "demo"),
        base_url=os.getenv("LLM_BASE_URL", Settings.base_url).rstrip("/"),
        api_key=os.getenv("LLM_API_KEY", ""), llm_model=os.getenv("LLM_MODEL", ""),
        input_price=price("INPUT_PRICE_PER_MILLION"),
        output_price=price("OUTPUT_PRICE_PER_MILLION"),
        currency=os.getenv("COST_CURRENCY", "USD"),
    )
