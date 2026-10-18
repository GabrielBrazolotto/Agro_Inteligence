"""Carga validada e atômica; consultas fixas agregadas, com resultados limitados."""
import hashlib
from io import BytesIO
from pathlib import Path
import os
import tempfile

import duckdb
import pandas as pd

from agro_ai.config import ROOT
from agro_ai.schema import SCHEMA, SCHEMA_VERSION
from agro_ai.synthetic import TABLES
from agro_ai.validation import validate_frames
from agro_ai.observability import observe

MAX_ROWS = 20


def initialize_database(path: Path, seeds: Path = ROOT / 'data/seeds') -> None:
    path = Path(path)
    payloads = {name: (seeds / f'{name}.csv').read_bytes() for name in TABLES}
    signature = hashlib.sha256(str(SCHEMA_VERSION).encode() + b''.join(payloads.values())).hexdigest()
    if path.exists():
        with duckdb.connect(str(path), read_only=True) as connection:
            has_metadata = connection.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name='dataset_metadata'").fetchone()[0]
            if has_metadata and connection.execute('SELECT signature FROM dataset_metadata').fetchone() == (signature,):
                return
    frames = {name: pd.read_csv(BytesIO(data)) for name, data in payloads.items()}
    validate_frames(frames)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix='carga-') as work:
        staged = Path(work) / 'novo.duckdb'
        with duckdb.connect(str(staged)) as connection:
            connection.begin()
            connection.execute(SCHEMA)
            for table in TABLES:
                connection.register('incoming_frame', frames[table])
                connection.execute(f'INSERT INTO {table} BY NAME SELECT * FROM incoming_frame')
                connection.unregister('incoming_frame')
            connection.execute('INSERT INTO dataset_metadata VALUES (?, ?)', [signature, SCHEMA_VERSION])
            connection.commit()
        os.replace(staged, path)


