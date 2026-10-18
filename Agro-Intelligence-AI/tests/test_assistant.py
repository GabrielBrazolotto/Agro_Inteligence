from types import SimpleNamespace

from agro_ai.assistant import prepare_context
from agro_ai.database import initialize_database
from agro_ai.gemini import GeminiGateway
import pytest


def test_context_contains_business_data_and_followup_history(tmp_path):
    path = tmp_path / 'commercial.duckdb'
    initialize_database(path)
    class Index:
        def search(self, question):
            assert 'desconto' in question and 'e o prazo?' in question
            return [{'source': 'politica.md', 'chunk': 1, 'text': '5%'}]
    context, sources = prepare_context(
        SimpleNamespace(database=path), Index(),
        [{'role': 'user', 'content': 'desconto'}, {'role': 'user', 'content': 'e o prazo?'}],
    )
    assert '493126517.02' in context
    assert len(context) < 24000
    assert '"vendas": [' not in context
    assert '"catalogo": [' not in context
    assert sources[0]['source'] == 'politica.md'


def test_gateway_stream_maps_roles_and_ignores_empty_chunks():
    captured = {}
    def generate_content_stream(**kwargs):
        captured.update(kwargs)
        return iter([SimpleNamespace(text='Olá'), SimpleNamespace(text=None),
                     SimpleNamespace(text=' mundo')])
    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway.settings = SimpleNamespace(model='fake')
    gateway.client = SimpleNamespace(models=SimpleNamespace(
        generate_content_stream=generate_content_stream))
    result = ''.join(gateway.stream([
        {'role': 'user', 'content': 'Oi'}, {'role': 'assistant', 'content': 'Olá'}], 'sistema'))
    assert result == 'Olá mundo'
    assert [item.role for item in captured['contents']] == ['user', 'model']
    assert captured['config'].system_instruction == 'sistema'


def test_embedding_task_types_and_missing_results():
    captured = []
    def embed_content(**kwargs):
        captured.append(kwargs)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[1., 0.])])
    gateway = GeminiGateway.__new__(GeminiGateway)
    gateway.settings = SimpleNamespace(embedding_model='fake')
    gateway.client = SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))
    assert gateway.embed(['texto']) == [[1., 0.]]
    gateway.embed(['pergunta'], query=True)
    assert [call['config'].task_type for call in captured] == [
        'RETRIEVAL_DOCUMENT', 'RETRIEVAL_QUERY']
    with pytest.raises(ValueError):
        gateway.embed(['um', 'dois'])
