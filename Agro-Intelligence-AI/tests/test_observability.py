from contextlib import contextmanager
from types import SimpleNamespace
from threading import Event
import json
from uuid import uuid4

import pytest
from google.genai.errors import ServerError

import agro_ai.observability as obs


@pytest.mark.parametrize('code,category',[(401,'authentication'),(403,'authentication'),(404,'configuration'),(429,'rate_limit'),(503,'service')])
def test_auth_http_diagnostic_is_sanitized(code,category):
    class Failure(Exception):
        status_code=code
    def fail():
        raise Failure('SECRET credential body')
    result=obs.check_authentication(SimpleNamespace(auth_check=fail))
    assert result=={'ok':False,'category':category,'http_code':code}
    assert 'SECRET' not in json.dumps(result)


def test_auth_network_permission_timeout_and_success():
    import httpx
    def blocked():
        try:
            raise PermissionError('SECRET')
        except PermissionError as cause:
            raise httpx.ConnectError('SECRET') from cause
    def timeout():
        raise httpx.ReadTimeout('SECRET')
    assert obs.check_authentication(SimpleNamespace(auth_check=blocked))['category']=='network_permission'
    assert obs.check_authentication(SimpleNamespace(auth_check=timeout))['category']=='timeout'
    assert obs.check_authentication(SimpleNamespace(auth_check=lambda:True))['ok']
    assert obs.check_authentication(None)['category']=='configuration'


class FakeSpan:
    def __init__(self,record):
        self.record=record
    def update(self,**values):
        self.record['updates'].append(values)


class FakeClient:
    def __init__(self):
        self.records=[]
        self.stack=[]
        self.exits=[]
        self.flushes=0
    @contextmanager
    def start_as_current_observation(self,**values):
        record={**values,'updates':[],'parent':self.stack[-1]['name'] if self.stack else None}
        self.records.append(record)
        self.stack.append(record)
        try:
            yield FakeSpan(record)
        except BaseException as error:
            self.exits.append(error)
            raise
        finally:
            self.stack.pop()
    def get_current_trace_id(self):
        return 'a'*32
    def flush(self):
        self.flushes+=1


@pytest.fixture
def client(monkeypatch):
    client=FakeClient()
    telemetry=obs.Telemetry(client)
    monkeypatch.setattr(obs,'get_telemetry',lambda:telemetry)
    return client


def test_parentage_privacy_and_latencies(client):
    with obs.chat_request('PRIVATE-PROMPT email@example.com',[]) as request:
        with obs.observation('agent.estoque',as_type='agent',agent='estoque',prompt='PRIVATE-PROMPT'):
            with obs.observation('test.tool',as_type='tool',tool='duckdb_estoque_pedidos'):
                obs.annotate_current(output='PRIVATE-RESULT',sql='SELECT PRIVATE',result_rows=20)
        request.update(output_characters=15)
    request.telemetry.flush(wait=True)
    assert client.records[0]['name']=='agro.chat.request'
    assert client.records[-1]['parent']=='agro.agent.estoque'
    payload=json.dumps(client.records)
    assert 'PRIVATE' not in payload and 'email@example.com' not in payload
    assert 'latency_ms' in payload and 'result_rows' in payload
    assert client.flushes>=1


@pytest.mark.parametrize('mode,status',[('gemini','degraded'),('factual','fallback')])
def test_root_redacted_io_and_response_status_keep_child_error(client,mode,status):
    with obs.chat_request('SECRET email@example.com',[]) as root:
        with pytest.raises(ServerError):
            with obs.observation('gemini.generate',as_type='generation'):
                raise ServerError(429,{'error':{'message':'SECRET'}})
        assert obs.complete_chat('PRIVATE COMMERCIAL OUTPUT',[{'status':'failed'}],mode)==status
    records=client.records
    payload=json.dumps(records)
    assert 'SECRET' not in payload and 'PRIVATE' not in payload and 'email@example.com' not in payload
    assert any('input' in update and update['input']['content']=='omitted_for_privacy' for update in records[0]['updates'])
    assert any('output' in update and update['output']['status']==status for update in records[0]['updates'])
    child=next(row for row in records if row['name']=='agro.gemini.generate')
    assert any(update.get('level')=='ERROR' for update in child['updates'])
    response=next(row for row in records if row['name']=='agro.chat.response')
    assert response['updates'][-1]['metadata']['status']==status


def test_real_business_exception_is_not_serialized_or_swallowed(client):
    with pytest.raises(ServerError):
        with obs.chat_request('private',[]):
            with obs.observation('test.failure'):
                raise ServerError(503,{'error':{'message':'SECRET KEY AND PRIVATE PROMPT'}})
    assert client.exits==[]
    serialized=json.dumps(client.records)
    assert 'SECRET' not in serialized and 'PRIVATE' not in serialized
    assert '503' in serialized and 'failed' in serialized


