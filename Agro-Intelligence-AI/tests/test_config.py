from agro_ai.config import get_settings


def test_env_reload_bom_and_environment_precedence(monkeypatch, tmp_path):
    import agro_ai.config
    monkeypatch.setattr(agro_ai.config, 'ROOT', tmp_path)
    for name in ('GEMINI_API_KEY', 'GEMINI_MODEL', 'GEMINI_EMBEDDING_MODEL'):
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / '.env'
    env.write_text('GEMINI_API_KEY=fake-first\nGEMINI_MODEL=gemini-2.5-flash', encoding='utf-8-sig')
    assert get_settings().api_key == 'fake-first'
    assert 'fake-first' not in repr(get_settings())
    env.write_text('GEMINI_API_KEY=fake-second\n', encoding='utf-8')
    assert get_settings().api_key == 'fake-second'
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-process')
    assert get_settings().api_key == 'fake-process'
    assert get_settings().model == 'gemini-3.5-flash'
