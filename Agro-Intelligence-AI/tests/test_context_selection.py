from types import SimpleNamespace

from agro_ai.assistant import prepare_context, select_commercial_context
from agro_ai.database import commercial_snapshot, initialize_database


def test_monthly_context_contains_complete_months_but_no_unrelated_rankings(tmp_path):
    path = tmp_path / 'monthly.duckdb'
    initialize_database(path)
    snapshot = commercial_snapshot(path)
    selected = select_commercial_context(snapshot, 'Como o faturamento evoluiu por mês?')
    assert len(selected['mensal']) == 12
    assert selected['totais'] == snapshot['totais']
    assert 'receita_por_cliente' not in selected
    assert 'evolucao_precos' not in selected
    assert 'alertas_estoque' not in selected
    assert sum(item['receita_faturada'] for item in selected['mensal']) == selected['totais']['receita_faturada']


def test_multiple_dimensions_and_general_summary():
    snapshot = {'regra': 'fake', 'totais': {}, 'por_regiao': [1], 'por_familia': [2],
                'vendas': list(range(100)), 'catalogo': list(range(100)),
                'receita_por_cliente': list(range(20)), 'alertas_estoque': list(range(20))}
    selected = select_commercial_context(snapshot, 'Quais regiões têm menor margem?')
    assert selected['por_regiao'] == [1]
    assert selected['por_familia'] == [2]
    overview = select_commercial_context(snapshot, 'Quero um resumo geral')
    assert len(overview['receita_por_cliente']) == 10
    assert len(overview['alertas_estoque']) == 10
    assert 'vendas' not in overview and 'catalogo' not in overview
    assert len(snapshot['receita_por_cliente']) == 20


def test_real_monthly_context_with_all_rag_documents_is_small(tmp_path):
    from agro_ai.config import ROOT
    class Index:
        def search(self, query):
            return [{'source':path.name,'chunk':1,'text':path.read_text(encoding='utf-8')[:900]}
                    for path in sorted((ROOT/'data/documents').glob('*.md'))]
    path = tmp_path / 'context.duckdb'
    initialize_database(path)
    context, sources = prepare_context(SimpleNamespace(database=path), Index(), [
        {'role':'user','content':'Como o faturamento evoluiu por mês?'}])
    assert len(sources) == 3
    assert len(context) < 6500
    assert '2025-10' in context and '2026-09' in context
