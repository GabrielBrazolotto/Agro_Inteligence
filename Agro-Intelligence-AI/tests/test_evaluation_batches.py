from dataclasses import replace
import json
from types import SimpleNamespace
import pytest
from google.genai.errors import ClientError

from agro_ai.config import ROOT,get_settings
from agro_ai.evaluation.cache import EvaluationCache,reference_state,file_digest
from agro_ai.evaluation.batches import golden,plan,batches,execute_batch,consolidate
from agro_ai.evaluation.judge import answer_units,IndexedRelevancy,score_indexed_relevancy

SOURCE=ROOT/'reports/evaluation/20261017T134931Z-two-cases/results.json'


@pytest.fixture
def imported(tmp_path):
    settings=replace(get_settings(),request_interval_seconds=0)
    state=reference_state(settings)
    cache=EvaluationCache(tmp_path/'cache')
    before=file_digest(SOURCE)
    cache.import_legacy(SOURCE,golden(),settings,state)
    assert file_digest(SOURCE)==before
    return cache,settings,state


def test_indexed_citations_resolve_exact_offsets_and_require_all_units():
    answer='**Receita: R$ 10,00**\n\n- margem: 2%\n'
    units=answer_units(answer)
    assert len(units)==2
    for unit in units:
        assert answer[unit['start']:unit['end']]==unit['text']
    value={'verdicts':[{'unit_id':unit['unit_id'],'relevant':True,'reason':'test'} for unit in units],'explanation':'test'}
    score=score_indexed_relevancy(IndexedRelevancy.model_validate(value),answer)
    assert score['answer_relevancy']['score']==1
    assert score['relevancy_judgment']['verdicts'][0]['quote']==units[0]['text']
    for invalid in [value['verdicts'][:1],value['verdicts']+[value['verdicts'][0]],
                    [{'unit_id':'Atributos ...','relevant':True,'reason':'test'}]]:
        with pytest.raises(ValueError):
            score_indexed_relevancy(IndexedRelevancy(verdicts=invalid,explanation='test'),answer)


def test_plan_no_network_preserves_valid_history_and_prepares_16(imported,monkeypatch):
    cache,settings,state=imported
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:pytest.fail('plan não pode inicializar SDK'))
    status=plan(cache,golden(),state,2)
    assert status['consolidated']['summary']['evaluated']==1
    assert status['consolidated']['summary']['partially_evaluated']==1
    assert status['consolidated']['summary']['not_executed']==16
    assert status['baseline_pending']==['G12']
    assert len(status['batches'])==8
    triples=batches(status['remaining_case_ids'],3)
    assert all(len(group) in (2,3) for group in triples)
    assert [item for group in triples for item in group]==status['remaining_case_ids']


def test_cache_rejects_invalid_scores_and_is_immutable(imported):
    cache,settings,state=imported
    case=golden()[0];response=cache.response(case,state)
    old=cache.metric(response,'answer_relevancy')
    assert old['metric']['score']==2/3
    changed={'answer_relevancy':{'status':'evaluated','score':1.0}}
    cache.put_metric(response,'answer_relevancy',changed,{},'different')
    assert cache.metric(response,'answer_relevancy')==old
    assert cache.response(case,{**state,'database':'changed'}) is None
    g12=cache.response(golden()[11],state)
    assert cache.put_metric(g12,'answer_relevancy',{'answer_relevancy':{'status':'invalid_judgment','score':None}}, {},'invalid') is None
    assert cache.metric(g12,'answer_relevancy') is None


def test_pending_g12_only_judges_relevancy_then_reuses_it(imported,monkeypatch,tmp_path):
    cache,settings,state=imported
    requests=[]
    def generate(**kwargs):
        payload=json.loads(kwargs['contents']);requests.append(payload)
        assert 'answer' not in payload  # Não pedir afirmações de Faithfulness já válidas.
        return SimpleNamespace(text=json.dumps({'verdicts':[{'unit_id':u['unit_id'],'relevant':True,'reason':'mock'}
            for u in payload['answer_units']],'explanation':'mock'}),usage_metadata=None)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr('agro_ai.evaluation.batches.ChatTurn',lambda *args:pytest.fail('Não regenerar resposta ML'))
    before=file_digest(SOURCE)
    _,report=execute_batch(settings,cache,['G12'],True,0,1,tmp_path/'run1')
    assert report['actual_api_calls']==1
    assert report['results'][0]['requested_metrics']==['answer_relevancy']
    assert report['results'][0]['reused_metrics']==['faithfulness']
    assert len(requests)==1 and file_digest(SOURCE)==before
    _,second=execute_batch(settings,cache,['G12'],True,0,1,tmp_path/'run2')
    assert second['actual_api_calls']==0 and len(requests)==1
    assert consolidate(cache,golden(),state)['summary']['evaluated']==2


