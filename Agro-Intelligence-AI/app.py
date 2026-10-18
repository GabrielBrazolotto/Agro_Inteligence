"""Interface Streamlit do assistente comercial."""
import streamlit as st

from agro_ai.assistant import prepare_context
from agro_ai.config import get_settings
from agro_ai.database import commercial_snapshot, initialize_database
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.config import ROOT
from agro_ai.synthetic import TABLES
from agro_ai.ml.inference import ml_chat_response, is_prediction_request
from agro_ai.ml.schema import EXAMPLE as ML_EXAMPLE, ARTIFACT_DIR
from agro_ai.agents.orchestrator import AgentOrchestrator, plan_agents
from agro_ai.chatflow import ChatTurn
from agro_ai.observability import chat_request,observation,annotate_current,complete_chat
from agro_ai.diagnostics import (ChatFailure, EmptyResponseError, LOGGER,
                                 configure_logging, operation)

configure_logging()

st.set_page_config(page_title='Agro Intelligence AI', page_icon='🌱', layout='wide')
st.title('🌱 Agro Intelligence AI')
st.caption('AI Factory • PUCPR | Base comercial fictícia • ML com dataset público externo')
settings = get_settings()


@st.cache_resource
def initialize(path, dataset_stamp):
    initialize_database(path)
    return True


try:
    dataset_stamp = tuple(((ROOT / 'data/seeds' / f'{table}.csv').stat().st_mtime_ns,
                           (ROOT / 'data/seeds' / f'{table}.csv').stat().st_size) for table in TABLES)
    initialize(settings.database, dataset_stamp)
    snapshot = commercial_snapshot(settings.database)
except Exception:
    st.error('Não foi possível abrir o banco local. Verifique as permissões de data/runtime.')
    st.stop()

with st.sidebar:
    st.header('Base comercial simulada')
    counts = snapshot['contagens']
    st.write(f"{counts['clientes']:,} clientes • {counts['produtos']:,} produtos • "
             f"{counts['vendas']:,} linhas comerciais • {counts['pedidos']:,} pedidos")
    st.caption(f"{counts['centros']} centros • {counts['regioes']} regiões • "
               f"{counts['estoque']:,} posições de estoque • "
               f"{len(list(settings.documents.glob('*.md')))} documentos RAG")
    st.caption(f'Modelo: {settings.model}')
    st.caption(f'Agentes: {settings.agent_model or settings.model}')
    st.caption(f'Juiz LLM: {settings.judge_model or settings.agent_model or settings.model}')
    if st.button('Limpar conversa'):
        st.session_state.messages = []
        st.rerun()
    st.markdown('**Experimente:**')
    st.write('Qual a receita faturada por cliente?')
    st.write('Qual a política de descontos e o prazo de entrega?')
    st.write('Como o faturamento evoluiu por mês e região?')
    st.write('Quais famílias têm menor margem e quantas rupturas existem?')
    st.caption('Agentes especializados: Estoque e Comercial. Tarefas compostas compartilham resultados.')
    st.markdown('**Previsão ML experimental de backorder**')
    st.caption('Dataset público externo; não treinado com os dados sintéticos da cooperativa.')
    st.code(ML_EXAMPLE, language=None)
    if (ARTIFACT_DIR / 'metadata.json').exists():
        with st.expander('Avaliação do modelo ML'):
            import json
            try:
                report = json.loads((ARTIFACT_DIR / 'metadata.json').read_text(encoding='utf-8'))
                st.write({'registros_utilizados': report['used_rows'],
                          'teste': report['splits']['test']['rows'],
                          'metricas_teste': report['test_metrics']})
                st.caption('Métricas no dataset público, sem validação no agro brasileiro.')
                matrix = ROOT / 'reports/ml/confusion_matrix.png'
                if matrix.exists():
                    st.image(str(matrix), caption='Teste reservado: linhas reais × colunas previstas')
            except Exception:
                st.caption('Relatório indisponível. Execute o treinamento local.')
    st.caption('O histórico permanece somente nesta sessão. A API recebe as mensagens, '
               'os dados fictícios e os trechos recuperados. Chamadas podem consumir cota.')

