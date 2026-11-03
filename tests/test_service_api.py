from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from lab.api import create_app
from lab.generation import ProviderError
from lab.service import Service


def test_main_flow_with_substitute_encoder(service):
    result = service.ask('Embeddings representam textos como vetores numéricos', 3)
    assert result['answerable'] and result['mode'] == 'demo'
    assert result['sources']
    assert result['sources'][0]['text'] in result['answer']
    assert '[' + result['sources'][0]['id'] + ']' in result['answer']
    assert result['metrics']['latency_ms'] >= 0
    assert result['metrics']['estimated_cost'] is None
    assert result['metrics']['input_tokens'] is None


def test_abstention_never_calls_llm(service):
    class NoEvidence:
        manifest = service.retriever.manifest
        def search(self, q, k): return []
    class Never:
        def answer(self, *args): raise AssertionError('Nao deveria chamar provedor')
    result = Service(service.settings, NoEvidence(), Never()).ask('meteorologia', mode='llm')
    assert not result['answerable'] and result['cited_ids'] == []
    assert 'evidência suficiente' in result['answer']


def test_threshold_blocks_weak_context(service):
    s = Service(replace(service.settings, min_similarity=1), service.retriever)
    assert not s.ask('uma pergunta diferente')['answerable']


@pytest.mark.parametrize('body', [
    {'question':''}, {'question':'  '}, {'question':'x'*1001}, {},
    {'question':'x','top_k':0}, {'question':'x','top_k':11},
    {'question':'x','top_k':True}, {'question':'x','mode':'unknown'},
])
def test_api_validation(service, body):
    with TestClient(create_app(service=service)) as client:
        assert client.post('/ask', json=body).status_code == 422


def test_api_static_and_real_service_with_fake_encoder(service):
    with TestClient(create_app(service=service)) as client:
        assert client.get('/health').json()['index_ready']
        assert client.get('/').status_code == 200
        assert client.get('/static/app.js').status_code == 200
        assert client.get('/docs').status_code == 200
        response = client.post('/ask', json={'question':'O que são embeddings?','top_k':3})
        assert response.status_code == 200 and response.json()['sources']


def test_missing_index_and_no_report(settings):
    with TestClient(create_app(settings=settings)) as client:
        assert client.get('/health').status_code == 503
        assert client.post('/ask', json={'question':'teste'}).status_code == 503
        assert client.get('/evaluations').json()['status'] == 'not_run'


def test_api_provider_error_does_not_expose_secrets(service):
    class Broken:
        def answer(self, *args): raise ProviderError('Provedor indisponivel.')
    instance = Service(service.settings, service.retriever, Broken())
    with TestClient(create_app(service=instance)) as client:
        response = client.post('/ask', json={'question':'Embeddings vetores numéricos','mode':'llm'})
        assert response.status_code == 502
        assert response.json()['detail'] == 'Provedor indisponivel.'


def test_unknown_local_error_is_sanitized(service):
    class Broken:
        def ask(self, *args): raise RuntimeError('secret-value')
    with TestClient(create_app(service=Broken())) as client:
        response = client.post('/ask', json={'question':'teste'})
        assert response.status_code == 503
        assert 'secret-value' not in response.text
