"""Leitura de CSV público em zip sem extrair/executar arquivos externos."""
import hashlib
import zipfile

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from agro_ai.ml.schema import FEATURES, TARGET, SEED, SOURCE_SHA256


def load_public_data(archive, max_rows=200000, expected_checksum=SOURCE_SHA256):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != expected_checksum:
        raise ValueError('Checksum da fonte pública divergente.')
    with zipfile.ZipFile(archive) as zipped:
        candidates = [name for name in zipped.namelist()
                      if name.lower().endswith('.csv') and 'training' in name.lower()]
        if len(candidates) != 1:
            raise ValueError('Esperado um único CSV Training na fonte pública.')
        member = candidates[0]
        with zipped.open(member) as file:
            frame = pd.read_csv(file, usecols=['sku', *FEATURES, TARGET], low_memory=False)
    source_rows = len(frame)
    # A fonte contém linha final de contagem/rodapé. Nunca criar um alvo para ela.
    valid = frame[TARGET].isin(['Yes', 'No']) & frame['sku'].notna()
    frame = frame.loc[valid].copy()
    if frame['sku'].duplicated().any():
        raise ValueError('SKU repetido: revisar agrupamento antes de treinar.')
    eligible_rows = len(frame)
    if max_rows and len(frame) > max_rows:
        # Amostra uniforme, não balanceada pelo alvo. A prevalência não é forçada.
        frame = frame.sample(n=max_rows, random_state=SEED)
    frame = frame.reset_index(drop=True)
    x = frame[FEATURES].apply(pd.to_numeric, errors='raise').astype(float)
    x['lead_time'] = x['lead_time'].replace(-99, np.nan)
    if np.isinf(x.to_numpy()).any():
        raise ValueError('Atributo infinito no dataset.')
    y = frame[TARGET].map({'No': 0, 'Yes': 1}).astype(int)
    if y.nunique() != 2:
        raise ValueError('O dataset precisa conter as duas classes.')
    return x, y, {'member': member, 'source_rows': source_rows,
                  'eligible_rows': eligible_rows, 'used_rows': len(frame),
                  'excluded_invalid_target_or_sku': source_rows-eligible_rows,
                  'archive_sha256': digest,
                  'sampling': 'uniform_without_replacement_not_balanced',
                  'sku_unique': True, 'positive_rows': int(y.sum())}


def split_data(x, y):
    # Mesmo vetor de entrada não pode ocorrer em treino/validação/teste diferentes.
    # Inclui duplicatas com alvos conflitantes: continuam no mesmo grupo.
    groups = pd.util.hash_pandas_object(x[FEATURES], index=False).to_numpy()
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    development, test = next(outer.split(x, y, groups))
    inner = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED+1)
    train_local, validation_local = next(inner.split(
        x.iloc[development], y.iloc[development], groups[development]))
    parts = {'train': development[train_local], 'validation': development[validation_local], 'test': test}
    group_sets = [set(groups[parts[name]]) for name in parts]
    if any(group_sets[i] & group_sets[j] for i in range(3) for j in range(i+1,3)):
        raise ValueError('Vazamento entre partições.')
    return parts, groups