totals = snapshot['totais']
st.caption(f"Período sintético: {totals['inicio']} a {totals['fim']}. "
           'Margem comercial bruta; carteira pendente não é faturamento. '
           'Dados não representam resultados de uma cooperativa real nem avaliação de ML.')
def brl(value):
    return 'R$ ' + f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
columns = st.columns(3)
columns[0].metric('Receita faturada', brl(totals['receita_faturada']))
columns[1].metric('Carteira pendente', brl(totals['carteira_pendente']))
columns[2].metric('Margem sobre faturadas', brl(totals['margem_faturada']))
with st.expander('Consultar dados comerciais'):
    st.caption('Resultados limitados a 20 linhas por consulta; totais calculados sobre a base completa.')
    for label, key in [('Vendas por status', 'resumo'), ('Faturamento mensal', 'mensal'),
                       ('Regiões', 'por_regiao'), ('Famílias', 'por_familia'),
                       ('Centros', 'por_centro'), ('Maiores clientes', 'receita_por_cliente'),
                       ('Estoque por unidade', 'estoque_resumo'), ('Amostra de alertas', 'alertas_estoque'),
                       ('Amostra de linhas comerciais', 'vendas')]:
        st.markdown(f'**{label}**')
        st.dataframe(snapshot[key], use_container_width=True)

if not settings.api_key:
    st.info('Para respostas comerciais e RAG, configure GEMINI_API_KEY no .env '
            'e reinicie o Streamlit. Dados comerciais e inferência ML local funcionam sem chave '
            'quando o artefato treinado está disponível.')

if 'messages' not in st.session_state:
    st.session_state.messages = []


def show_sources(sources):
    if sources:
        with st.expander('Trechos recuperados para esta resposta'):
            for item in sources:
                st.markdown(f'**{item["source"]} — trecho {item["chunk"]}**')
                st.text(item['text'])


def show_tools(trace):
    if trace:
        with st.expander('Agentes e ferramentas consultadas'):
            st.dataframe(trace, use_container_width=True)


for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.markdown(message['content'])
        show_sources(message.get('sources', []))
        show_tools(message.get('tools', []))

if prompt := st.chat_input('Pergunte sobre vendas, documentos ou previsão ML de backorder...',
                            disabled=not settings.api_key and not (ARTIFACT_DIR/'model.joblib').exists(),
                            max_chars=4000):
    history = st.session_state.messages + [{'role': 'user', 'content': prompt}]
    with st.chat_message('user'):
        st.markdown(prompt)
    with st.chat_message('assistant'):
        output = st.empty()
        sources = []
        gateway = None
        orchestrator = None
        turn = None
        prepared = None
        tool_trace = []
        with chat_request(prompt,history):
            try:
                turn=ChatTurn(settings,GeminiGateway,DocumentIndex)
                with st.spinner('Os agentes estão consultando as ferramentas e compartilhando resultados...'):
                    turn.prepare(history)
                    sources=turn.sources
                    tool_trace=turn.tools
                with output.container():
                    answer=st.write_stream(turn.stream())
                complete_chat(answer,tool_trace,turn.answer_mode)
                st.session_state.messages = history + [
                    {'role': 'assistant', 'content': answer, 'sources': sources,'tools':tool_trace}]
                show_sources(sources)
                show_tools(tool_trace)
            except ChatFailure as failure:
                annotate_current(status='failed',error_category=failure.category,http_code=failure.code)
                output.empty()
                st.error(failure.user_message)
                if failure.stage == 'generation':
                    show_sources(sources)
                show_tools(tool_trace)
                st.caption('Esta tentativa não foi adicionada ao histórico. '
                           'Uma resposta parcial, se recebida, foi descartada.')
            finally:
                if turn:
                    try:
                        turn.close()
                    except Exception:
                        LOGGER.warning('agent_client_close_failed')
                if orchestrator:
                    try:
                        orchestrator.close()
                    except Exception:
                        LOGGER.warning('agent_client_close_failed')
                close = getattr(gateway, 'close', None)
                if close:
                    try:
                        close()
                    except Exception:
                        LOGGER.warning('client_close_failed')