@pytest.mark.parametrize('stage',['start','update','end','flush'])
def test_telemetry_errors_do_not_break_chat(monkeypatch,stage,caplog):
    class Broken(FakeClient):
        @contextmanager
        def start_as_current_observation(self,**kwargs):
            if stage=='start':
                raise RuntimeError('SECRET')
            span=FakeSpan({'updates':[]})
            if stage=='update':
                span.update=lambda **kwargs:(_ for _ in ()).throw(RuntimeError('SECRET'))
            yield span
            if stage=='end':
                raise RuntimeError('SECRET')
        def flush(self):
            if stage=='flush':
                raise RuntimeError('SECRET')
    telemetry=obs.Telemetry(Broken())
    monkeypatch.setattr(obs,'get_telemetry',lambda:telemetry)
    with obs.chat_request('PRIVATE',[]):
        actual='chat keeps working'
    telemetry.flush(wait=True)
    assert actual=='chat keeps working'
    assert 'SECRET' not in caplog.text


def test_flush_wait_is_bounded():
    release=Event()
    client=SimpleNamespace(flush=lambda:release.wait(1))
    telemetry=obs.Telemetry(client)
    try:
        assert not telemetry.flush(wait=True,timeout=.001)
    finally:
        release.set()
        telemetry.flush_thread.join(1)


def test_disabled_or_missing_configuration_never_initializes_sdk(monkeypatch):
    import langfuse
    monkeypatch.setattr(langfuse,'Langfuse',lambda **kwargs:pytest.fail('SDK should not start'))
    assert obs._build_telemetry(obs.TelemetrySettings(False,'fake','fake','https://example.com')).client is None
    assert obs._build_telemetry(obs.TelemetrySettings(True)).client is None
    assert 'fake-secret' not in repr(obs.TelemetrySettings(True,'fake-public','fake-secret','https://example.com'))


def test_env_reading_and_opt_out(monkeypatch,tmp_path):
    monkeypatch.setattr(obs,'ROOT',tmp_path)
    for name in ('LANGFUSE_ENABLED','LANGFUSE_PUBLIC_KEY','LANGFUSE_SECRET_KEY','LANGFUSE_BASE_URL'):
        monkeypatch.delenv(name,raising=False)
    (tmp_path/'.env').write_text('LANGFUSE_ENABLED=true\nLANGFUSE_PUBLIC_KEY=fake\nLANGFUSE_SECRET_KEY=fake\nLANGFUSE_BASE_URL=https://example.com',encoding='utf-8')
    assert obs.telemetry_settings().enabled and obs.telemetry_settings().configured
    monkeypatch.setenv('LANGFUSE_ENABLED','false')
    assert not obs.telemetry_settings().enabled


def test_generator_usage_uses_api_snapshot_without_summing_or_inventing_cost(client):
    from agro_ai.gemini import GeminiGateway
    gateway=GeminiGateway.__new__(GeminiGateway)
    gateway.settings=SimpleNamespace(model='gemini-3.5-flash')
    usage=SimpleNamespace(prompt_token_count=100,candidates_token_count=20,total_token_count=125,thoughts_token_count=5)
    gateway.client=SimpleNamespace(models=SimpleNamespace(generate_content_stream=lambda **kwargs:iter([
        SimpleNamespace(text='hello',usage_metadata=usage),SimpleNamespace(text=' world',usage_metadata=usage)])))
    with obs.chat_request('PRIVATE',[]):
        assert ''.join(gateway.stream([{'role':'user','content':'PRIVATE'}],'SECRET SYSTEM'))=='hello world'
    generation=next(row for row in client.records if row['as_type']=='generation')
    usage_updates=[row['usage_details'] for row in generation['updates'] if 'usage_details' in row]
    assert usage_updates[-1]=={'input':100,'output':20,'total':125,'reasoning':5}
    assert 'model' not in generation  # Sem precificação automática por model id.
    assert 'cost_details' not in json.dumps(client.records)
    assert 'PRIVATE' not in json.dumps(client.records) and 'SECRET' not in json.dumps(client.records)


def test_absent_usage_and_retry_are_not_fabricated(client,monkeypatch):
    from agro_ai.gemini import GeminiGateway
    calls=[]
    def stream(**kwargs):
        calls.append(1)
        if len(calls)==1:
            raise ServerError(503,{'error':{'message':'SECRET'}})
        yield SimpleNamespace(text='done')
    gateway=GeminiGateway.__new__(GeminiGateway)
    gateway.settings=SimpleNamespace(model='gemini-3.5-flash')
    gateway.client=SimpleNamespace(models=SimpleNamespace(generate_content_stream=stream))
    monkeypatch.setattr('agro_ai.gemini.time.sleep',lambda _:None)
    with obs.chat_request('PRIVATE',[]):
        assert ''.join(gateway.stream([],'PRIVATE'))=='done'
    generations=[row for row in client.records if row['as_type']=='generation']
    assert len(generations)==2
    assert 'failed' in json.dumps(generations[0]) and 'ok' in json.dumps(generations[1])
    assert 'usage_details' not in json.dumps(generations)


