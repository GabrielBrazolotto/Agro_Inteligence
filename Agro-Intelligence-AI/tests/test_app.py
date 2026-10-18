from streamlit.testing.v1 import AppTest


def test_ui_without_key(monkeypatch, tmp_path):
    from agro_ai.config import Settings, ROOT
    import agro_ai.config
    import agro_ai.ml.schema
    monkeypatch.setattr(agro_ai.ml.schema, 'ARTIFACT_DIR', tmp_path/'missing-model')
    # Não ler nem usar credenciais eventualmente existentes no ambiente.
    monkeypatch.setattr(agro_ai.config, 'get_settings', lambda: Settings(
        api_key='', model='fake', embedding_model='fake', database=tmp_path / 'ui.duckdb'))
    app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
    assert not app.exception
    assert app.chat_input[0].disabled
    assert len(app.dataframe) == 9
    assert len(app.metric) == 3
    assert 'Agro Intelligence AI' in app.title[0].value


def test_chat_history_streaming_and_clear(monkeypatch, tmp_path):
    from agro_ai.config import Settings, ROOT
    import agro_ai.config
    import agro_ai.gemini
    import agro_ai.rag

    class Gateway:
        def __init__(self, settings):
            pass

        def stream(self, history, context):
            yield 'Receita faturada: '
            yield 'R$ 56.300,00.'

    class Index:
        def __init__(self, *args):
            pass

        def synchronize(self):
            return 3

        def search(self, query):
            return [{'source': 'politica_comercial.md', 'chunk': 1, 'text': 'Simulação.'}]

    monkeypatch.setattr(agro_ai.config, 'get_settings', lambda: Settings(
        api_key='fake-test-only', model='fake', embedding_model='fake',
        database=tmp_path / 'chat.duckdb'))
    monkeypatch.setattr(agro_ai.gemini, 'GeminiGateway', Gateway)
    monkeypatch.setattr(agro_ai.rag, 'DocumentIndex', Index)
    app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
    app.chat_input[0].set_value('Qual a receita?').run(timeout=30)
    assert not app.exception
    assert len(app.session_state['messages']) == 2
    assert app.session_state['messages'][1]['content'] == 'Receita faturada: R$ 56.300,00.'
    app.run(timeout=30)
    assert len(app.chat_message) == 2
    app.sidebar.button[0].click().run(timeout=30)
    assert app.session_state['messages'] == []


def test_generation_failure_hides_partial_answer_and_keeps_sources(monkeypatch, tmp_path):
    from agro_ai.config import Settings, ROOT
    from google.genai.errors import ClientError
    import agro_ai.config
    import agro_ai.gemini
    import agro_ai.rag

    class Gateway:
        def __init__(self, settings):
            pass

        def stream(self, history, context):
            yield 'PRIVATE PARTIAL RESPONSE'
            raise ClientError(429, {'error': {'message': 'PRIVATE API KEY AND PROMPT'}})

    class Index:
        def __init__(self, *args):
            pass

        def synchronize(self):
            return 3

        def search(self, query):
            return [{'source': 'politica_comercial.md', 'chunk': 1, 'text': 'Documento fictício.'}]

    monkeypatch.setattr(agro_ai.config, 'get_settings', lambda: Settings(
        'fake-only', 'fake', 'fake', database=tmp_path / 'failure.duckdb'))
    monkeypatch.setattr(agro_ai.gemini, 'GeminiGateway', Gateway)
    monkeypatch.setattr(agro_ai.rag, 'DocumentIndex', Index)
    app = AppTest.from_file(str(ROOT / 'app.py')).run(timeout=30)
    app.chat_input[0].set_value('Qual é a política de descontos?').run(timeout=30)
    assert not app.exception
    assert 'geração' in app.error[0].value
    assert 'cota' in app.error[0].value
    assert 'PRIVATE' not in str(app)
    assert app.session_state['messages'] == []
    assert any('Trechos recuperados' in expander.label for expander in app.expander)
