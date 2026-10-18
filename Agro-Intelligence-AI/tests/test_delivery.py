from copy import deepcopy
import math
import pytest
from scripts.prepare_etapa2_delivery import aggregate,collect


@pytest.mark.parametrize('value,status',[(None,'invalid_judgment'),(0,'not_executed'),
    (math.nan,'evaluated'),(math.inf,'evaluated'),(1.01,'evaluated')])
def test_delivery_rejects_invalid_or_unexecuted_metric(value,status):
    rows=[{'id':'unit','metrics':{'faithfulness':{'status':status,'score':value},
        'answer_relevancy':{'status':'evaluated','score':1}}}]
    with pytest.raises(ValueError): aggregate(rows)


def test_delivery_threshold_is_strict_and_preserves_low_scores():
    rows=[{'id':identifier,'metrics':{'faithfulness':{'status':'evaluated','score':1},
        'answer_relevancy':{'status':'evaluated','score':score}}}
        for identifier,score in [('boundary',.8),('below',.2)]]
    before=deepcopy(rows)
    result=aggregate(rows)
    assert result['answer_relevancy']['below_threshold']==['below']
    assert result['answer_relevancy']['mean']==.5 and rows==before


def test_delivery_uses_fifteen_real_cached_cases_without_sdk(monkeypatch):
    monkeypatch.setattr('agro_ai.evaluation.judge.genai.Client',lambda **kw:pytest.fail('no remote calls'))
    evidence=collect()
    assert len(evidence['cases'])==15 and evidence['new_api_calls']==0
    assert all(row['metrics'][name]['status']=='evaluated' for row in evidence['cases']
        for name in ('faithfulness','answer_relevancy'))
    assert evidence['summary']['answer_relevancy']['below_threshold']==['G01','G04','G11']
    checks=[c for row in evidence['cases'] for c in row['deterministic_current_duckdb']]
    assert len(checks)==8 and all(c['status']=='passed' for c in checks)
    assert evidence['cases'][-1]['metrics']['faithfulness']['score']==14/15
