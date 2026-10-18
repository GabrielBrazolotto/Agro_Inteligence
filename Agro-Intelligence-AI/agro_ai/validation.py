"""Validações de integridade e reconciliação financeira dos dados sintéticos."""
import numpy as np
import pandas as pd

from agro_ai.synthetic import TABLES, START, END


def validate_frames(frames: dict[str, pd.DataFrame]) -> dict:
    checks = []
    def require(condition, label):
        if not bool(condition):
            raise ValueError(f'Dados inválidos: {label}')
        checks.append(label)

    def cents(series):
        return (series.astype(float) * 100).round().astype('int64')

    require(set(frames) == set(TABLES), 'tabelas_esperadas')
    for name, frame in frames.items():
        require(not frame.empty, f'{name}_nao_vazia')
        require(not frame.isna().any().any(), f'{name}_sem_nulos')
        require(not frame.select_dtypes(include=['str', 'object']).apply(
            lambda col: col.astype(str).str.strip().eq('').any()).any(), f'{name}_sem_texto_vazio')
        require(frame['id'].is_unique and (frame['id'] > 0).all(), f'{name}_chave_primaria')
        if 'codigo' in frame:
            require(frame['codigo'].is_unique, f'{name}_codigo_unico')
    links = [('centros', 'regiao_id', 'regioes'), ('clientes', 'regiao_id', 'regioes'),
             ('pedidos', 'cliente_id', 'clientes'), ('pedidos', 'centro_id', 'centros'),
             ('pedidos', 'regiao_id', 'regioes'), ('vendas', 'pedido_id', 'pedidos'),
             ('vendas', 'cliente_id', 'clientes'), ('vendas', 'produto_id', 'produtos'),
             ('vendas', 'centro_id', 'centros'), ('vendas', 'regiao_id', 'regioes'),
             ('estoque', 'produto_id', 'produtos'), ('estoque', 'centro_id', 'centros'),
             ('historico_precos', 'produto_id', 'produtos')]
    for child, key, parent in links:
        require(frames[child][key].isin(frames[parent]['id']).all(), f'fk_{child}_{key}')
    p, v, o, e, h = [frames[x] for x in ('produtos', 'vendas', 'pedidos', 'estoque', 'historico_precos')]
    require(not e.duplicated(['produto_id', 'centro_id']).any(), 'estoque_par_unico')
    require(not h.duplicated(['produto_id', 'data_referencia']).any(), 'preco_mensal_unico')
    for table, columns in [(p, ['preco_lista', 'custo_unitario']),
                           (h, ['preco_lista', 'custo_unitario']),
                           (v, ['quantidade', 'preco_lista', 'preco_unitario', 'custo_unitario'])]:
        require((table[columns] > 0).all().all() and np.isfinite(table[columns]).all().all(),
                f'positivos_{len(checks)}')
    require(p['unidade'].isin(['KG', 'L', 'tonelada', 'saca_40KG', 'saca_20KG']).all(), 'unidades_permitidas')
    for name, frame in [('vendas', v), ('estoque', e)]:
        units = frame['produto_id'].map(p.set_index('id')['unidade'])
        require(frame['unidade'].eq(units).all(), f'{name}_unidade_do_produto')
    require((v['quantidade'] % 1 == 0).all(), 'quantidades_inteiras')
    require(v['desconto_pct'].between(0, 18).all(), 'descontos_limites')
    expected_unit = (cents(v['preco_lista']) * (10000 - (v['desconto_pct']*100).round().astype('int64')) + 5000) // 10000
    require(cents(v['preco_unitario']).eq(expected_unit).all(), 'preco_descontado_half_up')
    for result, left, right in [('receita_bruta', 'quantidade', 'preco_lista'),
                                ('receita_liquida', 'quantidade', 'preco_unitario'),
                                ('custo_total', 'quantidade', 'custo_unitario')]:
        require(cents(v[result]).eq(v[left] * cents(v[right])).all(), f'calculo_{result}')
    require(cents(v['desconto_valor']).eq(cents(v['receita_bruta'])-cents(v['receita_liquida'])).all(), 'calculo_desconto')
    require(cents(v['margem_valor']).eq(cents(v['receita_liquida'])-cents(v['custo_total'])).all(), 'calculo_margem')
    require(np.allclose(v['margem_pct'], 100*v['margem_valor']/v['receita_liquida'], atol=.000051, rtol=0), 'percentual_margem')
    require(o['status'].isin(['faturado', 'pendente', 'cancelado']).all(), 'status_pedidos')
    parent = o.set_index('id')
    for key in ('cliente_id', 'centro_id', 'regiao_id', 'vencimento'):
        require(v[key].eq(v['pedido_id'].map(parent[key])).all(), f'item_pedido_{key}')
    require(v['data_venda'].eq(v['pedido_id'].map(parent['data_pedido'])).all(), 'item_data_pedido')
    statuses = o.set_index('id')['status'].map({'faturado': 'faturada', 'pendente': 'pendente', 'cancelado': 'cancelada'})
    require(v['status'].eq(v['pedido_id'].map(statuses)).all(), 'status_linha_pedido')
    require(set(v['pedido_id']) == set(o['id']), 'todos_pedidos_com_itens')
    totals = cents(v['receita_liquida']).groupby(v['pedido_id']).sum()
    require(cents(o['valor_liquido']).eq(o['id'].map(totals)).all(), 'reconciliacao_pedidos_itens')
    for child, parent_name, key in [('pedidos', 'clientes', 'cliente_id'), ('pedidos', 'centros', 'centro_id')]:
        mapped = frames[child][key].map(frames[parent_name].set_index('id')['regiao_id'])
        require(frames[child]['regiao_id'].eq(mapped).all(), f'regiao_{child}_{parent_name}')
    for name, column in [('vendas', 'data_venda'), ('pedidos', 'data_pedido'),
                          ('historico_precos', 'data_referencia'), ('estoque', 'data_referencia')]:
        dates = pd.to_datetime(frames[name][column], errors='raise')
        require(dates.between(START, END).all(), f'periodo_{name}')
    require(pd.to_datetime(v['data_venda']).dt.to_period('M').nunique() == 12, 'doze_meses')
    require((pd.to_datetime(v['vencimento']) > pd.to_datetime(v['data_venda'])).all(), 'vencimentos_posteriores')
    require((h.groupby('produto_id').size() == 12).all(), 'historico_doze_precos_produto')
    lookup = h.assign(mes=h['data_referencia'].str[:7]).set_index(['produto_id', 'mes'])['preco_lista']
    expected_prices = [lookup.loc[(pid, date[:7])] for pid, date in zip(v['produto_id'], v['data_venda'])]
    require(cents(v['preco_lista']).eq(cents(pd.Series(expected_prices))).all(), 'preco_historico_venda')
    pairs = set(zip(e['produto_id'], e['centro_id']))
    require(all(pair in pairs for pair in zip(v['produto_id'], v['centro_id'])), 'itens_com_par_estoque')
    require((e[['quantidade', 'reservado', 'disponivel', 'estoque_minimo']] >= 0).all().all(), 'estoque_nao_negativo')
    require(e['disponivel'].eq(e['quantidade']-e['reservado']).all(), 'estoque_disponivel')
    require((e['estoque_maximo'] > e['estoque_minimo']).all() and (e['custo_unitario'] > 0).all(), 'estoque_limites_custo')
    require((e.loc[e['cenario']=='ruptura', 'disponivel'] == 0).all(), 'cenario_ruptura')
    require((e.loc[e['cenario']=='excesso', 'disponivel'] > e.loc[e['cenario']=='excesso', 'estoque_maximo']).all(), 'cenario_excesso')
    financial = {}
    for status in ('faturada', 'pendente', 'cancelada'):
        value = int(cents(v.loc[v['status']==status, 'receita_liquida']).sum())
        financial[status] = f'{value // 100}.{value % 100:02}'
    return {'checks': checks, 'checks_count': len(checks), 'totais_brl': financial}
