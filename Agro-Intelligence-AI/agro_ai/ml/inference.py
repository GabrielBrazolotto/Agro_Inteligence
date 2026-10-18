"""Inferência exclusivamente com o pipeline treinado e seu contrato de sete campos."""
import hashlib
import json
import math
import re
import unicodedata
import os
from functools import lru_cache

os.environ.setdefault('LOKY_MAX_CPU_COUNT', '2')

import joblib
import pandas as pd
from threadpoolctl import threadpool_limits

from agro_ai.ml.schema import FEATURES, TARGET, ARTIFACT_DIR, ALIASES, EXAMPLE
from agro_ai.observability import observe,annotate_current


class MLInputError(ValueError):
    pass


def normalize(text):
    return ''.join(char for char in unicodedata.normalize('NFKD',text.lower())
                   if not unicodedata.combining(char))


def is_prediction_request(text):
    text = normalize(text)
    return bool(re.search(r'ruptura|backorder', text) and
                re.search(r'preveja|prever|previsao|prediga|predicao|risco|classifique', text))


def parse_features(text):
    """Parser de campos explícitos em uma pergunta; não é o classificador."""
    text = normalize(text)
    mapping = {alias: feature for feature, aliases in ALIASES.items() for alias in aliases}
    pairs = re.findall(r'\b([a-z][a-z0-9_]*)\s*[:=]\s*([^;\s]+)', text)
    values = {}
    for alias, raw in pairs:
        if alias not in mapping:
            raise MLInputError('Campo não reconhecido. Use somente os sete atributos do exemplo.')
        feature = mapping[alias]
        if feature in values:
            raise MLInputError('Um atributo foi informado mais de uma vez.')
        try:
            value = float(raw.rstrip('.,').replace(',', '.'))
        except ValueError:
            raise MLInputError('Informe números sem separador de milhar, separados por ponto e vírgula.') from None
        values[feature] = value
    return validate_features(values)


def validate_features(values):
    if set(values) != set(FEATURES):
        missing = [key for key in FEATURES if key not in values]
        raise MLInputError('Informe exatamente os sete atributos. Faltam: ' + ', '.join(missing))
    result = {}
    for key in FEATURES:
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value):
            raise MLInputError('Todos os atributos devem ser números finitos.')
        if abs(value) > 1e9 or (key != 'national_inv' and value < 0):
            raise MLInputError('Valores fora do domínio: somente estoque pode ser negativo; limite numérico 1 bilhão.')
        result[key] = float(value)
    return result


@lru_cache(maxsize=2)
def _load(artifact, model_stamp, metadata_stamp):
    metadata_path = artifact.parent / 'metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != metadata['artifact_sha256']:
        raise ValueError('Artefato ML divergente do hash registrado.')
    # Somente artefato produzido localmente pelo treino; nunca baixar pickle pronto.
    bundle = joblib.load(artifact)
    if bundle['features'] != FEATURES or bundle['target'] != TARGET:
        raise ValueError('Contrato do artefato incompatível.')
    if list(bundle['pipeline'].feature_names_in_) != FEATURES:
        raise ValueError('Colunas do pipeline incompatíveis.')
    return bundle, metadata


@observe('ml.predict_backorder')
def predict_risk(values, directory=ARTIFACT_DIR):
    features = validate_features(values)
    artifact = directory / 'model.joblib'
    metadata_path = directory / 'metadata.json'
    bundle, metadata = _load(artifact, artifact.stat().st_mtime_ns, metadata_path.stat().st_mtime_ns)
    with threadpool_limits(limits=2):
        score = float(bundle['pipeline'].predict_proba(pd.DataFrame([features], columns=FEATURES))[0,1])
    ranges = metadata.get('training_ranges', {})
    outside = [key for key,value in features.items() if key in ranges and
               not ranges[key]['min'] <= value <= ranges[key]['max']]
    return {'class': int(score >= bundle['threshold']), 'score': score,
            'threshold': bundle['threshold'], 'features': features,
            'source': bundle['source'], 'calibrated': False, 'outside_training_range': outside}


def ml_chat_response(prompt, *, on_result=None):
    if not is_prediction_request(prompt):
        return None
    try:
        features = parse_features(prompt)
    except MLInputError as error:
        annotate_current(status='needs_input')
        return (str(error) + '\n\nExemplo de pedido de previsão:\n\n`' + EXAMPLE + '`\n\n'
                'Quantidades na mesma unidade do produto; prazo na unidade temporal da fonte. '
                'Não posso obter todos esses atributos do DuckDB atual nem inventar previsões de demanda.')
    try:
        result = predict_risk(features)
    except Exception:
        # Não mostrar exceção bruta, caminhos, entrada do usuário ou conteúdo do artefato.
        from agro_ai.diagnostics import LOGGER
        LOGGER.error('ml_inference_failed')
        annotate_current(status='failed',error_category='local')
        return ('O modelo ML não está disponível ou o artefato é incompatível. '
                'Execute `python -m scripts.train_ml --download` no ambiente do projeto.')
    if on_result is not None:
        on_result(result)
    label = 'Risco sinalizado de backorder' if result['class'] else 'Backorder não sinalizado'
    fields = '\n'.join(f'- `{key}`: {value:g}' for key,value in result['features'].items())
    warning = ('\n\nAtributos fora da faixa observada no treino: ' +
               ', '.join(result['outside_training_range']) + '. Resultado extrapolativo.') if result['outside_training_range'] else ''
    return (f'**Previsão ML experimental: {label}.**\n\n'
            f'Score da classe backorder: **{result["score"]:.4f}**; '
            f'limiar validado: **{result["threshold"]:.2f}**. '
            'O score não é uma probabilidade calibrada nem garantia de ruptura futura.\n\n'
            f'Atributos usados pelo modelo:\n\n{fields}\n\n'
            f'Fonte: [dataset público de backorders]({result["source"]}). '
            'Inferência feita pelo modelo scikit-learn treinado; o Gemini não calcula esta previsão. '
            'Não validado para uma cooperativa agroindustrial brasileira; backorder é um proxy de '
            'indisponibilidade para atender pedidos, não um diagnóstico agronômico ou um alerta operacional certificado.' + warning)
