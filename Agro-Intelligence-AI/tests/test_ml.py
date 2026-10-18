import hashlib
import json
import zipfile

import numpy as np
import pandas as pd
import pytest

from agro_ai.ml.schema import FEATURES, EXAMPLE, ARTIFACT_DIR
from agro_ai.ml.inference import (parse_features, validate_features, MLInputError,
                                  ml_chat_response, predict_risk, is_prediction_request)
from agro_ai.ml.data import split_data, load_public_data
from agro_ai.ml.training import evaluate


def test_seven_attributes_exactly_and_no_target():
    features = parse_features(EXAMPLE)
    assert list(features) == FEATURES
    assert features == dict(zip(FEATURES,[10.,8.,0.,100.,20.,60.,15.]))
    for value in [dict(features, went_on_backorder=1), {key:value for key,value in features.items() if key!='lead_time'}]:
        with pytest.raises(MLInputError):
            validate_features(value)


@pytest.mark.parametrize('suffix', ['; national_inv=12', '; alvo=1'])
def test_parser_rejects_unknown_or_duplicate_fields(suffix):
    with pytest.raises(MLInputError):
        parse_features(EXAMPLE+suffix)


@pytest.mark.parametrize('field,value', [('lead_time',-1),('min_bank',float('inf')),
                                       ('national_inv',float('nan')),('sales_1_month',True),
                                       ('forecast_3_month',1e12)])
def test_invalid_values_never_reach_model(field,value):
    features = parse_features(EXAMPLE)
    features[field] = value
    with pytest.raises(MLInputError):
        validate_features(features)


def test_group_split_keeps_identical_inputs_together():
    # Dados artificiais somente para teste de partição; não para métricas reportadas.
    x = pd.DataFrame({name:np.repeat(np.arange(100),2) for name in FEATURES}, dtype=float)
    y = pd.Series(np.repeat(np.arange(100)%2,2))
    parts, groups = split_data(x,y)
    assert sorted(np.concatenate(list(parts.values())).tolist()) == list(range(len(x)))
    assert not set(groups[parts['train']]) & set(groups[parts['test']])
    assert not set(groups[parts['train']]) & set(groups[parts['validation']])
    assert not set(groups[parts['validation']]) & set(groups[parts['test']])


def test_public_loader_rejects_changed_archive(tmp_path):
    path = tmp_path/'data.zip'
    path.write_bytes(b'changed')
    with pytest.raises(ValueError,match='Checksum'):
        load_public_data(path)


def test_loader_uses_observed_target_and_discards_footer(tmp_path):
    frame = pd.DataFrame({name:range(20) for name in FEATURES})
    frame['sku'] = range(20)
    frame['went_on_backorder'] = ['Yes','No']*10
    frame = pd.concat([frame,pd.DataFrame([{}])],ignore_index=True)
    path=tmp_path/'test.zip'
    with zipfile.ZipFile(path,'w') as zipped:
        zipped.writestr('Training_Dataset_v2.csv',frame.to_csv(index=False))
    x,y,metadata=load_public_data(path,expected_checksum=hashlib.sha256(path.read_bytes()).hexdigest())
    assert len(x)==20 and y.sum()==10
    assert metadata['excluded_invalid_target_or_sku']==1
    assert list(x)==FEATURES


def test_metrics_calculation_known_example():
    metrics=evaluate([0,0,1,1],[.1,.8,.7,.2],.5)
    assert metrics['confusion_matrix']==[[1,1],[1,1]]
    assert metrics['accuracy']==metrics['precision']==metrics['recall']==metrics['f1']==.5


def test_ml_intent_does_not_capture_commercial_queries():
    assert not is_prediction_request('Quantas posições estão em ruptura?')
    assert not is_prediction_request('Qual a margem por família?')
    assert ml_chat_response('Qual a política de descontos?') is None
    missing=ml_chat_response('Preveja o risco de ruptura do produto PRD-001')
    assert 'Faltam' in missing and 'não' in missing.lower()


@pytest.mark.skipif(not (ARTIFACT_DIR/'model.joblib').exists(),reason='Execute treino público primeiro')
def test_persisted_model_and_reported_metrics_match_real_holdout():
    from agro_ai.config import ROOT
    from agro_ai.ml.inference import _load
    report=json.loads((ARTIFACT_DIR/'metadata.json').read_text(encoding='utf-8'))
    predictions=pd.read_csv(ROOT/'reports/ml/test_predictions.csv')
    recomputed=evaluate(predictions['y_true'],predictions['score'],report['threshold'])
    for key in ['accuracy','precision','recall','f1','roc_auc']:
        assert recomputed[key]==pytest.approx(report['test_metrics'][key])
    assert recomputed['confusion_matrix']==report['test_metrics']['confusion_matrix']
    example=json.loads((ROOT/'reports/ml/example.json').read_text(encoding='utf-8'))
    result=predict_risk(example['features'])
    assert result['score']==pytest.approx(example['score'])
    assert result['class']==example['prediction']


@pytest.mark.skipif(not (ARTIFACT_DIR/'model.joblib').exists(),reason='Execute treino público primeiro')
def test_streamlit_ml_prediction_without_gemini_or_api_key(monkeypatch,tmp_path):
    from streamlit.testing.v1 import AppTest
    from agro_ai.config import ROOT, Settings
    import agro_ai.config
    import agro_ai.gemini
    monkeypatch.setattr(agro_ai.config,'get_settings',lambda:Settings('', 'fake','fake',database=tmp_path/'ui_ml.duckdb'))
    def forbidden(*args,**kwargs):
        pytest.fail('ML local não deve chamar Gemini')
    monkeypatch.setattr(agro_ai.gemini,'GeminiGateway',forbidden)
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    assert not app.chat_input[0].disabled
    app.chat_input[0].set_value(EXAMPLE).run(timeout=30)
    assert not app.exception
    assert 'Previsão ML experimental' in app.session_state['messages'][-1]['content']
    assert 'national_inv' in app.session_state['messages'][-1]['content']
    assert len(app.session_state['messages'])==2
