import argparse
import os
from pathlib import Path

from src.rag_assistant import RagAssistant


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulte documentos com o assistente RAG.")
    parser.add_argument("question", help="Pergunta sobre os documentos")
    parser.add_argument("--knowledge-dir", default="knowledge_base", help="Diretório dos documentos")
    parser.add_argument("--local", action="store_true", help="Não realiza chamadas externas")
    args = parser.parse_args()

    assistant = RagAssistant(
        Path(args.knowledge_dir),
        chunk_size=int(os.getenv("CHUNK_SIZE", "900")),
        overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
    )
    answer, results = assistant.ask(
        args.question, top_k=int(os.getenv("TOP_K", "4")), use_openai=not args.local
    )
    print(answer)
    if results:
        print("\nFontes recuperadas:")
        for result in results:
            print(f"- {result.chunk.chunk_id} (relevância: {result.score:.3f})")


if __name__ == "__main__":
    main()
