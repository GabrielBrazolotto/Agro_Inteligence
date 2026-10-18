import logging

import httpx
import pytest
from google.genai.errors import ClientError, ServerError

from agro_ai.diagnostics import (ChatFailure, EmptyResponseError, LOGGER,
                                 configure_logging, operation)
from agro_ai.gemini import GeminiGateway
from agro_ai.config import Settings
from types import SimpleNamespace


@pytest.mark.parametrize('code', [400, 401, 403, 404, 429, 500])
@pytest.mark.parametrize('stage', ['retrieval', 'generation'])
def test_api_codes_are_safe_and_stage_specific(code, stage, caplog):
    secret = 'SENSITIVE-KEY-PROMPT-CUSTOMER'
    cls = ServerError if code >= 500 else ClientError
    with caplog.at_level(logging.INFO, logger='agro_ai'):
        with pytest.raises(ChatFailure) as caught:
            with operation(stage):
                raise cls(code, {'error': {'message': secret, 'status': secret}})
    failure = caught.value
    assert failure.stage == stage
    assert failure.code == code
    assert failure.reference
    assert secret not in failure.user_message
    assert secret not in caplog.text
    assert secret not in str(failure)
    assert f'http={code}' in caplog.text


@pytest.mark.parametrize('error,category', [
    (httpx.ConnectError('SECRET URL'), 'connection'),
    (httpx.ReadTimeout('SECRET URL'), 'timeout'),
    (EmptyResponseError('SECRET PROMPT'), 'empty_response'),
    (RuntimeError('SECRET DATA'), 'local'),
])
def test_transport_and_local_errors(error, category):
    with pytest.raises(ChatFailure) as caught:
        with operation('index_sync'):
            raise error
    assert caught.value.category == category
    assert 'SECRET' not in caught.value.user_message


def test_stream_failure_after_first_chunk_is_not_swallowed():
    def stream(**kwargs):
        yield SimpleNamespace(text='partial confidential text')
        raise ServerError(500, {'error': {'message': 'SECRET'}})
    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway.settings = SimpleNamespace(model='fake')
    gateway.client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=stream))
    iterator = gateway.stream([{'role': 'user', 'content': 'fake'}], 'fake')
    assert next(iterator) == 'partial confidential text'
    with pytest.raises(ChatFailure) as caught:
        with operation('generation'):
            next(iterator)
    assert caught.value.code == 500


def test_empty_stream_is_explicit():
    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway.settings = SimpleNamespace(model='fake')
    gateway.client = SimpleNamespace(models=SimpleNamespace(
        generate_content_stream=lambda **kwargs: iter([SimpleNamespace(text=None)])))
    with pytest.raises(EmptyResponseError):
        list(gateway.stream([{'role': 'user', 'content': 'fake'}], 'fake'))


def test_sdk_configuration_is_explicit(monkeypatch):
    import agro_ai.gemini
    captured = {}
    monkeypatch.setattr(agro_ai.gemini.genai, 'Client', lambda **kwargs: captured.update(kwargs))
    GeminiGateway(Settings('fake-only', 'gemini-2.5-flash', 'gemini-embedding-001'))
    assert captured['vertexai'] is False
    assert captured['http_options'].retry_options.attempts == 1
    assert captured['http_options'].timeout == 30000


def test_logging_setup_never_enables_http_debug():
    configure_logging()
    configure_logging()
    assert sum(bool(getattr(handler, '_agro_safe', False)) for handler in LOGGER.handlers) == 1
    assert not LOGGER.propagate
    assert logging.getLogger('httpx').level == logging.CRITICAL
