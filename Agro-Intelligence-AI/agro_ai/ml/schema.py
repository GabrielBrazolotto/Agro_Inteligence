"""Contrato único de treinamento e inferência. Não mapear dados locais por suposição."""
from pathlib import Path
from agro_ai.config import ROOT

FEATURES = ['national_inv', 'lead_time', 'in_transit_qty', 'forecast_3_month',
            'sales_1_month', 'sales_3_month', 'min_bank']
TARGET = 'went_on_backorder'
ARTIFACT_DIR = ROOT / 'models/backorder'
RAW_DIR = ROOT / 'data/ml/raw'
SEED = 20261015
SOURCE_URL = 'https://raw.githubusercontent.com/akhiilkasare/Back-Order-Prediction-iNeuron/3bf0817ebb1a20e675ff02244660507e59f180f2/Dataset.zip'
SOURCE_PAGE = 'https://github.com/akhiilkasare/Back-Order-Prediction-iNeuron/tree/3bf0817ebb1a20e675ff02244660507e59f180f2'
SOURCE_SHA256 = '70ed395f05bcac971cd610dfb5c31832548e5fc0804b8aa58b131c99c9dc7c5f'
ALIASES = {
    'national_inv': ('national_inv', 'estoque'),
    'lead_time': ('lead_time', 'prazo'),
    'in_transit_qty': ('in_transit_qty', 'transito'),
    'forecast_3_month': ('forecast_3_month', 'previsao_3m'),
    'sales_1_month': ('sales_1_month', 'vendas_1m'),
    'sales_3_month': ('sales_3_month', 'vendas_3m'),
    'min_bank': ('min_bank', 'estoque_minimo'),
}
EXAMPLE = ('Preveja o risco de backorder com estoque=10; prazo=8; transito=0; '
           'previsao_3m=100; vendas_1m=20; vendas_3m=60; estoque_minimo=15')
