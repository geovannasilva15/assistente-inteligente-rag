# Análise antes da implementação

Consulta em 03/11/2026 ao repositório `geovannasilva15/assistente-inteligente-rag`, por conector GitHub e cópia local.

- Repositório privado, padrão `main`, commit `3fcb3f899777bd17f9bc4a1174fa926eaddc4485`.
- `main`: somente README inicial, sem aplicação, dependências ou testes.
- `feat/professional-rag-release`, `feat/publicacao-profissional` e `publish-rag-project`: mesmo commit inicial.
- `implementacao-rag-profissional`, commit `8cbb30a63d826ca44b4bdeebe740cbe7371ba6ad`: RAG lexical, Streamlit, CLI, ingestão TXT/MD/PDF, geração opcional OpenAI, políticas fictícias, Docker e cinco testes unittest. Todos os arquivos foram lidos antes das alterações.
- PR #1 aberto com essa implementação; não foi alterado, fechado ou mesclado. Alegações de testes de sua descrição não foram tratadas como evidência da nova versão.
- Conector indicava permissão de escrita. Clone pelo terminal exigiu acesso de rede fora do sandbox e depois funcionou.
- Cópia nova limpa antes dos arquivos. A pasta superior contém outros trabalhos, mantidos fora deste projeto.

Decisão: criar `codex/ai-reliability-lab` da `main`, preservar a implementação anterior em `legacy/` e implementar a versão atual em `lab/`. O conteúdo útil continua consultável sem misturar dependências antigas ou políticas fictícias à base de IA. O README inicial foi atualizado, com referência ao histórico e autoria.

Não havia AGENTS.md no repositório. Não houve merge, mudança de visibilidade ou publicação em hospedagem externa. O outro PR também altera o README e organiza a aplicação de forma diferente: uma integração futura entre as propostas precisará de revisão.
