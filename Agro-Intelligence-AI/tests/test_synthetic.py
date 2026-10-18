import json

import pandas as pd
import pytest

from agro_ai.config import ROOT
from agro_ai.synthetic import generate, write_dataset, TABLES
from agro_ai.validation import validate_frames


@pytest.fixture(scope='module')
def dataset():
    return generate()


def test_reproducible_generation_and_exact_counts(dataset):
    again = generate()
    expected = dict(zip(TABLES, [5, 15, 5000, 1000, 12000, 8000, 20000, 3000]))
    assert {key: len(frame) for key, frame in dataset.items()} == expected
    for table in TABLES:
        pd.testing.assert_frame_equal(dataset[table], again[table])
    report = validate_frames(dataset)
    assert report['checks_count'] >= 90
    assert report['totais_brl']['faturada'] == '493126517.02'


@pytest.mark.parametrize('table,column,value', [
    ('clientes', 'nome', None), ('clientes', 'id', 2),
    ('clientes', 'codigo', 'CLI-000002'), ('clientes', 'regiao_id', 999),
    ('vendas', 'receita_liquida', 1), ('vendas', 'margem_pct', 99),
    ('vendas', 'desconto_pct', 99), ('vendas', 'unidade', 'inexistente'),
    ('vendas', 'data_venda', '2030-01-01'), ('vendas', 'status', 'pendente'),
    ('estoque', 'reservado', 9999999), ('pedidos', 'valor_liquido', 1),
])
def test_validation_rejects_corrupt_data(dataset, table, column, value):
    corrupted = {name: frame.copy(deep=True) if name == table else frame for name, frame in dataset.items()}
    # O primeiro pedido tem estado determinístico; usar status inválido sempre distinto.
    if column == 'status':
        value = 'invalido'
    corrupted[table].loc[0, column] = value
    with pytest.raises(ValueError):
        validate_frames(corrupted)


def test_scenarios_seasonality_and_concentration(dataset):
    sales, stocks = dataset['vendas'], dataset['estoque']
    assert sales['cenario'].value_counts().to_dict() == {
        'normal': 19700, 'desconto_elevado_margem_negativa': 100,
        'margem_alta': 100, 'margem_comprimida': 100}
    assert stocks['cenario'].value_counts().to_dict() == {'normal': 2880, 'ruptura': 60, 'excesso': 60}
    assert (sales.loc[sales['cenario']=='desconto_elevado_margem_negativa', 'margem_valor'] < 0).all()
    assert (sales.loc[sales['cenario']=='margem_comprimida', 'margem_valor'] == 0).all()
    assert (sales.loc[sales['cenario']=='margem_alta', 'margem_pct'] > 39).all()
    months = pd.to_datetime(sales['data_venda']).dt.month
    assert months.isin([7, 8, 9, 10]).mean() > .55
    assert sales['regiao_id'].eq(1).mean() > .40
    assert sales['regiao_id'].eq(5).mean() < .08


def test_writer_backs_up_existing_csv_and_hashes_are_stable(dataset, tmp_path):
    output = tmp_path / 'seeds'
    output.mkdir()
    (output / 'clientes.csv').write_text('original\n', encoding='utf-8')
    backup, first = write_dataset(dataset, output)
    assert (backup / 'clientes.csv').read_text(encoding='utf-8') == 'original\n'
    _, second = write_dataset(dataset, output)
    assert first['sha256'] == second['sha256']
    loaded = {table: pd.read_csv(output / f'{table}.csv') for table in TABLES}
    assert validate_frames(loaded)['totais_brl'] == first['validacao']['totais_brl']
    checked_in = json.loads((ROOT / 'data/seeds/manifest.json').read_text(encoding='utf-8'))
    assert first['sha256'] == checked_in['sha256']
