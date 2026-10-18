from decimal import Decimal

import duckdb
import pytest

from agro_ai.database import commercial_snapshot, initialize_database


def test_seed_is_idempotent_and_revenue_excludes_other_statuses(tmp_path):
    path = tmp_path / 'test.duckdb'
    initialize_database(path)
    initialize_database(path)
    snapshot = commercial_snapshot(path)
    assert len(snapshot['vendas']) == 20
    assert snapshot['contagens']['vendas'] == 20000
    assert snapshot['contagens']['pedidos'] == 8000
    totals = {row['status']: row['valor'] for row in snapshot['resumo']}
    assert totals == {'faturada': Decimal('493126517.02'),
                      'pendente': Decimal('155146363.54'), 'cancelada': Decimal('34784595.17')}
    assert totals['faturada'] == snapshot['totais']['receita_faturada']
    with duckdb.connect(str(path)) as connection:
        assert connection.execute("SELECT SUM(valor_liquido) FROM pedidos WHERE status='faturado'").fetchone()[0] == totals['faturada']
        with pytest.raises(duckdb.ConstraintException):
            connection.execute('UPDATE vendas SET cliente_id=999999 WHERE id=1')


def test_snapshot_limits_and_complete_aggregations(tmp_path):
    import json
    path = tmp_path / 'bounded.duckdb'
    initialize_database(path)
    snapshot = commercial_snapshot(path, limit=999999)
    assert all(len(value) <= 20 for value in snapshot.values() if isinstance(value, list))
    assert len(snapshot['mensal']) == 12
    assert len(snapshot['por_regiao']) == 5
    assert len(snapshot['por_centro']) == 15
    assert sum(row['receita_faturada'] for row in snapshot['mensal']) == snapshot['totais']['receita_faturada']
    assert sum(row['receita_faturada'] for row in snapshot['por_regiao']) == snapshot['totais']['receita_faturada']
    assert sum(row['receita_faturada'] for row in snapshot['por_familia']) == snapshot['totais']['receita_faturada']
    assert sum(row['rupturas'] for row in snapshot['estoque_resumo']) == 60
    assert sum(row['excessos'] for row in snapshot['estoque_resumo']) == 60
    assert len(json.dumps(snapshot, default=str)) < 35000


def test_invalid_import_preserves_existing_database(tmp_path):
    import shutil
    from agro_ai.config import ROOT
    path = tmp_path / 'atomic.duckdb'
    initialize_database(path)
    previous = path.read_bytes()
    seeds = tmp_path / 'seeds'
    shutil.copytree(ROOT / 'data/seeds', seeds)
    products = seeds / 'produtos.csv'
    import pandas as pd
    frame = pd.read_csv(products)
    frame.loc[0, 'preco_lista'] = -1
    frame.to_csv(products, index=False)
    with pytest.raises(ValueError):
        initialize_database(path, seeds)
    assert path.read_bytes() == previous
