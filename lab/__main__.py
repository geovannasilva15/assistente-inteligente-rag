import argparse
import json

from .config import from_env


def main():
    parser = argparse.ArgumentParser(description="AI Reliability Lab")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest", help="Recria o indice persistido de documentos locais.")
    commands.add_parser("evaluate", help="Avalia o modo demo com top-k 3 e 5.")
    ask = commands.add_parser("ask", help="Consulta o indice persistido.")
    ask.add_argument("question")
    ask.add_argument("--top-k", type=int, default=None)
    ask.add_argument("--mode", choices=["demo", "llm"], default=None)
    args = parser.parse_args()
    settings = from_env()
    try:
        if args.command == "ingest":
            from .retrieval import build_index
            result = build_index(settings)
        elif args.command == "evaluate":
            from .evaluation import run_evaluation
            report = run_evaluation(settings)
            result = {"executed_at": report["executed_at"], "runs": [
                {k: v for k, v in run.items() if k != "cases"} for run in report["runs"]]}
        else:
            from .retrieval import Retriever
            from .service import Service
            result = Service(settings, Retriever(settings)).ask(args.question, args.top_k, args.mode)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        parser.exit(1, "Falha na operacao. Verifique configuracao, indice e disponibilidade do modelo/provedor. "
                    "Consulte o README para reconstruir o indice.\n")


if __name__ == "__main__":
    main()
