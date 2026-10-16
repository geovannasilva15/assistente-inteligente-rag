import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.rag_assistant import RagAssistant


load_dotenv()
st.set_page_config(page_title="Assistente RAG", page_icon="📚", layout="wide")
st.title("Assistente Inteligente com RAG")
st.caption("Consulte documentos e confira os trechos usados em cada resposta.")

uploads = st.file_uploader(
    "Envie arquivos TXT, Markdown ou PDF", type=["txt", "md", "pdf"], accept_multiple_files=True
)
with st.sidebar:
    st.subheader("Configuração")
    top_k = st.slider("Trechos recuperados", 1, 8, int(os.getenv("TOP_K", "4")))
    use_openai = st.toggle("Usar OpenAI quando configurada", value=bool(os.getenv("OPENAI_API_KEY")))
    st.info("Sem chave configurada, o assistente responde em modo local.")


def build_assistant() -> RagAssistant:
    if not uploads:
        return RagAssistant(Path("knowledge_base"))
    temp_dir = Path(tempfile.mkdtemp(prefix="rag_documents_"))
    for uploaded in uploads:
        safe_name = Path(uploaded.name).name
        (temp_dir / safe_name).write_bytes(uploaded.getbuffer())
    return RagAssistant(temp_dir)


question = st.text_input("Pergunta", placeholder="Ex.: Qual é a política de trabalho remoto?")
if st.button("Consultar", type="primary", disabled=not question.strip()):
    try:
        with st.spinner("Consultando os documentos..."):
            assistant = build_assistant()
            answer, results = assistant.ask(question, top_k=top_k, use_openai=use_openai)
        st.subheader("Resposta")
        st.write(answer)
        with st.expander("Trechos recuperados"):
            if not results:
                st.warning("Nenhum trecho relacionado foi encontrado.")
            for result in results:
                st.markdown(f"**{result.chunk.source} · relevância {result.score:.3f}**")
                st.write(result.chunk.text)
                st.divider()
    except Exception as error:
        st.error(f"Não foi possível processar a consulta: {error}")
