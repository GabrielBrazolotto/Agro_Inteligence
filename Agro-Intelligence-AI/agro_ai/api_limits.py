"""Serialização e bloqueios conservadores; nunca registrar corpos de erros."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import math
import re
from threading import RLock
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

from google.genai.errors import APIError
from agro_ai.config import ROOT
from agro_ai.diagnostics import ChatFailure,LOGGER

_lock=RLock()
_last={}


def limit_evidence(error,now=None):
    """Somente sinais estruturados de QuotaFailure/RetryInfo/Retry-After."""
    now=now or datetime.now(timezone.utc)
    seconds=None
    response=getattr(error,'response',None)
    headers=getattr(response,'headers',{}) or {}
    raw=headers.get('Retry-After')
    if raw:
        try:
            seconds=float(raw)
        except (ValueError,TypeError):
            try:
                seconds=max(0,(parsedate_to_datetime(raw)-now).total_seconds())
            except (ValueError,TypeError,OverflowError):
                pass
    details=getattr(error,'details',{})
    if isinstance(details,dict):
        details=details.get('error',details)
    details=details.get('details',[]) if isinstance(details,dict) else []
    daily=False
    for detail in details if isinstance(details,list) else []:
        if not isinstance(detail,dict):
            continue
        if str(detail.get('@type','')).endswith('QuotaFailure'):
            for violation in detail.get('violations',[]):
                if not isinstance(violation,dict):
                    continue
                identifier=str(violation.get('quotaId',''))+' '+str(violation.get('quotaMetric',''))
                daily=daily or bool(re.search(r'perday|per_day|requests/day',identifier,re.I))
        if str(detail.get('@type','')).endswith('RetryInfo'):
            match=re.fullmatch(r'(\d+(?:\.\d+)?)s',str(detail.get('retryDelay','')))
            if match:
                seconds=max(seconds or 0,float(match[1]))
    if seconds is not None and (not math.isfinite(seconds) or seconds<0):
        seconds=None
    return {'daily_limit':daily,'retry_after_seconds':seconds}


def next_daily_reset(now=None):
    now=now or datetime.now(timezone.utc)
    local=now.astimezone(ZoneInfo('America/Los_Angeles'))
    return (local+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)


def _state_path(settings):
    # Namespace local derivado da chave; nunca armazenar a chave propriamente dita.
    digest=hashlib.sha256(settings.api_key.encode()).hexdigest()[:20]
    return ROOT/'data/runtime/api_limits'/f'{digest}.json'


def _read(settings):
    path=_state_path(settings)
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    except Exception:
        # Estado ilegível exige intervenção; não apagar para forçar novas chamadas.
        raise ChatFailure('generation','limit_state_unavailable',reference=uuid4().hex[:12]) from None


def _save(settings,state):
    path=_state_path(settings)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(state),encoding='utf-8')
    temporary.replace(path)


def block_daily(settings,model):
    with _lock:
        state=_read(settings)
        state[model]={'until':next_daily_reset().isoformat(),'category':'daily_limit','http_code':429}
        _save(settings,state)


@contextmanager
def request_slot(settings,model,stage='generation'):
    """Segura o lock durante todo o streaming; nenhuma repetição automática de 429."""
    if not getattr(settings,'api_key',None):
        yield  # Objetos mínimos usados por testes; nunca utilizados em produção.
        return
    with _lock:
        state=_read(settings)
        entry=state.get(model)
        now=datetime.now(timezone.utc)
        if entry:
            remaining=(datetime.fromisoformat(entry['until'])-now).total_seconds()
            if remaining>0:
                # Não manter UI/CLI bloqueado durante Retry-After longo.
                raise ChatFailure(stage,entry['category'],entry.get('http_code',429),uuid4().hex[:12])
        key=(_state_path(settings).name,model)
        delay=max(0,getattr(settings,'request_interval_seconds',0)-(time.monotonic()-_last.get(key,-1e12)))
        if delay:
            time.sleep(delay)
        _last[key]=time.monotonic()
        try:
            yield
        except APIError as error:
            signal=limit_evidence(error)
            wait=signal['retry_after_seconds']
            if error.code==429 or wait is not None:
                category='daily_limit' if signal['daily_limit'] and error.code==429 else 'cooldown'
                until=next_daily_reset() if category=='daily_limit' else datetime.now(timezone.utc)+timedelta(seconds=max(wait or 0,60 if error.code==429 else 0))
                state[model]={'until':until.isoformat(),'category':category,'http_code':error.code}
                try:
                    _save(settings,state)
                except Exception:
                    LOGGER.warning('api_limit_state_write_failed')
                LOGGER.warning('api_limit http=%s daily=%s retry_after_seconds=%s',error.code,signal['daily_limit'],wait)
            raise