def test_rate_limit_keeps_partial_metric_and_stops_batch(imported,monkeypatch,tmp_path):
    cache,settings,state=imported
    def fail(**kwargs):
        raise ClientError(429,{'error':{'message':'SECRET'}})
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=fail)))
    _,report=execute_batch(settings,cache,['G12','G02'],False,0,1,tmp_path/'run')
    assert report['actual_api_calls']==1
    assert report['results'][0]['metrics']['faithfulness']['score']==1
    assert report['results'][0]['metrics']['answer_relevancy']['score'] is None
    assert report['results'][1]['generation_status']=='not_executed'
    assert 'SECRET' not in json.dumps(report,default=str)
    status=consolidate(cache,golden(),state)
    assert status['summary']['partially_evaluated']==1
    assert status['summary']['cases_with_infrastructure_failure']==1


def test_cache_integrity_and_no_historical_replay_overwrite(imported,tmp_path):
    cache,settings,state=imported
    path=next((cache.directory/'responses/G01').glob('*.json'))
    data=json.loads(path.read_text(encoding='utf-8'));data['payload']['answer']='tampered'
    path.write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(ValueError,match='cache_integrity_error'):
        cache.response(golden()[0],state)
    from agro_ai.evaluation.resume import replay_saved_judgments
    before=file_digest(SOURCE)
    replay_saved_judgments(SOURCE.parent,tmp_path/'new-report')
    assert file_digest(SOURCE)==before
    with pytest.raises(ValueError,match='report_directory_already_exists'):
        replay_saved_judgments(SOURCE.parent,SOURCE.parent)


def test_fresh_batch_caches_responses_and_both_metrics_without_repeating(monkeypatch,tmp_path):
    import agro_ai.evaluation.batches as module
    cache=EvaluationCache(tmp_path/'cache')
    settings=replace(get_settings(),request_interval_seconds=0)
    prepared=[];requests=[]
    class Turn:
        def __init__(self,*args):
            self.tools=[{'tool':'duckdb_estoque_pedidos','status':'ok'}]
            self.evidence={'estoque':{'contagem':60}}
            self.answer_mode='gemini'
        def prepare(self,history):
            prepared.append(history[-1]['content'])
        def stream(self):
            yield '60 posições.'
        def close(self):
            pass
    def generate(**kwargs):
        payload=json.loads(kwargs['contents']);requests.append(payload)
        return SimpleNamespace(text=json.dumps({'claims':[{'claim_id':u['claim_id'],'factual':True,'supported':True,'snippet_ids':[payload['evidence_snippets'][0]['snippet_id']],'reason':'mock'} for u in payload['claim_units']],
            'verdicts':[{'unit_id':unit['unit_id'],'relevant':False,'reason':'mock baixa relevância'} for unit in payload['answer_units']],
            'explanation':'mock'}),usage_metadata=None)
    monkeypatch.setattr(module,'ChatTurn',Turn)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    _,first=execute_batch(settings,cache,['G02','G03'],False,0,2,tmp_path/'first')
    assert len(prepared)==len(requests)==2
    assert first['results'][0]['metrics']['answer_relevancy']['score']==0
    _,second=execute_batch(settings,cache,['G02','G03'],False,0,2,tmp_path/'second')
    assert second['actual_api_calls']==0 and len(prepared)==len(requests)==2
    assert second['results'][0]['metrics']['answer_relevancy']['score']==0
    with pytest.raises(ValueError):
        execute_batch(settings,cache,['G02','G03','G04','G05'],False,0,2,tmp_path/'too-many')


def test_not_applicable_is_resolved_without_inventing_numeric_score(imported):
    cache,settings,state=imported
    case=next(case for case in golden() if case['id']=='G16')
    response=cache.put_response(case,{'answer':'Pode esclarecer o critério?', 'evidence':[],
        'generation_status':'ok','tools':[]},state,{'test':True})
    assessment={'faithfulness':{'status':'not_applicable','score':None},
                'answer_relevancy':{'status':'evaluated','score':.5}}
    for name in assessment:
        cache.put_metric(response,name,assessment,{'test':True},'test')
    row=next(row for row in consolidate(cache,golden(),state)['cases'] if row['id']=='G16')
    assert row['status']=='evaluated'
    assert row['metrics']['faithfulness']['score'] is None
