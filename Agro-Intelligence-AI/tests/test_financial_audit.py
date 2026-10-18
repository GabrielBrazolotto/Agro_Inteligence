from decimal import Decimal

import duckdb
import pytest

from agro_ai.agents.tools import SystemTools
from agro_ai.agents.orchestrator import AgentOrchestrator
from agro_ai.config import Settings
from agro_ai.database import initialize_database,commercial_snapshot


@pytest.fixture(scope='module')
def settings(tmp_path_factory):
    path=tmp_path_factory.mktemp('audit')/'audit.duckdb'
    initialize_database(path)
    return Settings('','fake','fake',database=path)


def test_rupture_is_not_broad_supply_signal_and_no_duplicate_values(settings):
    tools=SystemTools(settings.database)
    totals=tools.stock_and_orders('ruptura')['totais']
    assert totals['rupturas_observadas']==60
    assert totals['rupturas_com_carteira']==41
    assert totals['insuficiencias_com_saldo']==695
    assert totals['pares_sinalizados']==755
    assert totals['carteira_em_ruptura']==Decimal('4399084.73')
    assert totals['carteira_em_insuficiencia_com_saldo']==Decimal('69752075.66')
    assert totals['carteira_nos_pares_sinalizados']==totals['carteira_em_ruptura']+totals['carteira_em_insuficiencia_com_saldo']
    with duckdb.connect(str(settings.database),read_only=True) as con:
        assert con.execute('SELECT COUNT(*)=COUNT(DISTINCT (produto_id,centro_id)) FROM estoque').fetchone()[0]
        independent=con.execute("""SELECT SUM(v.receita_liquida) FROM vendas v
          WHERE v.status='pendente' AND (v.produto_id,v.centro_id) IN
          (SELECT produto_id,centro_id FROM estoque WHERE disponivel=0)""").fetchone()[0]
    assert independent==totals['carteira_em_ruptura']
    impact=tools.rupture_impact()['totais']
    assert impact['linhas_pendentes']==103 and impact['pedidos_distintos']==101
    assert impact['custo_carteira']==Decimal('3506069.23')
    assert impact['margem_carteira']==Decimal('893015.50')
    assert impact['carteira_pendente']-impact['custo_carteira']==impact['margem_carteira']
    assert all(row['disponivel']==0 for row in tools.stock_and_orders('ruptura')['prioridades_amostra'])


def test_regional_weighted_margins_reconcile_with_invoiced_items(settings):
    snapshot=commercial_snapshot(settings.database)
    regions=snapshot['por_regiao']
    assert len(regions)==5
    assert [row['margem_pct'] for row in regions]==pytest.approx([20.2163,20.6741,20.2254,19.6242,20.2592])
    assert sum(row['receita_faturada'] for row in regions)==snapshot['totais']['receita_faturada']
    assert sum(row['custo_faturado'] for row in regions)==snapshot['totais']['custo_faturado']
    assert sum(row['margem_faturada'] for row in regions)==snapshot['totais']['margem_faturada']
    for row in regions:
        assert row['margem_faturada']==row['receita_faturada']-row['custo_faturado']
        assert row['margem_pct']==pytest.approx(round(float(100*row['margem_faturada']/row['receita_faturada']),4))
    with duckdb.connect(str(settings.database),read_only=True) as con:
        simple_average=con.execute("SELECT AVG(margem_pct) FROM vendas WHERE status='faturada' AND regiao_id=1").fetchone()[0]
    assert abs(simple_average-regions[0]['margem_pct'])>.01


def test_compound_strict_impact_and_regional_query_never_trigger_ml(settings,monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('Não pode inferir ML sem sete entradas explícitas')
    monkeypatch.setattr('agro_ai.agents.tools.predict_risk',forbidden)
    runner=AgentOrchestrator(settings,use_llm=False)
    question='Quais rupturas de estoque afetam pedidos pendentes e qual o impacto comercial nas margens?'
    history=[{'role':'user','content':question}]
    prepared=runner.prepare(history)
    assert prepared.agents==['estoque','comercial']
    assert any(x['tool']=='duckdb_impacto_rupturas_total' and x.get('depends_on') for x in prepared.state.trace)
    assert not any(x['tool']=='scikit_learn_backorder' for x in prepared.state.trace)
    assert '4.399.084,73' in ''.join(runner.stream_answer(prepared,history))
    regional=SystemTools(settings.database).commercial('Quais regiões possuem maior faturamento e qual é a margem média de cada uma?')
    assert len(regional['por_regiao'])==5
    assert all('margem_pct' in row and 'custo_faturado' in row for row in regional['por_regiao'])
