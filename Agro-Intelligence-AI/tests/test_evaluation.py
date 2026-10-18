import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
from google.genai.errors import ClientError

from agro_ai.config import ROOT,get_settings
from agro_ai.evaluation.judge import Judgment,score_judgment
from agro_ai.evaluation.reference import check_finances,reference_rows,QUERIES
from agro_ai.evaluation.runner import execute_case,summarize,evidence_from_turn,Limiter,CallLimit,run


def golden():
    return json.loads((ROOT/'data/evaluation/golden.json').read_text(encoding='utf-8'))


def test_golden_has_domains_and_legitimate_references():
    rows=golden()
    assert len(rows)>=15 and len({r['id'] for r in rows})==len(rows)
    assert {'ambigua','fora_escopo','ml_valido','rag_politica','regional_margens','composta'}<={r['category'] for r in rows}
    for row in rows:
        assert row['question'] and row['expected_behavior'] and row['references']
        assert set(row['checks'])<=set(QUERIES)
        for reference in row['references']:
            if not reference.startswith('sql:'):
                assert (ROOT/reference.split('#')[0]).is_file()


def test_sql_oracle_financial_precision_and_exclusion_of_pending():
    settings=get_settings()
    assert reference_rows(settings.database,'revenue')[0]['valor']==Decimal('493126517.02')
    assert reference_rows(settings.database,'rupture_pending')[0]['valor']==Decimal('4399084.73')
    answer='Receita R$ 493.126.517,02; carteira R$ 155.146.363,54.'
    assert all(r['status']=='passed' for r in check_finances(settings.database,['revenue','pending'],answer))
    assert check_finances(settings.database,['revenue'],'R$ 493.126.517,03')[0]['status']=='failed'
    assert check_finances(settings.database,['revenue'],'R$ 648.272.880,56')[0]['status']=='failed'


def test_evidence_never_contains_unretrieved_reference_or_analysis():
    turn=SimpleNamespace(evidence={'comercial':{'documentos':[{'text':'ACTUALLY RETRIEVED'}],
                          'indisponivel':{'unavailable':True}}},sources=[])
    result=evidence_from_turn(turn)
    assert len(result)==1 and 'ACTUALLY RETRIEVED' in json.dumps(result)
    assert 'golden' not in json.dumps(result)


def judgment(supported=True,relevant=True):
    return Judgment.model_validate({'claims':[{'quote':'Receita 10','supported':supported,
       'evidence_ids':['e1'] if supported else [],'reason':'test'}],
       'relevance_units':[{'quote':'Receita 10','relevant':relevant,'reason':'test'}],'explanation':'test'})


def test_metrics_compute_from_real_verdict_structure_and_invalid_refs_fail():
    evidence=[{'id':'e1','content':'Receita 10'}]
    result=score_judgment(judgment(False,False),'Receita 10',evidence)
    assert result['faithfulness']['score']==0 and result['answer_relevancy']['score']==0
    with pytest.raises(ValueError):
        score_judgment(judgment(),'different answer',evidence)
    invalid=score_judgment(judgment(),'Receita 10',[{'id':'other'}])
    assert invalid['faithfulness']['score'] is None
    assert invalid['answer_relevancy']['score']==1
    result=score_judgment(judgment(False),'Receita 10',[])
    assert result['faithfulness']['score'] is None


def test_failed_judge_never_becomes_zero():
    class Judge:
        def evaluate(self,*args):
            raise ClientError(429,{'error':{'message':'SECRET'}})
    turn=SimpleNamespace(prepare=lambda _:None,stream=lambda:iter(['Receita 10']),
        close=lambda:None,tools=[],answer_mode='gemini',evidence={})
    case={**golden()[0],'checks':[],'expected_tools':[]}
    row=execute_case(case,get_settings(),Judge(),lambda:turn)
    assert row['answer']=='Receita 10'
    assert row['evaluation_failure']['http_code']==429
    assert row['metrics']['faithfulness']['score'] is None
    assert summarize([row])['faithfulness']['mean'] is None
    assert 'SECRET' not in json.dumps(row)


def test_generation_rate_limit_skips_judge_but_preserves_evidence():
    class Judge:
        def evaluate(self,*args):
            pytest.fail('Circuit breaker deve evitar nova chamada')
    tools=[{'tool':'gemini_sintese','status':'failed','category':'api','http':429}]
    turn=SimpleNamespace(prepare=lambda _:None,stream=lambda:iter(['Fallback factual']),
        close=lambda:None,tools=tools,answer_mode='factual',evidence={'comercial':{'total':10}})
    row=execute_case({**golden()[0],'checks':[]},get_settings(),Judge(),lambda:turn)
    assert row['generation_status']=='fallback'
    assert row['evidence'] and row['metrics']['answer_relevancy']['score'] is None


