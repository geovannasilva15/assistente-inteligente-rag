import json
from dataclasses import replace

import httpx
import pytest

from lab.evaluation import evaluate, retrieval_metrics
from lab.generation import LLM, ProviderError, estimate_cost


def test_cost_known_and_missing(settings):
    priced = replace(settings, input_price=2, output_price=8)
    assert estimate_cost(1000, 100, priced)['amount'] == pytest.approx(.0028)
    assert estimate_cost(1000, 100, priced)['currency'] == 'USD'
    assert estimate_cost(1000, None, priced) is None
    assert estimate_cost(1000, 100, settings) is None


@pytest.mark.parametrize('price', [-1, float('inf'), float('nan')])
def test_bad_prices(settings, price):
    with pytest.raises(ValueError): replace(settings, input_price=price)


def test_metrics_use_unique_sources():
    assert retrieval_metrics(['a','b'], ['a','a','c']) == (1,.5)
    assert retrieval_metrics(['a'], ['b']) == (0,0)
    assert retrieval_metrics([], ['a']) == (None,None)


def test_evaluation_denominators_and_citations(service):
    cases = [
        {'id':'yes','question':'Embeddings vetores numéricos','answerable':True,
         'expected_sources':['rag:embeddings'],'expected_points':['vetores numéricos']},
        {'id':'no','question':'zzzzzz','answerable':False,'expected_sources':[], 'expected_points':[]},
    ]
    report = evaluate(service, cases, 3)
    assert report['case_count'] == 2 and report['answerable_count'] == 1
    assert report['hit_rate_at_k'] == 1
    assert report['cases'][0]['citations_valid']
    assert report['mean_latency_ms'] >= 0


def configured(settings):
    return replace(settings, api_key='test-secret', llm_model='test-model', base_url='https://provider.invalid/v1')


def test_llm_mock_protocol_and_minimal_context(settings):
    def handler(request):
        body = json.loads(request.content)
        assert request.headers['Authorization'] == 'Bearer test-secret'
        assert body['model'] == 'test-model'
        context = json.loads(body['messages'][1]['content'])['context']
        assert context == [{'id':'a:1:0','text':'conteudo'}]
        return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({
            'answerable':True,'answer':'Resposta [a:1:0]','cited_ids':['a:1:0']})}}],
            'usage':{'prompt_tokens':25,'completion_tokens':7}})
    result = LLM(configured(settings),httpx.MockTransport(handler)).answer('pergunta', [{'id':'a:1:0','text':'conteudo','private_metadata':'not_sent'}])
    assert result[1] == ['a:1:0'] and result[2]['prompt_tokens'] == 25


@pytest.mark.parametrize('status', [401,429,500])
def test_llm_http_errors_sanitized(settings, status):
    provider = LLM(configured(settings),httpx.MockTransport(lambda request:httpx.Response(status,text='test-secret')))
    with pytest.raises(ProviderError) as error:
        provider.answer('pergunta', [])
    assert 'test-secret' not in str(error.value)


def test_llm_timeout(settings):
    def timeout(request): raise httpx.ConnectTimeout('test-secret')
    with pytest.raises(ProviderError):
        LLM(configured(settings),httpx.MockTransport(timeout)).answer('x',[])


@pytest.mark.parametrize('content', [
    'nao e json',
    json.dumps({'answerable':True,'answer':'Resposta [inventado]','cited_ids':['inventado']}),
    json.dumps({'answerable':True,'answer':'Resposta sem citacao','cited_ids':['a:1:0']}),
    json.dumps({'answerable':'true','answer':'Resposta','cited_ids':[]}),
])
def test_llm_invalid_output_rejected(settings, content):
    transport = httpx.MockTransport(lambda request:httpx.Response(200,json={'choices':[{'message':{'content':content}}]}))
    with pytest.raises(ProviderError):
        LLM(configured(settings),transport).answer('x',[{'id':'a:1:0','text':'contexto'}])


def test_llm_missing_configuration(settings):
    with pytest.raises(ProviderError): LLM(settings).answer('x',[])


def test_llm_can_abstain(settings):
    content = json.dumps({'answerable':False,'answer':'Não sei','cited_ids':[]})
    transport = httpx.MockTransport(lambda request:httpx.Response(200,json={'choices':[{'message':{'content':content}}]}))
    answer, ids, _ = LLM(configured(settings), transport).answer('x',[])
    assert answer is None and ids == []
