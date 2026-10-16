import tempfile
import unittest
from pathlib import Path

from src.rag_assistant.generation import generate_local_answer
from src.rag_assistant.ingestion import read_document, split_document
from src.rag_assistant.models import Document
from src.rag_assistant.pipeline import RagAssistant


class RagAssistantTests(unittest.TestCase):
    def test_splits_document_with_valid_overlap(self):
        document = Document(source="teste.txt", text="Conteúdo de teste. " * 80)
        chunks = split_document(document, chunk_size=180, overlap=30)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.source == "teste.txt" for chunk in chunks))

    def test_rejects_invalid_overlap(self):
        with self.assertRaises(ValueError):
            split_document(Document("teste.txt", "conteúdo"), chunk_size=100, overlap=100)

    def test_retrieves_relevant_source_and_answers_with_citation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "politica.md"
            path.write_text(
                "O trabalho remoto é permitido em dois dias por semana. "
                "A autenticação de dois fatores é obrigatória.",
                encoding="utf-8",
            )
            assistant = RagAssistant(Path(directory), chunk_size=200, overlap=20)
            answer, results = assistant.ask("Quantos dias de trabalho remoto?", use_openai=False)
        self.assertTrue(results)
        self.assertEqual(results[0].chunk.source, "politica.md")
        self.assertIn("[politica.md]", answer)

    def test_returns_safe_message_without_match(self):
        answer = generate_local_answer("pergunta", [])
        self.assertIn("Não encontrei", answer)

    def test_rejects_empty_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vazio.txt"
            path.write_text("   \n", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_document(path)


if __name__ == "__main__":
    unittest.main()