def test_partial_answer_not_evaluated_or_saved():
    def stream():
        yield 'PRIVATE PARTIAL'
        raise ClientError(429,{'error':{'message':'SECRET'}})
    turn=SimpleNamespace(prepare=lambda _:None,stream=stream,close=lambda:None,tools=[],answer_mode='unknown')
    row=execute_case(golden()[0],get_settings(),None,lambda:turn)
    assert row['answer'] is None and row['generation_status']=='failed'
    assert row['metrics']['faithfulness']['score'] is None


def test_limiter_budget_and_disabled_run_no_remote_calls(tmp_path):
    limiter=Limiter(0,1)
    limiter.wait()
    with pytest.raises(CallLimit):
        limiter.wait()
    path,report=run(get_settings(),False,max_cases=2,output=tmp_path)
    assert report['summary']['attempted_questions']==0
    assert report['summary']['faithfulness']['mean'] is None
    assert (path/'results.md').is_file()


def test_judge_sdk_structured_response_and_api_usage(monkeypatch):
    from agro_ai.evaluation.judge import GeminiJudge
    calls=[]
    def generate(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(text=json.dumps({'claims':[{'claim_id':'c001','factual':True,'supported':True,'snippet_ids':['s0001'],'reason':'value 10'}], 'verdicts':[{'unit_id':'u001','relevant':True,'reason':'receita'}], 'explanation':'test'}),usage_metadata=SimpleNamespace(
            prompt_token_count=25,candidates_token_count=10,total_token_count=35))
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:SimpleNamespace(
        models=SimpleNamespace(generate_content=generate),close=lambda:None))
    judge=GeminiJudge(get_settings(),Limiter(0))
    result=judge.evaluate('Qual receita?','Receita 10',[{'id':'e1','content':'Receita 10'}])
    assert result['faithfulness']['score']==1 and result['answer_relevancy']['score']==1
    assert result['usage']=={'input':25,'output':10,'total':35}
    from agro_ai.evaluation.judge import api_judgment_schema,IndexedFullJudgment
    assert result['cost'] is None and calls[0]['config'].response_schema==api_judgment_schema(IndexedFullJudgment)
    schema=json.dumps(api_judgment_schema())
    assert '$ref' not in schema and 'additionalProperties' not in schema
    judge.close()


def test_regional_and_monthly_sql_reconcile_with_total():
    database=get_settings().database
    total=reference_rows(database,'revenue')[0]['valor']
    assert sum(row['valor'] for row in reference_rows(database,'regional'))==total
    assert sum(row['valor'] for row in reference_rows(database,'monthly'))==total
    rows=reference_rows(database,'regional')
    text='\n'.join(f"{row['regiao']}: {row['valor']}; {row['margem_pct']}%" for row in rows)
    assert check_finances(database,['regional'],text)[0]['status']=='passed'
    swapped='\n'.join(f"{row['regiao']}: {rows[(i+1)%len(rows)]['valor']}; {row['margem_pct']}%" for i,row in enumerate(rows))
    assert check_finances(database,['regional'],swapped)[0]['status']=='failed'


def test_shared_ml_flow_captures_only_actual_inference_and_missing_inputs():
    from agro_ai.chatflow import ChatTurn
    from agro_ai.gemini import GeminiGateway
    from agro_ai.rag import DocumentIndex
    for case in [golden()[11],golden()[12],golden()[17]]:
        turn=ChatTurn(get_settings(),GeminiGateway,DocumentIndex)
        turn.prepare([{'role':'user','content':case['question']}])
        answer=''.join(turn.stream())
        assert turn.orchestrator is None and answer
        if case['id']=='G18':
            assert not evidence_from_turn(turn) and turn.tools[0]['status']=='needs_input'
        else:
            assert turn.evidence['ml']['calibrated'] is False
            assert len(turn.evidence['ml']['features'])==7
        turn.close()


def test_full_runner_stops_after_first_429_without_judge_or_remaining_questions(monkeypatch,tmp_path):
    import agro_ai.evaluation.runner as module
    class Judge:
        def __init__(self,*args):
            pass
        def evaluate(self,*args):
            pytest.fail('Não deve consumir cota do juiz após HTTP 429')
        def close(self):
            pass
    class Turn:
        def __init__(self,*args):
            self.tools=[{'tool':'gemini_analise','status':'failed','category':'api','http':429}]
            self.evidence={}
            self.answer_mode='factual'
        def prepare(self,history):
            pass
        def stream(self):
            yield 'Resumo factual indisponível.'
        def close(self):
            pass
    monkeypatch.setattr(module,'GeminiJudge',Judge)
    monkeypatch.setattr(module,'ChatTurn',Turn)
    from dataclasses import replace
    _,report=module.run(replace(get_settings(),api_key='fake'),True,interval=0,max_cases=3,output=tmp_path)
    assert report['summary']['attempted_questions']==1
    assert report['summary']['questions_evaluated']==0
    assert all(row['generation_status']=='not_executed' for row in report['results'][1:])
    assert report['analysis']['quality_conclusion']=='insufficient_judged_answers'
