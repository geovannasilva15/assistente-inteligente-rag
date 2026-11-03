const $ = id => document.getElementById(id);

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function percentage(value) {
  return value === null ? 'indisponível' : (value * 100).toFixed(1) + '%';
}

async function request(url, options) {
  const response = await fetch(url, options);
  let data;
  try {
    data = await response.json();
  } catch {
    throw new Error('A API retornou uma resposta inválida.');
  }
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string'
      ? data.detail : 'Revise a pergunta e as opções enviadas.');
  }
  return data;
}

function sourceCard(chunk) {
  const box = element('article', undefined, 'source');
  box.append(
    element('h4', `${chunk.source.title} · ${chunk.section}`),
    element('p', `ID: ${chunk.id} · similaridade: ${chunk.similarity.toFixed(3)}`)
  );
  const details = element('details');
  details.append(element('summary', 'Ler trecho e origem'), element('p', chunk.text));
  // Somente links HTTP(S); texto de documento/modelo nunca vira HTML.
  try {
    const url = new URL(chunk.source.url);
    if (['https:', 'http:'].includes(url.protocol)) {
      const link = element('a', 'Referência pública ↗');
      link.href = url.href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      details.append(link);
    }
  } catch { /* Fonte inválida continua visível como texto. */ }
  details.append(element('p', `${chunk.source.organization}. Consulta: ${chunk.source.accessed}. ${chunk.source.license}`));
  box.append(details);
  return box;
}

function renderAnswer(data) {
  $('answer').textContent = data.answer;
  $('answer-title').textContent = data.answerable ? 'Resposta com evidências' : 'Evidência insuficiente';
  $('status').textContent = data.mode === 'demo'
    ? 'Demonstração · extração literal' : 'LLM · provedor opcional';
  const metrics = data.metrics;
  const cost = metrics.estimated_cost;
  const values = [
    ['Tempo medido', `${metrics.latency_ms.toFixed(1)} ms`],
    ['Trechos recuperados / contexto', `${metrics.retrieved_count} / ${metrics.context_count}`],
    ['Tokens de entrada / saída', `${metrics.input_tokens ?? 'indisponível'} / ${metrics.output_tokens ?? 'indisponível'}`],
    ['Custo estimado', cost ? `${cost.amount.toFixed(8)} ${cost.currency}` : 'indisponível']
  ];
  $('metrics').replaceChildren();
  for (const [label, value] of values) {
    const item = element('div', undefined, 'metric');
    item.append(element('small', label), element('span', value));
    $('metrics').append(item);
  }
  const config = data.config;
  $('metrics').append(element('p', `Top-k ${config.top_k} · limiar ${config.min_similarity} · ${config.embedding_model}`, 'muted'));
  $('sources').replaceChildren(...data.sources.map(sourceCard));
  if (!data.sources.length) $('sources').append(element('p', 'Nenhuma fonte citada.', 'muted'));
  $('retrieved').replaceChildren(...data.retrieved.map(sourceCard));
  $('output').hidden = false;
}

function renderReport(data) {
  if (data.status === 'not_run') {
    $('report').textContent = data.message;
    return;
  }
  $('report').replaceChildren(element('p', `Execução: ${data.executed_at} · modo: ${data.mode} · modelo: ${data.config.embedding_model} · limiar: ${data.config.min_similarity}`));
  const table = element('table');
  const header = element('tr');
  for (const label of ['Top-k', 'Casos', 'Hit rate', 'Recall médio', 'Abstenção sem resposta', 'Tempo total']) {
    const cell = element('th', label);
    cell.scope = 'col';
    header.append(cell);
  }
  table.append(header);
  for (const run of data.runs) {
    const row = element('tr');
    const values = [run.top_k, run.case_count, percentage(run.hit_rate_at_k),
      percentage(run.mean_recall_at_k), percentage(run.unanswerable_abstention_rate),
      `${run.elapsed_ms.toFixed(1)} ms`];
    for (const value of values) row.append(element('td', String(value)));
    table.append(row);
  }
  $('report').append(table, element('p', data.limitations));
  for (const run of data.runs) {
    const details = element('details');
    details.append(element('summary', `Resultados por pergunta · top-k ${run.top_k}`));
    details.append(element('p', `Respondíveis: ${run.answerable_count} · sem resposta: ${run.unanswerable_count} · taxa de resposta nas respondíveis: ${percentage(run.answerable_response_rate)} · validade estrutural das citações: ${percentage(run.citation_validity_rate)}`));
    for (const testCase of run.cases) {
      details.append(element('p', `${testCase.id}: ${testCase.question} | esperado respondível: ${testCase.expected_answerable} | respondeu: ${testCase.actual_answerable} | recall: ${testCase.recall_at_k ?? 'não aplicável'} | fontes recuperadas: ${testCase.retrieved_sources.join(', ')}`));
    }
    $('report').append(details);
  }
}

document.querySelectorAll('.examples button').forEach(button => {
  button.addEventListener('click', () => {
    $('question').value = button.textContent;
    $('question').focus();
  });
});

$('mode').addEventListener('change', () => {
  $('mode-note').textContent = $('mode').value === 'demo'
    ? 'Sem chave paga. Copia trechos reais da base; não gera uma síntese por modelo de linguagem.'
    : 'Exige provedor configurado no servidor. A pergunta e os trechos selecionados serão enviados ao provedor; o uso pode gerar custos.';
});

$('form').addEventListener('submit', async event => {
  event.preventDefault();
  $('submit').disabled = true;
  $('status').classList.remove('error');
  $('status').textContent = 'Buscando evidências…';
  $('output').hidden = true;
  $('empty').hidden = true;
  try {
    const data = await request('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: $('question').value,
        top_k: Number($('topk').value), mode: $('mode').value})
    });
    renderAnswer(data);
  } catch (error) {
    $('status').textContent = error.message;
    $('status').classList.add('error');
  } finally {
    $('submit').disabled = false;
  }
});

$('load-report').addEventListener('click', async () => {
  $('load-report').disabled = true;
  $('report').textContent = 'Consultando execução…';
  try {
    renderReport(await request('/evaluations'));
  } catch (error) {
    $('report').textContent = error.message;
  } finally {
    $('load-report').disabled = false;
  }
});
