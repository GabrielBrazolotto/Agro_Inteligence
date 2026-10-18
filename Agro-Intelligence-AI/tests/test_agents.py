from decimal import Decimal
from types import SimpleNamespace

import duckdb
import pytest
from google.genai.errors import ServerError

from agro_ai.config import ROOT,Settings
from agro_ai.database import initialize_database
from agro_ai.agents.tools import SystemTools
from agro_ai.agents.orchestrator import AgentOrchestrator,plan_agents
from scripts.validate_agents import TASKS


@pytest.fixture(scope='module')
def settings(tmp_path_factory):
    path=tmp_path_factory.mktemp('agents')/'agents.duckdb'
    initialize_database(path)
    return Settings('fake-only','fake','fake',database=path)


class LocalIndex:
    """Fonte real de documento, busca simulada; não prova busca semântica remota."""
    def synchronize(self):
        return 3

    def search(self,question):
        return [{'source':'politica_comercial.md','chunk':1,
                 'text':(ROOT/'data/documents/politica_comercial.md').read_text(encoding='utf-8')}]


class FakeGateway:
    def __init__(self,settings):
        self.calls=[]

    def stream(self,history,context):
        self.calls.append(context)
        yield 'Síntese de teste baseada nas ferramentas.'

    def close(self):
        pass


@pytest.mark.parametrize('question',TASKS)
def test_three_composed_tasks_share_real_database_and_model(settings,question):
    tools=SystemTools(settings.database,LocalIndex())
    runner=AgentOrchestrator(settings,use_llm=False,tools=tools)
    history=[{'role':'user','content':question}]
    result=runner.prepare(history)
    answer=''.join(runner.stream_answer(result,history))
    assert result.agents==['estoque','comercial']
    assert all(row['status']=='ok' for row in result.state.trace)
    assert result.state.results['estoque']['abastecimento']['totais']['rupturas_observadas']==60
    assert result.state.results['comercial']['indicadores']['totais']['receita_faturada']==Decimal('493126517.02')
    impact=result.state.results['comercial']['impacto_compartilhado']
    assert impact['pares_consultados']==20
    assert any(row.get('depends_on')=='estoque.duckdb_estoque_pedidos' for row in result.state.trace)
    assert 'Resumo factual' in answer and 'amostra' in answer
    if 'backorder' in question:
        assert result.state.results['estoque']['ml']['score']==pytest.approx(.9266898444319546)


def test_impact_reconciles_selected_pairs_without_row_multiplication(settings):
    tools=SystemTools(settings.database)
    stock=tools.stock_and_orders()
    pairs=[(r['produto_id'],r['centro_id']) for r in stock['prioridades_amostra']]
    result=tools.commercial_impact(pairs+pairs)
    measured=sum(row['carteira_pendente'] for row in result['por_familia'])
    expected=sum(row['carteira_valor'] for row in stock['prioridades_amostra'])
    assert measured==expected
    assert result['pares_consultados']==20
    assert len(result['por_familia'])<=20
    assert stock['totais']['carteira_nos_pares_sinalizados']>=measured


def test_invalid_inputs_and_sql_injection_cannot_become_queries(settings):
    tools=SystemTools(settings.database)
    for pairs in [[('1); DROP TABLE vendas;--',1)],[(1,1)]*21+[(2,2)],[(True,1)]]:
        if len(pairs)>20 and len(set(pairs))<=20:
            pairs=[(index,1) for index in range(1,22)]
        with pytest.raises(ValueError):
            tools.commercial_impact(pairs)
    tools.commercial('DROP TABLE vendas; DELETE FROM clientes;')
    with duckdb.connect(str(settings.database),read_only=True) as connection:
        assert connection.execute('SELECT COUNT(*) FROM vendas').fetchone()[0]==20000


