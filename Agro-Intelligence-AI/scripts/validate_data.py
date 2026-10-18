"""Reconciliação local CSV × DuckDB: python -m scripts.validate_data."""
import hashlib
import json

import duckdb
import pandas as pd

from agro_ai.config import ROOT, get_settings
from agro_ai.synthetic import TABLES
from agro_ai.validation import validate_frames


def main():
    directory = ROOT / 'data/seeds'
    frames = {table: pd.read_csv(directory / f'{table}.csv') for table in TABLES}
    result = validate_frames(frames)
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    for filename, expected in manifest['sha256'].items():
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Hash divergente: {filename}')
    with duckdb.connect(str(get_settings().database), read_only=True) as con:
        counts = {table: con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in TABLES}
        if counts != {table: len(frame) for table, frame in frames.items()}:
            raise ValueError('Contagens CSV/DuckDB divergentes')
        totals = dict(con.execute('SELECT status,SUM(receita_liquida) FROM vendas GROUP BY status LIMIT 3').fetchall())
        if {key: str(value) for key, value in totals.items()} != result['totais_brl']:
            raise ValueError('Totais CSV/DuckDB divergentes')
        states = con.execute('SELECT status,COUNT(*) FROM pedidos GROUP BY status ORDER BY status LIMIT 3').fetchall()
        margin = con.execute("SELECT SUM(margem_valor) FROM vendas WHERE status='faturada' LIMIT 1").fetchone()[0]
    result.update(counts=counts, pedidos_por_status=dict(states), margem_faturada_brl=str(margin),
                  hashes_verificados=True, csv_duckdb_reconciliados=True)
    (directory / 'validation_report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
