from types import SimpleNamespace

import pytest

from agro_ai.rag import DocumentIndex, split_text


class FakeGateway:
    settings = SimpleNamespace(embedding_model='fake-local-test')

    def __init__(self):
        self.calls = 0

    def embed(self, texts, *, query=False):
        self.calls += 1
        # Vetores determinísticos apenas para testar persistência e busca, sem API.
        return [[1., 0., 0.] if 'desconto' in text.lower() else [0., 1., 0.]
                for text in texts]


def test_chunks_overlap_and_validation():
    assert split_text('abcdefghij', 6, 2) == ['abcdef', 'efghij', 'ij']
    assert split_text('') == []
    with pytest.raises(ValueError):
        split_text('abc', 5, 5)


def test_real_chroma_persistence_retrieval_and_changed_document(tmp_path):
    documents = tmp_path / 'docs'
    documents.mkdir()
    (documents / 'politica.md').write_text('Desconto de 5% aprovado.', encoding='utf-8')
    (documents / 'entrega.md').write_text('Entrega em cinco dias.', encoding='utf-8')
    gateway = FakeGateway()
    index = DocumentIndex(tmp_path / 'chroma', documents, gateway)
    assert index.synchronize() == 2
    assert index.synchronize() == 2
    assert gateway.calls == 1
    hits = index.search('desconto', limit=1)
    assert hits[0]['source'] == 'politica.md'
    reopened = DocumentIndex(tmp_path / 'chroma', documents, gateway)
    assert reopened.synchronize() == 2
    assert gateway.calls == 2  # Uma indexação e uma consulta.
    (documents / 'politica.md').write_text('Desconto de 3%.', encoding='utf-8')
    updated = DocumentIndex(tmp_path / 'chroma', documents, gateway)
    assert updated.collection.name != index.collection.name
    updated.synchronize()
    assert '3%' in updated.search('desconto', limit=1)[0]['text']