def test_missing_ml_fields_never_call_predictor(settings,monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('Não deve inferir atributos ausentes')
    monkeypatch.setattr('agro_ai.agents.tools.predict_risk',forbidden)
    runner=AgentOrchestrator(settings,use_llm=False,tools=SystemTools(settings.database,LocalIndex()))
    result=runner.prepare([{'role':'user','content':'Preveja risco de ruptura do PRD-00001 e impacto comercial.'}])
    assert result.state.results['estoque']['ml']['status']=='needs_input'
    assert any(row['status']=='needs_input' for row in result.state.trace)


def test_agent_analysis_and_final_synthesis_receive_shared_results(settings):
    runner=AgentOrchestrator(settings,FakeGateway,use_llm=True,tools=SystemTools(settings.database,LocalIndex()))
    history=[{'role':'user','content':TASKS[0]}]
    prepared=runner.prepare(history)
    answer=''.join(runner.stream_answer(prepared,history))
    assert len(runner.gateway.calls)==3
    assert 'prioridades_amostra' not in runner.gateway.calls[1]  # Compartilha os resultados relevantes, sem repetir todo o estoque.
    assert 'impacto_compartilhado' in runner.gateway.calls[1]
    assert 'analises' in runner.gateway.calls[2]
    assert answer=='Síntese de teste baseada nas ferramentas.'
    assert prepared.state.trace[-1]['tool']=='gemini_sintese'
    assert prepared.state.trace[-1]['status']=='ok'


def test_api_failure_returns_explicit_factual_summary(settings):
    class FailingGateway(FakeGateway):
        def stream(self,*args,**kwargs):
            raise ServerError(503,{'error':{'message':'PRIVATE API KEY'}})
    runner=AgentOrchestrator(settings,FailingGateway,tools=SystemTools(settings.database,LocalIndex()))
    history=[{'role':'user','content':TASKS[0]}]
    prepared=runner.prepare(history)
    answer=''.join(runner.stream_answer(prepared,history))
    assert 'sem síntese do Gemini' in answer
    assert 'PRIVATE' not in str(prepared.state.trace) and 'PRIVATE' not in answer
    assert any(row['status']=='failed' and row['http']==503 for row in prepared.state.trace)


def test_simple_routes_and_followup(settings):
    assert plan_agents('Qual a política de descontos?')==['comercial']
    assert plan_agents('Quantas rupturas de estoque existem?')==['estoque']
    runner=AgentOrchestrator(settings,use_llm=False,tools=SystemTools(settings.database,LocalIndex()))
    result=runner.prepare([{'role':'user','content':'Quais rupturas existem?'},
                          {'role':'assistant','content':'Resposta anterior.'},
                          {'role':'user','content':'E qual o impacto nas margens?'}])
    assert result.agents==['estoque','comercial']


def test_compound_chat_persists_tool_evidence(settings,monkeypatch):
    from streamlit.testing.v1 import AppTest
    import agro_ai.config
    import agro_ai.gemini
    import agro_ai.rag
    monkeypatch.setattr(agro_ai.config,'get_settings',lambda:settings)
    monkeypatch.setattr(agro_ai.gemini,'GeminiGateway',FakeGateway)
    monkeypatch.setattr(agro_ai.rag,'DocumentIndex',lambda *args:LocalIndex())
    app=AppTest.from_file(str(ROOT/'app.py')).run(timeout=30)
    app.chat_input[0].set_value(TASKS[0]).run(timeout=30)
    assert not app.exception
    saved=app.session_state['messages'][-1]
    assert {'estoque','comercial'} <= {entry['agent'] for entry in saved['tools']}
    assert any(entry.get('depends_on') for entry in saved['tools'])
    assert any(expander.label=='Agentes e ferramentas consultadas' for expander in app.expander)
    app.run(timeout=30)
    assert app.session_state['messages'][-1]['tools']==saved['tools']


def test_compound_ml_rejects_probability_claim_before_display(settings):
    class MisleadingGateway(FakeGateway):
        def stream(self,*args,**kwargs):
            yield 'A previsão ML indica a probabilidade de falta do produto.'
    runner=AgentOrchestrator(settings,MisleadingGateway,tools=SystemTools(settings.database,LocalIndex()))
    history=[{'role':'user','content':TASKS[2]}]
    prepared=runner.prepare(history)
    answer=''.join(runner.stream_answer(prepared,history))
    assert 'sem síntese do Gemini' in answer
    assert 'score 0.9267' in answer
    assert 'indica a probabilidade' not in answer
    assert prepared.state.trace[-1]['status']=='rejected'


def test_missing_agent_analysis_is_degraded_not_factual_fallback(settings):
    from google.genai.errors import ClientError
    class Gateway(FakeGateway):
        def stream(self,history,context):
            self.calls.append(context)
            if len(self.calls)==2:
                raise ClientError(429,{'error':{'message':'SECRET'}})
            yield 'Síntese disponível.'
    runner=AgentOrchestrator(settings,Gateway,tools=SystemTools(settings.database,LocalIndex()))
    history=[{'role':'user','content':TASKS[0]}]
    prepared=runner.prepare(history)
    answer=''.join(runner.stream_answer(prepared,history))
    assert prepared.state.answer_mode=='gemini'
    assert answer.startswith('Síntese disponível.')
    assert 'análise desse agente ficou incompleta' in answer
    assert prepared.state.trace[-1]['status']=='ok'
    assert any(row['status']=='failed' and row.get('http')==429 for row in prepared.state.trace)
    assert 'SECRET' not in answer


def test_factual_fallback_warns_synthesis_failure_and_keeps_real_totals(settings):
    class Gateway(FakeGateway):
        def stream(self,*args,**kwargs):
            raise ServerError(503,{'error':{'message':'SECRET'}})
    runner=AgentOrchestrator(settings,Gateway,tools=SystemTools(settings.database,LocalIndex()))
    history=[{'role':'user','content':TASKS[0]}]
    prepared=runner.prepare(history)
    answer=''.join(runner.stream_answer(prepared,history))
    assert prepared.state.answer_mode=='factual'
    assert 'Resposta incompleta' in answer
    assert 'R$ 4.399.084,73' in answer and 'R$ 493.126.517,02' in answer
