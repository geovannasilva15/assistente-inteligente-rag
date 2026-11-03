"""Verificacao real da API local. Execute com o servidor iniciado em modo demo."""
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

root = Path(__file__).resolve().parents[1]
with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60) as client:
    health = client.get("/health")
    health.raise_for_status()
    responses = []
    for question, expected in [
        ("O que significa top-k e qual o risco de aumentar esse valor?", True),
        ("Qual é a previsão do tempo amanhã?", False),
    ]:
        response = client.post("/ask", json={"question": question, "mode": "demo", "top_k": 3})
        response.raise_for_status()
        data = response.json()
        assert data["answerable"] == expected
        assert bool(data["sources"]) == expected
        assert all(f"[{c['id']}]" in data["answer"] for c in data["sources"])
        responses.append({"question": question, "response": data})
    assert client.post("/ask", json={"question": "   "}).status_code == 422
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    report = client.get("/evaluations")
    report.raise_for_status()
    assert len(report.json()["runs"]) == 2
result = {"executed_at": datetime.now(timezone.utc).isoformat(),
          "health": health.json(), "queries": responses, "validation_422": True,
          "home_200": True, "docs_200": True, "evaluation_runs": 2}
(root / "docs" / "smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("Smoke real aprovado: saude, pergunta com fonte, abstencao, validacao, interface, docs e relatorio.")
