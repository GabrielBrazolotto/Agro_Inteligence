"""Treino real, threshold só na validação e avaliação única no teste reservado."""
import hashlib
import json
import platform
import os
from importlib.metadata import version

from agro_ai.config import ROOT
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / 'data/runtime/matplotlib'))
os.environ.setdefault('LOKY_MAX_CPU_COUNT', '2')

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (accuracy_score, precision_score, recall_score, f1_score,
                             fbeta_score, roc_auc_score, average_precision_score,
                             confusion_matrix, ConfusionMatrixDisplay)
from sklearn.pipeline import Pipeline
from threadpoolctl import threadpool_limits

from agro_ai.ml.data import load_public_data, split_data
from agro_ai.ml.schema import FEATURES, TARGET, SEED, SOURCE_PAGE, SOURCE_URL, ARTIFACT_DIR


def evaluate(y, scores, threshold):
    predicted = (np.asarray(scores) >= threshold).astype(int)
    return {'accuracy': float(accuracy_score(y, predicted)),
            'precision': float(precision_score(y, predicted, zero_division=0)),
            'recall': float(recall_score(y, predicted, zero_division=0)),
            'f1': float(f1_score(y, predicted, zero_division=0)),
            'roc_auc': float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
            'average_precision': float(average_precision_score(y, scores)),
            'confusion_matrix': confusion_matrix(y, predicted, labels=[0,1]).tolist()}


def train(archive, output=ARTIFACT_DIR, reports=None, max_rows=200000):
    reports = reports or ROOT / 'reports/ml'
    output.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    x, y, source = load_public_data(archive, max_rows)
    parts, groups = split_data(x, y)
    if any(y.iloc[index].nunique() != 2 for index in parts.values()):
        raise ValueError('Cada partição precisa ter as duas classes.')
    pipeline = Pipeline([('classifier', HistGradientBoostingClassifier(
        max_iter=160, max_leaf_nodes=15, learning_rate=.07, min_samples_leaf=30,
        l2_regularization=1., class_weight='balanced', early_stopping=False,
        random_state=SEED))])
    training, validation, test = [parts[name] for name in ('train','validation','test')]
    with threadpool_limits(limits=2):
        pipeline.fit(x.iloc[training], y.iloc[training])
        val_scores = pipeline.predict_proba(x.iloc[validation])[:,1]
        thresholds = np.linspace(.05, .95, 91)
        f2 = [fbeta_score(y.iloc[validation], val_scores >= value, beta=2, zero_division=0)
              for value in thresholds]
        threshold = float(thresholds[int(np.argmax(f2))])
        # O teste não participa da escolha de modelo, pesos ou threshold.
        test_scores = pipeline.predict_proba(x.iloc[test])[:,1]
    baseline = DummyClassifier(strategy='most_frequent').fit(x.iloc[training], y.iloc[training])
    metrics = evaluate(y.iloc[test], test_scores, threshold)
    baseline_metrics = evaluate(y.iloc[test], baseline.predict_proba(x.iloc[test])[:,1], .5)
    splits = {name: {'rows': len(index), 'positives': int(y.iloc[index].sum()),
                     'positive_rate': float(y.iloc[index].mean()),
                     'groups': len(set(groups[index]))} for name,index in parts.items()}
    bundle = {'pipeline': pipeline, 'features': FEATURES, 'target': TARGET,
              'threshold': threshold, 'schema_version': 1, 'source': SOURCE_PAGE}
    artifact = output / 'model.joblib'
    joblib.dump(bundle, artifact, compress=3)
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report = {'dataset': 'Can You Predict Product Backorders? (public mirror)',
              'source_page': SOURCE_PAGE, 'source_url': SOURCE_URL, **source,
              'target': TARGET, 'positive_class': 'Yes', 'features': FEATURES,
              'excluded_features': ['sku', 'local_bo_qty', 'potential_issue', 'pieces_past_due',
                                    'deck_risk', 'oe_constraint', 'ppap_risk', 'stop_auto_buy', 'rev_stop'],
              'seed': SEED, 'splits': splits, 'split_strategy': 'two_stage_stratified_group_kfold_on_feature_vector',
              'temporal_validation': False, 'group_overlap': 0,
              'threshold': threshold, 'threshold_selection': 'max_validation_F2_on_fixed_grid_0.05_0.95',
              'validation_f2': float(max(f2)), 'test_metrics': metrics,
              'baseline_test_metrics': baseline_metrics,
              'artifact_sha256': artifact_hash, 'probabilities_calibrated': False,
              'training_ranges': {key: {'min':float(x.iloc[training][key].min()),
                                        'max':float(x.iloc[training][key].max())} for key in FEATURES},
              'versions': {name: version(name) for name in ['scikit-learn','numpy','pandas','joblib']},
              'python': platform.python_version(),
              'limitations': ['Sem datas para validação temporal ou garantia de horizonte futuro.',
                              'Amostra de dataset público de cadeia de suprimentos; não agro brasileiro.',
                              'Scores de classificador com pesos de classe não são probabilidades calibradas.',
                              'Disponibilidade dos atributos e rótulos na origem não foi auditada no ERP.',
                              'Não foi treinado nem validado com os dados comerciais sintéticos locais.']}
    (output/'metadata.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    (reports/'metrics.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    assignments = pd.DataFrame({'sample_row': np.arange(len(x)), 'feature_group': groups})
    assignments['partition'] = ''
    for name,index in parts.items():
        assignments.loc[index,'partition'] = name
    assignments.to_csv(reports/'split_assignments.csv', index=False)
    pd.DataFrame({'sample_row': test, 'y_true': y.iloc[test].to_numpy(),
                  'score': test_scores, 'y_pred': (test_scores>=threshold).astype(int)}).to_csv(
                      reports/'test_predictions.csv', index=False)
    # Exemplo com atributos realmente presentes na fonte pública, sem alvo na entrada.
    complete = np.flatnonzero(x.iloc[test].notna().all(axis=1).to_numpy())
    example_position = int(complete[0])
    example_index = int(test[example_position])
    example = {'features': {key: (None if pd.isna(value) else float(value))
                            for key,value in x.iloc[example_index].items()},
               'score': float(test_scores[example_position]), 'prediction': int(test_scores[example_position]>=threshold),
               'partition': 'test', 'note': 'Exemplo de inferência, não avaliação adicional.'}
    (reports/'example.json').write_text(json.dumps(example,indent=2,ensure_ascii=False),encoding='utf-8')
    display = ConfusionMatrixDisplay(np.array(metrics['confusion_matrix']), display_labels=['Sem backorder','Backorder'])
    display.plot(cmap='Blues', values_format='d')
    plt.title('Teste reservado — dataset público de backorder')
    plt.tight_layout()
    plt.savefig(reports/'confusion_matrix.png', dpi=160)
    plt.close()
    return report
