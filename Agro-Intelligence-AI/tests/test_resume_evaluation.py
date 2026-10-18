from dataclasses import replace
from types import SimpleNamespace
import json
import pytest
from google.genai.errors import ClientError

from agro_ai.config import ROOT,get_settings
from agro_ai.evaluation.resume import reusable_answer,Ledger,run_two
from agro_ai.evaluation.runner import Limiter

SOURCE=ROOT/'reports/evaluation/20261017T130820Z/results.json'


def test_cache_preserves_answer_context_and_historical_failure():
    case=json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))[0]
    original=json.loads(SOURCE.read_text(encoding='utf-8'))['results'][0]
    row=reusable_answer(SOURCE,case,get_settings())
    assert row['answer']==original['answer'] and row['evidence']==original['evidence']
    assert row['generation_status']=='reused' and row['original_generation_status']=='degraded'
    assert row['api_failures']==[] and row['historical_api_failures']
    assert reusable_answer(SOURCE,{**case,'question':'different'},get_settings()) is None


def test_cache_rejects_changed_evidence_and_partial_answers(tmp_path):
    report=json.loads(SOURCE.read_text(encoding='utf-8'))
    case=json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))[0]
    report['results'][0]['evidence'][0]['content']={'invented':True}
    p=tmp_path/'source.json';p.write_text(json.dumps(report),encoding='utf-8')
    assert reusable_answer(p,case,get_settings()) is None
    report['results'][0]['generation_status']='failed'
    p.write_text(json.dumps(report),encoding='utf-8')
    assert reusable_answer(p,case,get_settings()) is None


def test_ledger_uses_final_cumulative_usage_and_counts_attempts():
    ledger=Ledger(Limiter(0,2))
    def chunks():
        for _ in range(2):
            yield SimpleNamespace(usage_metadata=SimpleNamespace(prompt_token_count=10,total_token_count=12))
    assert len(list(ledger.wrap(chunks,'fake','generation',True)()))==2
    assert len(ledger.records)==1 and ledger.records[0]['usage']['total']==12


def test_cosmetic_quotes_are_valid_but_abbreviations_do_not_invalidate_other_metric():
    from agro_ai.evaluation.judge import Judgment,score_judgment
    value={'claims':[{'quote':'Receita 10','supported':True,'evidence_ids':['e1'],'reason':'mock'}],
        'relevance_units':[{'quote':'Receita ...','relevant':True,'reason':'mock'}],'explanation':'mock'}
    result=score_judgment(Judgment.model_validate(value),'**Receita 10**',[{'id':'e1'}])
    assert result['faithfulness']['score']==1
    assert result['answer_relevancy']['score'] is None
    assert result['answer_relevancy']['status']=='invalid_judgment'


@pytest.mark.parametrize('api_failure',[False,True])
def test_resume_never_runs_more_than_two_and_does_not_regenerate_cache(monkeypatch,tmp_path,api_failure):
    import agro_ai.evaluation.resume as module
    generated=[]
    def generate(**kwargs):
        if api_failure:
            raise ClientError(429,{'error':{'message':'SECRET'}})
        payload=json.loads(kwargs['contents'])
        result={'claims':[{'claim_id':u['claim_id'],'factual':True,'supported':True,
            'snippet_ids':[payload['evidence_snippets'][0]['snippet_id']],'reason':'mock'} for u in payload['claim_units']],
            'verdicts':[{'unit_id':u['unit_id'],'relevant':True,'reason':'mock'} for u in payload['answer_units']],
            'explanation':'mock'}
        return SimpleNamespace(text=json.dumps(result),usage_metadata=None)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(
        close=lambda:None,models=SimpleNamespace(generate_content=generate)))
    class Turn:
        def __init__(self,*args):
            self.tools=[{'tool':'duckdb_estoque_pedidos','status':'ok'}]
            self.evidence={'estoque':{'abastecimento':{'total':60}}}
            self.answer_mode='gemini'
        def prepare(self,history):
            generated.append(history[-1]['content'])
        def stream(self):
            yield '60 posições.'
        def close(self):
            pass
    monkeypatch.setattr(module,'ChatTurn',Turn)
    s=replace(get_settings(),request_interval_seconds=0)
    _,report=run_two(s,SOURCE,interval=0,output=tmp_path)
    assert len(report['results'])==2 and report['selected_cases']==['G01','G02']
    assert report['reused_answers']==1
    assert len(generated)==(0 if api_failure else 1)
    if api_failure:
        assert report['results'][0]['metrics']['faithfulness']['score'] is None
        assert report['results'][1]['generation_status']=='not_executed'
        assert 'SECRET' not in json.dumps(report,default=str)
    else:
        assert report['summary']['questions_evaluated']==2
    with pytest.raises(ValueError):
        run_two(s,SOURCE,['G01','G02','G03'],interval=0,output=tmp_path)
