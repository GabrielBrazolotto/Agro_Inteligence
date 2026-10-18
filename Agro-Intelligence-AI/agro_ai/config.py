"""Configuração centralizada; segredos somente no ambiente."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    api_key: str = field(repr=False)
    model: str
    embedding_model: str
    database: Path = ROOT / 'data/runtime/cooperativa_v2.duckdb'
    chroma_dir: Path = ROOT / 'data/runtime/chroma'
    documents: Path = ROOT / 'data/documents'
    agent_model: str = ''
    judge_model: str = ''
    request_interval_seconds: float = 0


def get_settings() -> Settings:
    # Releitura a cada rerun; variáveis explícitas do processo têm precedência.
    values = dotenv_values(ROOT / '.env', encoding='utf-8-sig', interpolate=False)
    def value(name, default=''):
        return (os.environ.get(name, values.get(name)) or default).strip()
    model=value('GEMINI_MODEL', 'gemini-3.5-flash')
    agent=value('GEMINI_AGENT_MODEL',model)
    judge=value('GEMINI_JUDGE_MODEL',agent)
    interval=float(value('GEMINI_MIN_INTERVAL_SECONDS','15'))
    if not 0<=interval<=60:
        raise ValueError('GEMINI_MIN_INTERVAL_SECONDS deve estar entre 0 e 60.')
    return Settings(
        api_key=value('GEMINI_API_KEY'),
        model=model,
        embedding_model=value('GEMINI_EMBEDDING_MODEL', 'gemini-embedding-001'),
        agent_model=agent,judge_model=judge,request_interval_seconds=interval,
    )
