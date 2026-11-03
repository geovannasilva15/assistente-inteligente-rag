# Verificação da entrega

Execuções locais em 03/11/2026, Windows, Python 3.12.10 e CPU. Horários dos arquivos JSON estão em UTC; São Paulo corresponde a UTC−3 nessa data.

## Evidências

- Instalação das dependências em `.venv` e verificação com `python -m pip check`: sem dependências quebradas. O comando de instalação com `requirements.txt` foi conferido novamente com as versões já instaladas.
- `python -m lab ingest`: download público do encoder FastEmbed/ONNX e criação real de 12 vetores/trechos. Nova execução do comando também aprovada usando o cache. Índice e pesos não entram no Git.
- `python -m lab ask "O que é recall@k?" --top-k 3 --mode demo`: resposta com IDs reais das seções de avaliação, sem provedor de geração.
- `python -m pytest -q`: **42 passaram**, tanto na primeira execução quanto na revisão final. Há um `StarletteDeprecationWarning` sobre o TestClient/HTTPX; não foi ocultado. O encoder dos testes é um substituto determinístico, e HTTP do LLM usa `MockTransport`.
- `python -m compileall -q lab scripts tests`: sem erro de sintaxe.
- Uvicorn iniciou em `127.0.0.1:8000`; foi reiniciado após nova ingestão para conferir o fluxo documentado.
- `python scripts/smoke.py`: verifica HTTP real de saúde, pergunta com fontes, pergunta sem evidência, validação 422, página inicial, OpenAPI e dois resultados de avaliação. Saída completa registrada em [smoke.json](smoke.json). Nenhum LLM pago é chamado.
- Navegador: página inicial, envio de pergunta sobre top-k, resposta/citações, expansão de trecho e metadados, carregamento do relatório e abstenção para previsão do tempo. Capturas finais em [images/demo-overview.jpg](images/demo-overview.jpg) e [images/demo-sources.jpg](images/demo-sources.jpg). A [captura completa inicial](images/demo-desktop.jpg) registra o conjunto anterior, antes da revisão de q15.
- Verificação de layout em viewport reduzido: largura efetiva do documento de 375 px e `scrollWidth` de 375 px, após ajustar o cabeçalho para quebrar linha. Não foi testado em aparelho físico. A captura móvel do navegador integrado apresentou limitação; somente a captura desktop é entregue.
- Revisão por padrões comuns de credenciais não encontrou chaves privadas ou tokens reais nos arquivos candidatos à entrega. `.env`, ambiente, pesos e índice estão ignorados; as credenciais usadas nos testes são valores fictícios explícitos.
- Comparação dos objetos Git confirmou conteúdo idêntico nos 15 arquivos anteriores preservados em `legacy/`; diferenças locais de LF/CRLF não alteram os blobs entregues.

## Avaliação real

A execução final do conjunto atual está em `reports/evaluation-20261103T123544182545Z.json`, também copiada em `latest.json`. O conjunto possui 16 casos: 11 respondíveis e 5 não respondíveis. A ordem foi k=3 e depois k=5, com encoder aquecido.

| k | Hit rate | Recall médio | Abstenção nas não respondíveis | Resposta nas respondíveis | Citações válidas entre respostas | Tempo total |
|---|---:|---:|---:|---:|---:|---:|
| 3 | 1,0 | 0,954545 | 0,8 | 0,818182 | 1,0 | 224,057 ms |
| 5 | 1,0 | 1,0 | 0,8 | 0,818182 | 1,0 | 224,444 ms |

Falhas relevantes: q14 recebe texto relacionado a cálculo de custo sem o preço atual pedido; q01 e q08 são recusadas apesar de serem respondíveis; q09 só recupera uma das duas seções esperadas com k=3. Métricas de recuperação usam candidatos antes do filtro; a citação válida não é prova de resposta correta. Os tempos de uma passagem não demonstram superioridade de desempenho.

Foi preservada a execução de `12:33:15 UTC`, com abstenção de 0,6 nas não respondíveis. Depois dessa execução, q15 foi revisada: a pergunta anterior sobre um limiar que garantia acerto tinha uma falsa premissa, que o texto podia refutar. A nova pergunta pede explicitamente um valor numérico recomendado pelo NIST, inexistente na base. O encoder, limiar e documentos não foram ajustados entre essas execuções. Como o conjunto mudou, não se trata de uma melhoria comprovada do sistema. Os hashes das perguntas distinguem os relatórios.

## Limites da verificação

Não houve geração paga real, teste de carga, auditoria de segurança, uso multiusuário, validação em aparelho físico, OCR/PDF na versão atual, execução local em Linux/macOS ou certificação de qualidade semântica. Integração com modelo externo foi verificada apenas por contrato e erros em HTTP substituto. O workflow de GitHub Actions deve ser conferido no PR; testes locais não demonstram que a CI remota executou.
