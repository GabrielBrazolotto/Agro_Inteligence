from dataclasses import replace
from datetime import datetime,timezone,timedelta
from types import SimpleNamespace
import json

import httpx
import pytest
from google.genai.errors import ClientError,ServerError

from agro_ai.config import Settings,get_settings
from agro_ai.diagnostics import ChatFailure,operation
from agro_ai.api_limits import limit_evidence,next_daily_reset
import agro_ai.api_limits as limits


@pytest.fixture
def isolated(monkeypatch,tmp_path):
    monkeypatch.setattr(limits,'ROOT',tmp_path)
    limits._last.clear()
    return Settings('fake-private-key','main','embedding')


def test_config_separates_models_without_changing_embedding(monkeypatch,tmp_path):
    import agro_ai.config as config
    monkeypatch.setattr(config,'ROOT',tmp_path)
    for name in ('GEMINI_MODEL','GEMINI_AGENT_MODEL','GEMINI_JUDGE_MODEL','GEMINI_EMBEDDING_MODEL','GEMINI_MIN_INTERVAL_SECONDS'):
        monkeypatch.delenv(name,raising=False)
    (tmp_path/'.env').write_text('GEMINI_MODEL=main\nGEMINI_AGENT_MODEL=agent\nGEMINI_JUDGE_MODEL=judge\nGEMINI_EMBEDDING_MODEL=embedding\nGEMINI_MIN_INTERVAL_SECONDS=15',encoding='utf-8')
    s=get_settings()
    assert (s.model,s.agent_model,s.judge_model,s.embedding_model)==('main','agent','judge','embedding')
    monkeypatch.setenv('GEMINI_AGENT_MODEL','process-agent')
    assert get_settings().agent_model=='process-agent'
    (tmp_path/'.env').write_text('',encoding='utf-8')
    monkeypatch.delenv('GEMINI_AGENT_MODEL')
    s=get_settings()
    assert s.model==s.agent_model==s.judge_model=='gemini-3.5-flash'
    assert s.embedding_model=='gemini-embedding-001'


def test_structured_daily_and_retry_headers_do_not_expose_errors():
    response=httpx.Response(429,headers={'Retry-After':'90'})
    error=ClientError(429,{'error':{'message':'SECRET','details':[
        {'@type':'type.googleapis.com/google.rpc.QuotaFailure','violations':[{'quotaId':'GenerateRequestsPerDayPerProjectPerModel-FreeTier'}]},
        {'@type':'type.googleapis.com/google.rpc.RetryInfo','retryDelay':'100s'}]}},response)
    assert limit_evidence(error)=={'daily_limit':True,'retry_after_seconds':100}
    assert 'SECRET' not in json.dumps(limit_evidence(error))
    assert limit_evidence(ClientError(429,{'error':{'message':'perday SECRET'}}))['daily_limit'] is False


def test_retry_after_http_date_and_daily_reset():
    now=datetime(2026,10,17,12,tzinfo=timezone.utc)
    error=ServerError(503,{},httpx.Response(503,headers={'Retry-After':'Sat, 17 Oct 2026 12:02:00 GMT'}))
    assert limit_evidence(error,now)['retry_after_seconds']==120
    assert next_daily_reset(now)==datetime(2026,10,18,7,tzinfo=timezone.utc)


def test_persistent_daily_block_prevents_next_request(isolated):
    with pytest.raises(ClientError):
        with limits.request_slot(isolated,'main'):
            raise ClientError(429,{'error':{'details':[{'@type':'google.rpc.QuotaFailure',
                'violations':[{'quotaId':'GenerateRequestsPerDayPerProjectPerModel'}]}]}})
    limits._last.clear()  # Simular novo controller/processo com o mesmo estado persistido.
    with pytest.raises(ChatFailure) as caught:
        with limits.request_slot(isolated,'main'):
            pytest.fail('Não pode entrar em nova requisição')
    assert caught.value.category=='daily_limit'
    assert 'fake-private-key' not in limits._state_path(isolated).read_text()
    with limits.request_slot(isolated,'other-model'):
        pass  # Estado separado, sem troca automática no aplicativo.


def test_retry_after_pauses_without_retry(isolated):
    with pytest.raises(ServerError):
        with limits.request_slot(isolated,'main'):
            raise ServerError(503,{},httpx.Response(503,headers={'Retry-After':'120'}))
    with pytest.raises(ChatFailure) as caught:
        with limits.request_slot(isolated,'main'):
            pytest.fail('Deve respeitar Retry-After')
    assert caught.value.category=='cooldown'


def test_daily_error_remains_safe_in_operation():
    with pytest.raises(ChatFailure) as caught:
        with operation('generation'):
            raise ClientError(429,{'error':{'message':'SECRET','details':[{'@type':'google.rpc.QuotaFailure',
                'violations':[{'quotaId':'GenerateRequestsPerDayPerProjectPerModel'}]}]}})
    assert caught.value.category=='daily_limit' and caught.value.code==429
    assert 'SECRET' not in caught.value.user_message


def test_agents_and_final_synthesis_use_separate_gateways():
    from agro_ai.agents.orchestrator import AgentOrchestrator
    calls=[]
    class Gateway:
        def __init__(self,settings):
            self.settings=settings
        def stream(self,*args):
            calls.append(self.settings.model)
            yield 'Resposta de teste.'
        def close(self):
            pass
    class Tools:
        def stock_and_orders(self,*args):
            return {}
    s=Settings('fake','main','embedding',agent_model='cheap',judge_model='judge')
    runner=AgentOrchestrator(s,Gateway,tools=Tools())
    history=[{'role':'user','content':'Quais estoques existem?'}]
    prepared=runner.prepare(history)
    assert ''.join(runner.stream_answer(prepared,history))=='Resposta de teste.'
    assert calls==['cheap','main']
    runner.close()


def test_judge_selects_judge_model(monkeypatch):
    from agro_ai.evaluation.judge import GeminiJudge
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(close=lambda:None))
    s=Settings('fake','main','embedding',agent_model='cheap',judge_model='judge')
    judge=GeminiJudge(s,None)
    assert judge.model=='judge'
    judge.close()


def test_pacing_between_requests(isolated,monkeypatch):
    sleeps=[]
    monkeypatch.setattr(limits.time,'monotonic',lambda:1000)
    monkeypatch.setattr(limits.time,'sleep',sleeps.append)
    s=replace(isolated,request_interval_seconds=15)
    with limits.request_slot(s,'main'):
        pass
    with limits.request_slot(s,'main'):
        pass
    assert sleeps==[15]


def test_gateway_does_not_retry_503_with_retry_after():
    from agro_ai.gemini import GeminiGateway
    calls=[]
    def generate(**kwargs):
        calls.append(1)
        raise ServerError(503,{},httpx.Response(503,headers={'Retry-After':'10'}))
    gateway=GeminiGateway.__new__(GeminiGateway)
    gateway.settings=SimpleNamespace(model='main')
    gateway.client=SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate))
    with pytest.raises(ServerError):
        list(gateway.stream([],'test'))
    assert calls==[1]
