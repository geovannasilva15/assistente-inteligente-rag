# Guia de apresentação — AI Reliability Lab

## Objetivo

O laboratório recebe perguntas sobre uma base pequena, encontra trechos relevantes e mostra de onde veio a resposta. Também executa perguntas de teste para revelar falhas na recuperação e na decisão de responder. Ele ajuda a estudar qualidade e rastreabilidade em aplicações de IA.

Este guia descreve a implementação entregue. Não atribui experiências profissionais ou decisões anteriores à autora. Antes de usar o roteiro em primeira pessoa, execute, leia e valide o que consegue explicar.

## Roteiro de aproximadamente um minuto

“Este é o AI Reliability Lab, um projeto de portfólio para estudar perguntas sobre documentos com fontes e avaliação. A aplicação usa Python e FastAPI, com uma interface web simples. Na ingestão, os textos são divididos em trechos e convertidos em embeddings locais. As perguntas passam pela mesma representação, e a busca seleciona os trechos mais próximos. O modo sem chave apresenta extrações literais com fontes. Há também um conector opcional para um modelo de linguagem. O diferencial é inspecionar a evidência e avaliar o comportamento: o conjunto de 16 perguntas compara top-k 3 e 5. A execução mostrou boa recuperação na base pequena, mas também uma resposta indevida e duas abstenções indevidas. Portanto, não apresento as métricas como prova de confiabilidade. O projeto torna os limites visíveis para orientar o próximo experimento.”

## Demonstração

1. Siga o README e abra a interface local em modo demo, top-k 3.
2. Pergunte: **O que significa top-k e qual o risco de aumentar esse valor?**
3. Abra **Ler trecho e origem** e explique `[rag:topk:0]`, título, seção e referência pública. O texto distribuído é próprio; o artigo é referência conceitual.
4. Mostre tempo medido e custo indisponível. A primeira consulta inclui carregar o encoder.
5. Pergunte **Qual é a previsão do tempo amanhã?** e mostre a abstenção e candidatos abaixo do limiar.
6. Abra **Consultar última execução**, explique denominadores e examine q14: o texto retornado fala de custo, mas não contém o preço atual pedido.

## Caminho da pergunta pelo código

`web/app.js` envia JSON para `/ask`. `lab/api.py` valida entrada. `lab/service.py` chama `Retriever`, que usa o índice persistido e calcula o embedding da pergunta com FastEmbed. O cosseno ordena os candidatos e retorna até k trechos. O serviço remove do contexto candidatos abaixo de 0,45. Sem contexto aprovado, se abstém. Com contexto, copia textos e IDs em demo ou envia pergunta/contexto ao LLM opcional. Fontes, candidatos, configuração e métricas voltam à interface como texto, sem interpretar HTML do modelo.

## RAG

RAG combina recuperação de documentos e resposta com contexto recuperado. Em vez de depender apenas do conhecimento nos parâmetros de um modelo, consulta uma base explícita. Isso facilita atualizar documentos e investigar origens. A busca pode falhar e um gerador pode interpretar mal o conteúdo; RAG não elimina erros.

O modo demo é recuperação com apresentação extrativa, sem geração por LLM. O modo opcional usa os mesmos trechos aprovados para gerar uma resposta. O projeto não treina um modelo próprio nem faz fine-tuning.

## Embeddings e busca vetorial

Embedding é uma lista de números que representa características de um texto aprendidas por um modelo. O encoder multilíngue transforma documentos e perguntas em vetores. O cosseno compara suas direções e ordena os mais próximos. Não é um registro de fatos nem uma probabilidade de acerto.

Vetores e metadados ficam num arquivo NPZ, sem pickle. A busca NumPy é exata sobre vetores normalizados, simples para 12 trechos. Um banco vetorial poderia ajudar numa base grande, com maior complexidade operacional.

## Top-k e fontes

Top-k é o máximo de candidatos recuperados: 3/5 no painel, 1 a 10 na API. É diferente do limiar: k controla quantidade, limiar controla quais candidatos entram no contexto. Mesmo com k=5, a resposta pode usar um ou nenhum trecho.

IDs seguem `documento:seção:posição_inicial_em_palavras`. As fontes trazem título, seção, organização, referência, data e condições. `sources` representa os citados, `retrieved` todos os candidatos. Uma referência válida localiza a evidência, mas não comprova toda interpretação da resposta.

## Avaliação e resultados

`python -m lab evaluate` usa 16 casos e compara k=3 e k=5 em demo, após aquecer o encoder. Salva data UTC, configuração, ambiente e hashes da base e perguntas. Não usa um segundo modelo para julgar respostas. Cada pergunta tem fontes/pontos esperados, classificação e justificativa.

Execução de 03/11/2026 às 09:35:44 em São Paulo:

- Hit rate: 11/11 respondíveis tiveram alguma seção esperada nos candidatos, em ambos os k.
- Recall médio: 95,45% com k=3; 100% com k=5.
- Abstenção correta nas não respondíveis: 4/5 em ambos.
- Resposta nas respondíveis: 9/11 em ambos.
- q14 recebeu texto relacionado a custo, sem o preço atual solicitado.
- q01/q08 se abstiveram porque os candidatos não passaram do limiar.
- q09 recuperou uma de duas seções esperadas com k=3; ambas com k=5.

