import pytest
from contextlib import nullcontext


@pytest.fixture(autouse=True)
def disable_remote_observability_in_tests(monkeypatch):
    """Não exportar conversas simuladas dos testes para o serviço remoto."""
    monkeypatch.setenv('LANGFUSE_ENABLED','false')
    # Chamadas SDK são mockadas nos testes funcionais; testar limites separadamente.
    monkeypatch.setattr('agro_ai.gemini.request_slot',lambda *args,**kwargs:nullcontext())
    monkeypatch.setattr('agro_ai.evaluation.judge.request_slot',lambda *args,**kwargs:nullcontext())
