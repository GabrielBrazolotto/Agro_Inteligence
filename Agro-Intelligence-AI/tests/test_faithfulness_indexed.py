from copy import deepcopy
import json
import pytest
from pydantic import ValidationError
from agro_ai.evaluation.faithfulness import (
    IndexedFaithfulness, claim_units, evidence_snippets, score_indexed_faithfulness)
from agro_ai.evaluation.judge import Claim, score_faithfulness


ANSWER='**60 posições** em ruptura.\nTítulo'
EVIDENCE=[{'id':'e1','origin':'duckdb','content':{'total':60}}]


def verdict():
    return {'claims':[
        {'claim_id':'c001','factual':True,'supported':True,'snippet_ids':['s0001'],'reason':'total=60 sustenta a contagem'},
        {'claim_id':'c002','factual':False,'supported':False,'snippet_ids':[],'reason':'Título sem fato'}],
        'explanation':'Comparação dos fatos com os campos recuperados'}


def test_valid_exact_resolution_and_unsupported_is_zero():
    result=score_indexed_faithfulness(IndexedFaithfulness(**verdict()),ANSWER,EVIDENCE)
    assert result['faithfulness']['score']==1
    assert result['faithfulness_judgment']['claims'][0]['quote']=='**60 posições** em ruptura.'
    assert result['faithfulness_judgment']['claims'][0]['evidence'][0]['value']==60
    for unit in claim_units(ANSWER):
        assert ANSWER[unit['start']:unit['end']]==unit['text']
    value=verdict();value['claims'][0].update(supported=False,snippet_ids=[],reason='Não há suporte')
    assert score_indexed_faithfulness(IndexedFaithfulness(**value),ANSWER,[])['faithfulness']['score']==0


@pytest.mark.parametrize('mutation',[
    lambda v:v['claims'].pop(),
    lambda v:v['claims'].append(deepcopy(v['claims'][0])),
    lambda v:v['claims'][0].update(claim_id='c999'),
    lambda v:v['claims'][0].update(snippet_ids=['s9999']),
    lambda v:v['claims'][0].update(snippet_ids=['s0001','s0001']),
    lambda v:v['claims'][0].update(snippet_ids=[]),
    lambda v:v['claims'][0].update(reason='   '),
    lambda v:v.update(explanation='   '),
    lambda v:v['claims'][1].update(supported=True),
])
def test_invalid_judgment_never_gets_score(mutation):
    value=verdict();mutation(value)
    result=score_indexed_faithfulness(IndexedFaithfulness(**value),ANSWER,EVIDENCE)
    assert result['faithfulness']['status']=='invalid_judgment'
    assert result['faithfulness']['score'] is None


def test_paraphrased_quotes_not_part_of_wire_protocol_and_strict_bool():
    for update in [{'quote':'Existem sessenta rupturas'}, {'supported':'true'}]:
        value=verdict();value['claims'][0].update(update)
        with pytest.raises(ValidationError):
            IndexedFaithfulness(**value)


def test_evidence_pointer_preserves_actual_content_and_unique_roots():
    evidence=[{'id':'e1','content':{'a/b':[60,'literal *text*']}}]
    snippets=evidence_snippets(evidence)
    assert snippets[0]['path']=='/content/a~1b/0'
    assert snippets[1]['value']=='literal *text*'
    with pytest.raises(ValueError):
        evidence_snippets(evidence+evidence)


def test_real_g02_failures_reproduced_without_rescoring_history():
    from agro_ai.config import ROOT
    for name,count in [('20261017T142045Z-batch-d6b957',6),('20261017T142342Z-batch-6e8c73',1)]:
        report=json.loads((ROOT/'reports/evaluation'/name/'results.json').read_text(encoding='utf-8'))
        row=next(r for r in report['results'] if r['id']=='G02')
        claims=[Claim(**c) for c in row['current_assessment']['faithfulness_judgment']['claims']]
        assert score_faithfulness(claims,row['answer'],row['evidence'])['reason']=='invalid_quote'
        def plain(t):
            return ' '.join(t.replace('**','').replace('`','').split())
        rejected=[c.quote for c in claims if plain(c.quote) not in plain(row['answer'])]
        assert len(rejected)==count
        if count==1:
            assert rejected==['insuficiência com saldo positivo (695 posições']
            assert '*insuficiência com saldo positivo* (695 posições' in row['answer']
        assert row['metrics']['answer_relevancy']['score']==1
        assert row['metrics']['faithfulness']['score'] is None


def test_faithfulness_only_wire_uses_ids_no_free_quotes(monkeypatch):
    from types import SimpleNamespace
    from agro_ai.evaluation.judge import GeminiJudge
    from agro_ai.config import get_settings
    requests=[]
    def generate(**kwargs):
        payload=json.loads(kwargs['contents']);requests.append(payload)
        assert 'answer_units' not in payload and 'answer' not in payload
        assert payload['claim_units'][0]['text']=='**60 posições** em ruptura.'
        assert payload['evidence_snippets'][0]['value']==60
        return SimpleNamespace(text=json.dumps(verdict()),usage_metadata=None)
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kwargs:
        SimpleNamespace(models=SimpleNamespace(generate_content=generate),close=lambda:None))
    judge=GeminiJudge(get_settings(),SimpleNamespace(wait=lambda:None))
    result=judge.evaluate_pending('Quantas?',ANSWER,EVIDENCE,['faithfulness'])
    assert result['faithfulness']['score']==1
    assert 'answer_relevancy' not in result and len(requests)==1
    judge.close()
