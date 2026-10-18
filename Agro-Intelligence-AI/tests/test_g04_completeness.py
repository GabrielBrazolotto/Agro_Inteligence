from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from decimal import Decimal
import pytest

from agro_ai.config import ROOT, get_settings
from agro_ai.agents.tools import SystemTools
from agro_ai.agents.orchestrator import WorkState, PreparedRun, factual_answer, AgentOrchestrator, monthly_answer_complete
from agro_ai.evaluation.batches import golden, execute_batch, consolidate
from agro_ai.evaluation.cache import EvaluationCache, reference_state
from agro_ai.evaluation.completeness import response_completeness
from agro_ai.evaluation.reference import reference_rows, check_finances


@pytest.fixture
def monthly():
    settings=get_settings()
    case=next(c for c in golden() if c['id']=='G04')
    indicators=SystemTools(settings.database).commercial(case['question'])
    evidence=[{'id':'e1','origin':'comercial.indicadores','content':indicators}]
    state=WorkState(results={'comercial':{'indicadores':indicators}})
    answer=factual_answer(PreparedRun(state,['comercial'],case['question']))
    return settings,case,evidence,answer


def test_monthly_tool_all_periods_and_fallback_reconcile_with_sql(monthly):
    settings,case,evidence,answer=monthly
    actual=evidence[0]['content']['mensal']
    expected=reference_rows(settings.database,'monthly')
    assert [r['mes'] for r in actual]==[r['mes'] for r in expected]
    assert len(actual)==12 and actual[0]['mes']=='2025-10' and actual[-1]['mes']=='2026-09'
    assert all(a['receita_faturada']==b['valor'] for a,b in zip(actual,expected))
    assert sum(r['receita_faturada'] for r in actual)==Decimal('493126517.02')
    assert check_finances(settings.database,['monthly'],answer)[0]['status']=='passed'
    assert response_completeness(case,answer,evidence)['status']=='passed'


@pytest.mark.parametrize('mutation',[
    lambda a:a.replace('2026-01:', 'Janeiro:'),
    lambda a:a.replace('2026-01: R$ 20.195.392,48','2026-01: R$ 20.195.392,49'),
    lambda a:a+'\n2026-01: R$ 20.195.392,48',
    lambda a:'R$ 493.126.517,02',
    lambda a:a.replace('2026-01: R$ 20.195.392,48','2026-01: 20.195.392,48'),
])
def test_incomplete_monthly_answers_not_reusable(monthly,mutation):
    _,case,evidence,answer=monthly
    assert response_completeness(case,mutation(answer),evidence)['status']=='failed'


def test_missing_or_truncated_context_not_complete(monthly):
    _,case,evidence,answer=monthly
    assert response_completeness(case,answer,[])['status']=='failed'
    evidence=deepcopy(evidence);evidence[0]['content']['mensal'].pop()
    assert response_completeness(case,answer,evidence)['reason']=='incomplete_monthly_evidence'


def test_cache_excludes_historical_incomplete_even_with_valid_grades(monthly,tmp_path):
    settings,case,evidence,answer=monthly
    cache=EvaluationCache(tmp_path);state=reference_state(settings)
    path=ROOT/'reports/evaluation/20261018T122104Z-batch-a8ba57/results.json'
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    historical=next(r for r in json.loads(path.read_text(encoding='utf-8'))['results'] if r['id']=='G04')
    response=cache.put_response(case,historical,state,{'report':str(path)})
    for name in ('faithfulness','answer_relevancy'):
        cache.put_metric(response,name,historical['metrics'],{},'historical')
    assert cache.response(case,state) is None
    assert cache.metric(response,'answer_relevancy')['metric']['score']==0
    row=consolidate(cache,[case],state)['cases'][0]
    assert row['status']=='response_incomplete' and row['executed']
    assert row['rejected_cached_responses'][0]['historical_metrics']['answer_relevancy']['score']==0
    valid=cache.put_response(case,{'answer':answer,'evidence':evidence},state,{'test':True})
    assert cache.response(case,state)['key']==valid['key']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before


def test_new_incomplete_response_not_sent_to_judge(monthly,tmp_path,monkeypatch):
    settings,case,evidence,answer=monthly
    class Turn:
        tools=[];answer_mode='factual'
        def __init__(self,*args):
            self.evidence={'comercial':{'indicadores':evidence[0]['content']}}
        def prepare(self,history): pass
        def stream(self): yield 'Somente totais gerais.'
        def close(self): pass
    monkeypatch.setattr('agro_ai.evaluation.batches.ChatTurn',Turn)
    monkeypatch.setattr('agro_ai.evaluation.batches.GeminiJudge',lambda *a:pytest.fail('não julgar resposta incompleta'))
    cache=EvaluationCache(tmp_path/'cache')
    _,report=execute_batch(replace(settings,request_interval_seconds=0),cache,['G04'],False,0,1,tmp_path/'report')
    assert report['actual_api_calls']==0
    assert report['results'][0]['validation_failure']['reason']=='incomplete_response'
    assert report['results'][0]['metrics']['faithfulness']['score'] is None
    assert cache.response(case,reference_state(settings)) is None


def test_generated_monthly_omission_uses_actual_complete_fallback(monthly):
    settings,case,evidence,answer=monthly
    class Gateway:
        def stream(self,*args):
            yield 'Totais gerais, sem detalhamento.'
    indicators=evidence[0]['content']
    assert monthly_answer_complete(answer,indicators['mensal'])
    state=WorkState(results={'comercial':{'indicadores':indicators}})
    prepared=PreparedRun(state,['comercial'],case['question'],Gateway())
    actual=''.join(AgentOrchestrator(settings,use_llm=False).stream_answer(prepared,
        [{'role':'user','content':case['question']}]))
    assert 'Totais gerais, sem detalhamento.' not in actual
    assert check_finances(settings.database,['monthly'],actual)[0]['status']=='passed'
    assert state.answer_mode=='factual'
    assert state.trace[-1]['reason']=='incomplete_monthly_response'