def test_sdk_real_export_in_memory_keeps_tree_and_omits_error_payload(monkeypatch):
    from langfuse import Langfuse
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.resources import Resource
    exporter=InMemorySpanExporter()
    provider=TracerProvider(resource=Resource({'service.name':'agro-test'}))
    sdk=Langfuse(public_key='pk-lf-local-test-'+uuid4().hex,secret_key='fake-only',
                 tracer_provider=provider,span_exporter=exporter)
    telemetry=obs.Telemetry(sdk)
    monkeypatch.setattr(obs,'get_telemetry',lambda:telemetry)
    with obs.chat_request('PRIVATE EMAIL',[]) as root:
        with pytest.raises(ValueError):
            with obs.observation('test.failure'):
                raise ValueError('SECRET RAW ERROR')
        obs.complete_chat('PRIVATE OUTPUT',[{'status':'failed'}],'gemini')
    assert telemetry.flush(wait=True)
    spans=exporter.get_finished_spans()
    top=next(span for span in spans if span.name=='agro.chat.request')
    child=next(span for span in spans if span.name=='agro.test.failure')
    assert child.parent.span_id==top.context.span_id
    assert top.end_time>=child.end_time
    assert not child.events
    assert 'PRIVATE' not in str([dict(span.attributes) for span in spans])
    assert 'SECRET' not in str([dict(span.attributes) for span in spans])
    sdk.shutdown()


@pytest.mark.parametrize('question',__import__('scripts.validate_observability',fromlist=['QUESTIONS']).QUESTIONS)
def test_five_question_flows_real_duckdb_ml_mock_provider(client,question):
    from agro_ai.config import get_settings
    from agro_ai.agents.tools import SystemTools
    from agro_ai.agents.orchestrator import AgentOrchestrator
    from agro_ai.gemini import GeminiGateway
    from agro_ai.config import ROOT
    class Index:
        @obs.observe('chroma.retrieve',as_type='retriever')
        def search(self,question):
            return [{'source':'politica_comercial.md','chunk':1,
                     'text':(ROOT/'data/documents/politica_comercial.md').read_text(encoding='utf-8')}]
        def synchronize(self):
            return 3
    def factory(settings):
        gateway=GeminiGateway.__new__(GeminiGateway)
        gateway.settings=settings
        gateway.client=SimpleNamespace(models=SimpleNamespace(generate_content_stream=lambda **kwargs:iter([
            SimpleNamespace(text='Síntese simulada das ferramentas.',usage_metadata=None)])),close=lambda:None)
        return gateway
    settings=get_settings()
    # Chave fictícia apenas para habilitar o caminho do gateway mockado.
    from dataclasses import replace
    settings=replace(settings,api_key='fake-only')
    runner=AgentOrchestrator(settings,factory,tools=SystemTools(settings.database,Index()))
    with obs.chat_request(question,[]) as root:
        history=[{'role':'user','content':question}]
        prepared=runner.prepare(history)
        answer=''.join(runner.stream_answer(prepared,history))
        with obs.observation('chat.response',output_characters=len(answer)):
            pass
    runner.close()
    names={row['name'] for row in client.records}
    assert {'agro.chat.request','agro.chat.response','agro.gemini.generate','agro.agent.tool'}<=names
    assert all('agro.agent.'+agent in names for agent in prepared.agents)
    assert all(item['status']=='ok' for item in prepared.state.trace)
    if 'backorder' in question:
        assert 'agro.ml.predict_backorder' in names
    assert question not in json.dumps(client.records)


@pytest.mark.parametrize('unfinished,missing_parent,complete',[(False,False,True),(True,False,False),(False,True,False)])
def test_v5_readback_requires_complete_tree(unfinished,missing_parent,complete):
    from scripts.validate_observability import verify_trace
    rows=[SimpleNamespace(id='root',name='agro.chat.request',trace_id='t',end_time=1,parent_observation_id=None),
          SimpleNamespace(id='child',name='agro.chat.response',trace_id='t',end_time=None if unfinished else 1,
                          parent_observation_id='missing' if missing_parent else 'root')]
    calls=[]
    def read(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(data=rows)
    sdk=SimpleNamespace(api=SimpleNamespace(observations=SimpleNamespace(get_many=read)))
    assert verify_trace(sdk,'t',{'agro.chat.request','agro.chat.response'})['complete'] is complete
    assert calls[0]['fields']=='core,basic,time'
