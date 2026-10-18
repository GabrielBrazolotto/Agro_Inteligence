import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import pytest

from agro_ai.config import ROOT,get_settings
from agro_ai.evaluation.faithfulness_audit import audit_report,write_audit
from agro_ai.evaluation.faithfulness import IndexedFaithfulness,score_indexed_faithfulness
from agro_ai.evaluation.cache import file_digest,EvaluationCache,reference_state
from agro_ai.evaluation.batches import golden

SOURCES={
    'G06':ROOT/'reports/evaluation/20261018T131059Z-pipeline-c774fe/judge-G06/results.json',
    'G15':ROOT/'reports/evaluation/20261018T144839Z-batch-ae229a/results.json'}


@pytest.mark.parametrize('case,claim,reason',[('G06','c006','nonfactual_marked_supported'),
    ('G15','c019','factual_supported_without_evidence')])
def test_real_rejected_judgments_stay_invalid_offline(case,claim,reason,monkeypatch):
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:pytest.fail('no network'))
    before=file_digest(SOURCES[case])
    result=audit_report(SOURCES[case],case)
    metric=result['derived_assessment']['faithfulness']
    assert metric['status']=='invalid_judgment' and metric['score'] is None
    assert result['matching_raw_ledger_entries']>=1
    assert result['preserved_answer_relevancy']['score']==1
    assert not result['offline_metric_valid'] and not result['verdict_modified']
    issues=result['derived_assessment']['faithfulness_validation']['issues']
    assert len(issues)==1
    assert issues[0]['claim_id']==claim and issues[0]['reasons']==[reason]
    assert not issues[0]['unknown_snippet_ids'] and not issues[0]['provided_snippet_ids']
    assert result['reconstructed_payload']['claim_units'][0]['claim_id']=='c001'
    assert result['reconstructed_payload']['evidence_snippets'][0]['snippet_id']=='s0001'
    assert before==file_digest(SOURCES[case])


def test_diagnostic_does_not_accept_unknown_zero_based_or_duplicate_refs():
    for ids,reason in [(['s0000'],'unknown_snippet_ids'),(['e1'],'unknown_snippet_ids'),
                       (['s0001','s0001'],'duplicate_snippet_ids')]:
        raw=IndexedFaithfulness(claims=[{'claim_id':'c001','factual':True,'supported':True,
            'snippet_ids':ids,'reason':'original unchanged'}],explanation='test')
        result=score_indexed_faithfulness(raw,'Receita 10',[{'id':'e1','content':10}])
        assert result['faithfulness']['score'] is None
        assert result['faithfulness_validation']['issues'][0]['reasons']==[reason]


def test_unsupported_claim_is_zero_not_automatically_reclassified():
    raw=IndexedFaithfulness(claims=[{'claim_id':'c001','factual':True,'supported':False,
        'snippet_ids':[],'reason':'O contexto não informa esse fato.'}],explanation='sem suporte')
    result=score_indexed_faithfulness(raw,'Fato sem suporte',[{'id':'e1','content':'outro conteúdo'}])
    assert result['faithfulness']['status']=='evaluated' and result['faithfulness']['score']==0


def test_audit_is_new_artifact_never_promotes_invalid_metric(tmp_path):
    before={c:file_digest(path) for c,path in SOURCES.items()}
    path,results=write_audit(list(SOURCES.values()),list(SOURCES),tmp_path/'audit')
    saved=json.loads((path/'results.json').read_text(encoding='utf-8'))
    assert saved['actual_api_calls']==0
    assert all(r['derived_assessment']['faithfulness']['score'] is None for r in saved['results'])
    assert all(not r['metric_cache_modified'] for r in saved['results'])
    assert before=={c:file_digest(p) for c,p in SOURCES.items()}
    with pytest.raises(ValueError): write_audit(list(SOURCES.values()),list(SOURCES),path)


def test_selected_single_case_judges_only_pending_faithfulness(tmp_path,monkeypatch):
    import agro_ai.evaluation.pipeline as module
    import agro_ai.evaluation.batches as batches
    cases=[{**golden()[5],'checks':[]},{**golden()[14],'checks':[]}]
    monkeypatch.setattr(module,'golden',lambda:cases);monkeypatch.setattr(batches,'golden',lambda:cases)
    settings=replace(get_settings(),request_interval_seconds=0)
    cache=EvaluationCache(tmp_path/'cache')
    for case in cases:
        response=cache.put_response(case,{'answer':'Fato sem prova.','evidence':[{'id':'e1','content':'outro conteúdo'}]},reference_state(settings),{})
        cache.put_metric(response,'answer_relevancy',{'answer_relevancy':{'status':'evaluated','score':1}}, {}, 'mock')
    calls=[]
    def generate(**kwargs):
        payload=json.loads(kwargs['contents']);calls.append(payload)
        assert 'answer_units' not in payload
        # Mock judge intentionally gives zero support: selection must not force approval.
        return SimpleNamespace(text=json.dumps({'claims':[{'claim_id':'c001','factual':True,
            'supported':False,'snippet_ids':[],'reason':'Não há prova nos trechos.'}],
            'explanation':'mock'}),usage_metadata=None)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    monkeypatch.setattr(batches,'ChatTurn',lambda *a:pytest.fail('must reuse saved response'))
    caps=module.policies_for(settings,tpm=1000000)
    _,run=module.run_pipeline(settings,cache,caps,interval=0,reserve=0,phase='judge',
        output=tmp_path/'run',budget_dir=tmp_path/'budget',case_ids=['G06'])
    assert len(calls)==1 and run['actual_api_calls']==1
    state=reference_state(settings)
    response=cache.response(cases[0],state)
    assert cache.metric(response,'faithfulness')['metric']['score']==0
    assert cache.metric(response,'answer_relevancy')['metric']['score']==1
    assert cache.metric(cache.response(cases[1],state),'faithfulness') is None
    with pytest.raises(ValueError):
        module.queue_plan(settings,cache,caps,case_ids=['G99'])
