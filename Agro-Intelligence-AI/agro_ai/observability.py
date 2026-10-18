"""Langfuse opcional, sem payloads e fail-open. Exceções originais nunca chegam ao SDK."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass,field
from functools import lru_cache,wraps
import inspect
import logging
import math
import os
import re
from threading import Thread,Lock
from time import perf_counter
from urllib.parse import urlsplit

from dotenv import dotenv_values
from agro_ai.config import ROOT

LOGGER=logging.getLogger('agro_ai')
_current=ContextVar('agro_observation',default=None)
SAFE_NUMBERS={'latency_ms','input_characters','output_characters','history_messages',
              'attempt','source_count','result_rows','http_code','first_token_ms'}
SAFE_LABELS={'agent','tool','stage','status','error_category','answer_mode','model_name','model_version'}


@dataclass(frozen=True)
class TelemetrySettings:
    enabled: bool=False
    public_key: str=field(default='',repr=False)
    secret_key: str=field(default='',repr=False)
    base_url: str=field(default='',repr=False)

    @property
    def configured(self):
        return bool(self.public_key and self.secret_key and self.base_url)


def telemetry_settings():
    values=dotenv_values(ROOT/'.env',encoding='utf-8-sig',interpolate=False)
    def value(name,default=''):
        return (os.environ.get(name,values.get(name)) or default).strip()
    return TelemetrySettings(value('LANGFUSE_ENABLED','false').lower() in ('true','1','yes'),
                             value('LANGFUSE_PUBLIC_KEY'),value('LANGFUSE_SECRET_KEY'),value('LANGFUSE_BASE_URL'))


def safe_metadata(values):
    result={}
    for key,value in values.items():
        if key in SAFE_NUMBERS and type(value) in (int,float) and math.isfinite(value) and value>=0:
            result[key]=value
        elif key in SAFE_LABELS and isinstance(value,str) and re.fullmatch(r'[a-z0-9_.-]{1,80}',value):
            if key in ('model_name','model_version') and not re.fullmatch(r'gemini-[a-z0-9.-]+',value):
                continue
            result[key]=value
    return result


def error_metadata(error):
    from google.genai.errors import APIError
    import httpx
    from agro_ai.diagnostics import ChatFailure,EmptyResponseError
    if isinstance(error,ChatFailure):
        return {'error_category':error.category,'http_code':error.code}
    if isinstance(error,APIError):
        from agro_ai.api_limits import limit_evidence
        return {'error_category':'daily_limit' if error.code==429 and limit_evidence(error)['daily_limit'] else 'api','http_code':error.code}
    return {'error_category':('timeout' if isinstance(error,httpx.TimeoutException) else
                              'connection' if isinstance(error,httpx.TransportError) else
                              'empty_response' if isinstance(error,EmptyResponseError) else 'local')}


class Telemetry:
    def __init__(self,client=None):
        self.client=client
        self.flush_thread=None
        self.flush_lock=Lock()
        self.last_flush_ok=None

    def flush(self,wait=False,timeout=5):
        if self.client is None:
            return False
        def work():
            try:
                self.client.flush()
                self.last_flush_ok=True
            except Exception:
                self.last_flush_ok=False
                LOGGER.warning('observability_flush_failed')
        with self.flush_lock:
            if self.flush_thread is None or not self.flush_thread.is_alive():
                self.last_flush_ok=None
                self.flush_thread=Thread(target=work,name='agro-telemetry-flush',daemon=True)
                self.flush_thread.start()
            thread=self.flush_thread
        if wait:
            thread.join(timeout)
            return not thread.is_alive() and self.last_flush_ok is True
        return True  # Enfileirado, não confirmação de entrega/ingestão.


@lru_cache(maxsize=2)
def _build_telemetry(settings):
    if not settings.enabled or not settings.configured:
        return Telemetry()
    try:
        url=urlsplit(settings.base_url)
        if (url.scheme not in ('https','http') or not url.hostname or url.username or url.password
                or url.query or url.fragment or (url.scheme=='http' and url.hostname not in ('localhost','127.0.0.1','::1'))):
            raise ValueError('Endpoint inválido')
        from langfuse import Langfuse
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        # Provider privado: não interceptar tracing de Chroma/HTTP de terceiros.
        provider=TracerProvider(resource=Resource({'service.name':'agro-intelligence-ai'}))
        for name in ('langfuse','opentelemetry','httpx','httpcore'):
            logging.getLogger(name).setLevel(logging.CRITICAL)
        client=Langfuse(public_key=settings.public_key,secret_key=settings.secret_key,
                        base_url=settings.base_url,timeout=3,debug=False,tracing_enabled=True,
                        sample_rate=1.,tracer_provider=provider,
                        should_export_span=lambda span:span.name.startswith('agro.'))
        return Telemetry(client)
    except Exception:
        LOGGER.warning('observability_initialization_failed')
        return Telemetry()


def get_telemetry():
    try:
        return _build_telemetry(telemetry_settings())
    except Exception:
        return Telemetry()


def check_authentication(client):
    """Diagnóstico sanitizado: não serializar mensagens, URLs ou corpos HTTP."""
    import httpx
    if client is None:
        return {'ok':False,'category':'configuration'}
    if not callable(getattr(client,'auth_check',None)):
        return {'ok':False,'category':'sdk_incompatible'}
    try:
        return {'ok':True,'category':'ok'} if client.auth_check() else {'ok':False,'category':'authentication_or_configuration'}
    except Exception as error:
        chain=[]
        seen=set()
        while error is not None and id(error) not in seen:
            seen.add(id(error))
            chain.append(error)
            error=error.__cause__ or error.__context__
        code=next((getattr(item,'status_code',None) for item in chain
                   if type(getattr(item,'status_code',None)) is int),None)
        category=('authentication' if code in (401,403) else
                  'configuration' if code in (400,404) else
                  'rate_limit' if code==429 else
                  'service' if code is not None and code>=500 else
                  'timeout' if any(isinstance(item,httpx.TimeoutException) for item in chain) else
                  'network_permission' if any(isinstance(item,PermissionError) for item in chain) else
                  'network' if any(isinstance(item,httpx.TransportError) for item in chain) else
                  'unknown')
        result={'ok':False,'category':category}
        if code is not None:
            result['http_code']=code
        return result


class Observation:
    def __init__(self,telemetry,span=None):
        self.telemetry=telemetry
        self.span=span
        self.status=None
        self.trace_id=None

    def update(self,**metadata):
        safe=safe_metadata(metadata)
        if 'status' in safe:
            self.status=safe['status']
        if self.span is not None:
            try:
                self.span.update(metadata=safe,level='ERROR' if self.status=='failed' else
                                 'WARNING' if self.status in ('fallback','degraded','rejected','needs_input') else 'DEFAULT',
                                 status_message=self.status or 'running')
            except Exception:
                LOGGER.warning('observability_update_failed')

    def redacted_io(self,kind,characters,status=None):
        if self.span is None or kind not in ('input','output'):
            return
        payload={'content':'omitted_for_privacy','characters':characters}
        payload.update(safe_metadata({'status':status}))
        try:
            self.span.update(**{kind:payload})
        except Exception:
            LOGGER.warning('observability_io_failed')

    def usage(self,usage_metadata):
        # Streaming retorna snapshots cumulativos: atualizar, nunca somar snapshots.
        fields={'input':'prompt_token_count','output':'candidates_token_count',
                'total':'total_token_count','reasoning':'thoughts_token_count',
                'cache_read':'cached_content_token_count'}
        values={key:value for key,attr in fields.items()
                if type(value:=getattr(usage_metadata,attr,None)) is int and value>=0}
        if values and self.span is not None:
            try:
                self.span.update(usage_details=values)
            except Exception:
                LOGGER.warning('observability_usage_failed')


@contextmanager
def observation(name,as_type='span',**metadata):
    parent=_current.get()
    # Uma pergunta = um root. Atualizações de tela/consultas avulsas não criam roots órfãos.
    telemetry=parent.telemetry if parent is not None else get_telemetry() if name=='chat.request' else Telemetry()
    handle=Observation(telemetry)
    scope=None
    started=perf_counter()
    try:
        if telemetry.client is not None:
            try:
                scope=telemetry.client.start_as_current_observation(
                    name='agro.'+name,as_type=as_type,metadata=safe_metadata(metadata))
                handle.span=scope.__enter__()
                handle.trace_id=telemetry.client.get_current_trace_id()
            except Exception:
                LOGGER.warning('observability_start_failed')
        token=_current.set(handle)
        try:
            yield handle
        except BaseException as error:
            handle.update(status='failed',**error_metadata(error))
            raise
        finally:
            handle.update(status=handle.status or 'ok',latency_ms=round((perf_counter()-started)*1000,3))
            _current.reset(token)
    finally:
        if scope is not None:
            try:
                # Nunca passar a exceção do negócio: o SDK poderia serializar mensagem/stack.
                scope.__exit__(None,None,None)
            except Exception:
                LOGGER.warning('observability_end_failed')


def annotate_current(**metadata):
    current=_current.get()
    if current is not None:
        current.update(**metadata)


def complete_chat(answer,tool_trace,answer_mode='gemini'):
    """Mesmo diagnóstico no Streamlit e CLI, sem exportar a resposta textual."""
    failures=any(row.get('status') in ('failed','rejected') for row in tool_trace)
    status='fallback' if answer_mode=='factual' else 'degraded' if failures else 'ok'
    root=_current.get()
    if root is not None:
        root.update(status=status,answer_mode=answer_mode,output_characters=len(answer))
        root.redacted_io('output',len(answer),status)
    with observation('chat.response',output_characters=len(answer),answer_mode=answer_mode) as response:
        response.update(status=status)
    return status


def observe(name,as_type='span'):
    def decorator(function):
        if inspect.isgeneratorfunction(function):
            @wraps(function)
            def generator(*args,**kwargs):
                with observation(name,as_type):
                    yield from function(*args,**kwargs)
            return generator
        @wraps(function)
        def wrapper(*args,**kwargs):
            with observation(name,as_type):
                return function(*args,**kwargs)
        return wrapper
    return decorator


@contextmanager
def chat_request(question,history):
    handle=None
    try:
        with observation('chat.request',as_type='chain',input_characters=len(question),
                         history_messages=len(history)) as handle:
            handle.redacted_io('input',len(question))
            with observation('chat.question',input_characters=len(question)):
                pass
            yield handle
    finally:
        if handle is not None:
            # Sair do root antes do flush, inclusive em erro ou cancelamento.
            try:
                handle.telemetry.flush(wait=False)
            except Exception:
                LOGGER.warning('observability_flush_schedule_failed')
