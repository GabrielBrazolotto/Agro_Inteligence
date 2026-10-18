from types import SimpleNamespace

import pytest
from google.genai.errors import APIError

from agro_ai.gemini import GeminiGateway


def gateway_for(stream):
    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway.settings = SimpleNamespace(model='fake')
    gateway.client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=stream))
    return gateway


def test_followup_retries_503_once_without_changing_history(monkeypatch):
    calls = []
    sleeps = []
    monkeypatch.setattr('agro_ai.gemini.time.sleep', sleeps.append)
    def stream(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise APIError(503, {'error': {'message': 'private'}})
        yield SimpleNamespace(text='À vista, desconto de 2%.')
    history = [{'role': 'user', 'content': 'Política de descontos?'},
               {'role': 'assistant', 'content': 'Até 5%.'},
               {'role': 'user', 'content': 'E à vista?'}]
    answer = ''.join(gateway_for(stream).stream(history, 'contexto fictício'))
    assert answer == 'À vista, desconto de 2%.'
    assert len(calls) == 2
    assert calls[0]['contents'] == calls[1]['contents']
    assert [item.role for item in calls[1]['contents']] == ['user', 'model', 'user']
    assert sleeps == [1]
    assert len(history) == 3


def test_persistent_503_stops_after_two_calls(monkeypatch):
    calls = []
    monkeypatch.setattr('agro_ai.gemini.time.sleep', lambda _: None)
    def stream(**kwargs):
        calls.append(kwargs)
        raise APIError(503, {'error': {'message': 'private'}})
    with pytest.raises(APIError):
        list(gateway_for(stream).stream([], 'fake'))
    assert len(calls) == 2


@pytest.mark.parametrize('code', [400, 401, 403, 404, 429, 500, 503])
def test_partial_response_is_never_retried(code, monkeypatch):
    monkeypatch.setattr('agro_ai.gemini.time.sleep', lambda _: pytest.fail('Unexpected retry'))
    calls = []
    def stream(**kwargs):
        calls.append(kwargs)
        yield SimpleNamespace(text='partial')
        raise APIError(code, {'error': {'message': 'private'}})
    with pytest.raises(APIError):
        list(gateway_for(stream).stream([], 'fake'))
    assert len(calls) == 1


@pytest.mark.parametrize('code', [400, 401, 403, 404, 429, 500])
def test_other_api_errors_are_not_retried(code, monkeypatch):
    monkeypatch.setattr('agro_ai.gemini.time.sleep', lambda _: pytest.fail('Unexpected retry'))
    def stream(**kwargs):
        raise APIError(code, {'error': {'message': 'private'}})
    with pytest.raises(APIError):
        list(gateway_for(stream).stream([], 'fake'))