Esses números pertencem a esta execução, não são percentuais esperados em produção. Há uma execução anterior com outra redação de pergunta, que não deve ser apresentada como experimento de melhoria do modelo.

## Interpretação das métricas

Hit rate pergunta “veio alguma fonte esperada?”. Recall pergunta “qual fração das fontes esperadas veio?”. Usa documento/seção distintos; repetir trechos da mesma seção não aumenta recall. As cinco perguntas sem resposta ficam fora dos denominadores de recuperação. A avaliação usa os candidatos antes do filtro; uma seção pode ser recuperada e depois excluída do contexto.

Abstenção compara uma decisão com o rótulo manual. Observe também resposta em respondíveis: recusar tudo não é útil. Validar IDs não equivale a avaliar fidelidade semântica. A checagem literal de pontos esperados é apenas diagnóstica.

O tempo é do servidor, sem rede do navegador. Há uma única passagem por configuração, ordem fixa e sem intervalo de confiança. Não há conclusão estatística de desempenho. Custo usa contagens do provedor e preços configurados, ou fica indisponível; não mede a fatura.

## Decisões implementadas

| Decisão | Motivo e consequência |
|---|---|
| FastAPI + HTML/CSS/JS | API e interface numa aplicação, sem build JS separado. |
| FastEmbed/ONNX multilíngue | Busca local em português na CPU; primeiro uso baixa pesos. |
| NumPy + NPZ | Simples para base pequena; escalabilidade limitada. |
| JSON com seções | Metadados controlados; não oferece ingestão geral de PDF. |
| 90 palavras/15 sobrepostas | Janelas curtas; contagem diferente de tokens do encoder. |
| Limiar inicial 0,45 | Regra auditável, ainda sem calibração independente. |
| Demo extrativa | Sem chave e com texto verificável; pode ser verbosa/irrelevante. |
| Validação de IDs no LLM | Rejeita referências inexistentes; não comprova suporte de cada frase. |
| Pytest com substitutos | Testes offline; qualidade semântica exige verificação separada. |
| Histórico em legacy | Preserva o trabalho anterior e sua busca lexical. |

Não diga “escolhi após comparar todos os modelos”: essa comparação não foi feita. Explique a decisão implementada e o que precisaria medir para reconsiderá-la.

## Dez perguntas de entrevista

**1. RAG é fine-tuning?** Não. RAG recupera contexto externo; fine-tuning altera parâmetros por treinamento. Aqui usamos um encoder pré-treinado e não treinamos o modelo.

**2. Por que não chamar só o LLM?** Uma base explícita facilita atualizar conteúdo e investigar a origem. Ainda exige conferir se o texto recuperado responde à pergunta.

**3. Como funciona sem chave?** O encoder roda localmente após o download, e o modo demo copia trechos aprovados com fontes. Não simula um gerador remoto.

**4. k=5 é sempre melhor?** Pode recuperar uma fonte faltante e também acrescentar ruído/tokens/custo. Nesta execução aumentou recall, sem corrigir as decisões de abstenção.

**5. Como detecta que não sabe?** Usa limiar de similaridade e, no modo LLM, permite abstenção do modelo. É uma heurística falível: q14 é um falso positivo concreto.

**6. Como evita citações inventadas?** O demo usa IDs reais; no LLM, valida IDs listados e presentes no texto contra o contexto. Uma afirmação ainda pode estar errada com fonte existente.

**7. O que os testes verificam?** As 42 verificações locais cobrem processamento, persistência, metadados, regras, API, métricas, custos e HTTP com substitutos. A busca real foi verificada separadamente.

**8. Recria o índice por pergunta?** Não. `python -m lab ingest` gera o arquivo, carregado uma vez por processo. Atualizar documentos exige reingestão e reinício do servidor.

**9. Quais riscos permanecem?** Injeção não é resolvida apenas com prompt. O serviço local não tem autenticação nem rate limit. Uso público exigiria controles de acesso, custos e conteúdo.

**10. Como avalia custo e confiabilidade?** Custo usa tokens/preços conhecidos, ou fica indisponível. Confiabilidade exige casos representativos, revisão de afirmações e investigação de falhas, não uma única métrica em 16 perguntas.

## Limitações, estudo e futuro

Não houve geração paga real, não há banco distribuído, upload seguro, OCR, autenticação ou monitoramento de produção. Os textos próprios não representam um acervo real; limiar não calibrado e falsos positivos/negativos estão documentados.

Estude Python (tipos, classes, exceções, dataclasses), HTTP/Pydantic/FastAPI, vetores/cosseno, divisão de texto, fixtures/substitutos, conjuntos de avaliação e Git/PRs. Leia `ingestion.py`, `retrieval.py`, `service.py`, `api.py` e `evaluation.py` nessa ordem e acompanhe uma pergunta no depurador. Experimente k e limiar, registre previsões antes de rodar e confira os casos individuais. Use perguntas novas, separadas das atuais, para reduzir ajuste aos testes.

Possíveis próximos passos: avaliação humana de fidelidade, conjunto independente, calibração da abstenção, busca híbrida/reranker, precisão de recuperação, múltiplas execuções com percentis de tempo e integração paga opt-in. São sugestões, não funcionalidades entregues.