@observe('duckdb.commercial_snapshot')
def commercial_snapshot(path: Path, limit: int = MAX_ROWS) -> dict:
    limit = max(1, min(int(limit), MAX_ROWS))
    with duckdb.connect(str(path), read_only=True) as connection:
        def records(sql):
            cursor = connection.execute(f'{sql} LIMIT {limit}')
            return [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

        counts = {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in TABLES}
        totals = records("""SELECT MIN(data_venda) AS inicio, MAX(data_venda) AS fim,
            SUM(CASE WHEN status='faturada' THEN receita_liquida ELSE 0 END) AS receita_faturada,
            SUM(CASE WHEN status='faturada' THEN custo_total ELSE 0 END) AS custo_faturado,
            SUM(CASE WHEN status='faturada' THEN margem_valor ELSE 0 END) AS margem_faturada,
            SUM(CASE WHEN status='pendente' THEN receita_liquida ELSE 0 END) AS carteira_pendente,
            SUM(CASE WHEN status='cancelada' THEN receita_liquida ELSE 0 END) AS valor_cancelado
            FROM vendas""")[0]
        return {
            'regra': ('Dados 100% sintéticos. Receita somente de itens faturados; carteira somente pendente. '
                      'Pedidos e linhas são visões da mesma operação: não somar entre si. '
                      'Receita líquida = bruta - descontos; impostos/devoluções não simulados. '
                      'Margem bruta comercial = receita líquida - custo, não lucro líquido. '
                      'Rankings e amostras são limitados; não concluir ausência a partir deles. '
                      'KG, L, toneladas, sacas de 40KG e de 20KG são unidades distintas.'),
            'limite_por_consulta': limit, 'contagens': counts, 'totais': totals,
            'resumo': records("""SELECT status, COUNT(*) AS linhas, COUNT(DISTINCT pedido_id) AS pedidos,
                SUM(receita_liquida) AS valor FROM vendas GROUP BY status ORDER BY status"""),
            'vendas': records("""SELECT v.id, c.nome AS cliente, p.nome AS produto, v.unidade,
                v.data_venda, v.quantidade, v.preco_unitario, v.receita_liquida AS valor, v.status
                FROM vendas v JOIN clientes c ON c.id=v.cliente_id
                JOIN produtos p ON p.id=v.produto_id ORDER BY v.data_venda DESC, v.id"""),
            'catalogo': records('SELECT codigo,nome,categoria,unidade,preco_lista FROM produtos ORDER BY id'),
            'receita_por_cliente': records("""SELECT c.codigo, c.nome AS cliente,
                SUM(v.receita_liquida) AS receita_faturada FROM clientes c
                JOIN vendas v ON v.cliente_id=c.id WHERE v.status='faturada'
                GROUP BY c.codigo,c.nome ORDER BY receita_faturada DESC,c.codigo"""),
            'mensal': records("""SELECT strftime(data_venda,'%Y-%m') AS mes,
                SUM(CASE WHEN status='faturada' THEN receita_liquida ELSE 0 END) AS receita_faturada,
                SUM(CASE WHEN status='pendente' THEN receita_liquida ELSE 0 END) AS carteira_pendente
                FROM vendas GROUP BY mes ORDER BY mes"""),
            'por_regiao': records("""SELECT r.codigo,r.nome AS regiao, COUNT(*) AS linhas,
                SUM(v.receita_liquida) AS receita_faturada,
                SUM(v.custo_total) AS custo_faturado,
                SUM(v.receita_liquida-v.custo_total) AS margem_faturada,
                ROUND(100*SUM(v.receita_liquida-v.custo_total)/NULLIF(SUM(v.receita_liquida),0),4) AS margem_pct
                FROM vendas v
                JOIN regioes r ON r.id=v.regiao_id WHERE v.status='faturada'
                GROUP BY r.codigo,r.nome ORDER BY receita_faturada DESC"""),
            'por_familia': records("""SELECT p.categoria, SUM(v.receita_liquida) AS receita_faturada,
                SUM(v.margem_valor) AS margem, ROUND(100*SUM(v.margem_valor)/SUM(v.receita_liquida),4) AS margem_pct,
                SUM(v.desconto_valor) AS desconto_valor FROM vendas v JOIN produtos p ON p.id=v.produto_id
                WHERE v.status='faturada' GROUP BY p.categoria ORDER BY receita_faturada DESC"""),
            'por_centro': records("""SELECT c.codigo,c.nome AS centro,
                SUM(CASE WHEN v.status='faturada' THEN v.receita_liquida ELSE 0 END) AS receita_faturada,
                SUM(CASE WHEN v.status='pendente' THEN v.receita_liquida ELSE 0 END) AS carteira_pendente
                FROM vendas v JOIN centros c ON c.id=v.centro_id GROUP BY c.codigo,c.nome
                ORDER BY receita_faturada DESC"""),
            'volumes_por_unidade': records("""SELECT unidade, SUM(quantidade) AS quantidade_faturada
                FROM vendas WHERE status='faturada' GROUP BY unidade ORDER BY unidade"""),
            'estoque_resumo': records("""SELECT unidade, COUNT(*) AS pares_produto_centro,
                SUM(disponivel) AS disponivel, SUM(CASE WHEN disponivel=0 THEN 1 ELSE 0 END) AS rupturas,
                SUM(CASE WHEN disponivel>estoque_maximo THEN 1 ELSE 0 END) AS excessos,
                SUM(quantidade*custo_unitario) AS valor_estoque FROM estoque GROUP BY unidade ORDER BY unidade"""),
            'alertas_estoque': records("""SELECT p.codigo AS produto,c.codigo AS centro,e.unidade,
                e.disponivel,e.estoque_minimo,e.estoque_maximo,e.cenario FROM estoque e
                JOIN produtos p ON p.id=e.produto_id JOIN centros c ON c.id=e.centro_id
                WHERE e.disponivel=0 OR e.disponivel>e.estoque_maximo
                QUALIFY ROW_NUMBER() OVER (PARTITION BY e.cenario ORDER BY e.id)<=5
                ORDER BY e.cenario,e.id"""),
            'cenarios_comerciais': records("""SELECT cenario,status,COUNT(*) AS linhas,
                SUM(receita_liquida) AS receita_liquida,SUM(margem_valor) AS margem
                FROM vendas GROUP BY cenario,status ORDER BY cenario,status"""),
            'carteira_por_vencimento': records("""SELECT strftime(vencimento,'%Y-%m') AS mes_vencimento,
                COUNT(DISTINCT pedido_id) AS pedidos,SUM(receita_liquida) AS valor_pendente
                FROM vendas WHERE status='pendente' GROUP BY mes_vencimento ORDER BY mes_vencimento"""),
            'evolucao_precos': records("""SELECT strftime(h.data_referencia,'%Y-%m') AS mes,p.categoria,
                p.unidade,ROUND(AVG(h.preco_lista),2) AS preco_medio,ROUND(AVG(h.custo_unitario),2) AS custo_medio
                FROM historico_precos h JOIN produtos p ON p.id=h.produto_id
                WHERE h.data_referencia IN (DATE '2025-10-01',DATE '2026-09-01')
                GROUP BY mes,p.categoria,p.unidade ORDER BY mes,p.categoria,p.unidade"""),
        }
