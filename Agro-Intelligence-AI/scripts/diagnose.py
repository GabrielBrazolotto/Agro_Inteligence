"""python -m scripts.diagnose [--live]. Saída somente de metadados seguros."""
import argparse
import json
import re
from dataclasses import replace
from importlib.metadata import version

from google.genai import types
from google.genai.errors import APIError

from agro_ai.config import ROOT, get_settings
from agro_ai.diagnostics import ChatFailure, EmptyResponseError, configure_logging, operation
from agro_ai.gemini import GeminiGateway
from agro_ai.rag import DocumentIndex
from agro_ai.api_limits import request_slot


def safe_api_evidence(error):
    """Examina detalhes em memória, mas retorna somente flags e enums permitidos."""
    raw = error.details if isinstance(error, APIError) else {}
    # Nunca imprimir raw: pode incluir dados da conta ou a chave.
    encoded = json.dumps(raw, default=lambda _: None)
    message = error.message.lower() if isinstance(error, APIError) and isinstance(error.message, str) else ''
    allowed = ('API_KEY_INVALID', 'API_KEY_EXPIRED', 'API_KEY_SERVICE_BLOCKED',
               'API_KEY_HTTP_REFERRER_BLOCKED', 'API_KEY_IP_ADDRESS_BLOCKED',
               'SERVICE_DISABLED', 'BILLING_DISABLED')
    def has_zero(value):
        if isinstance(value, dict):
            return any((key in ('quotaValue', 'quota_value') and str(item) == '0')
                       or has_zero(item) for key, item in value.items())
        return isinstance(value, list) and any(has_zero(item) for item in value)
    return {'http': error.code if isinstance(error, APIError) else None,
            'known_reasons': [reason for reason in allowed if reason in encoded],
            'quota_zero': has_zero(raw),
            'model_not_found_message': 'not found' in message,
            'unsupported_message': 'not supported' in message}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Autoriza chamadas reais, consumindo cota.')
    parser.add_argument('--list-models', action='store_true', help='Lista nomes públicos de modelos Flash.')
    parser.add_argument('--model', help='Modelo alternativo somente para este diagnóstico.')
    parser.add_argument('--nonstream', action='store_true', help='Compara endpoint sem streaming.')
    parser.add_argument('--generation-only', action='store_true')
    args = parser.parse_args()
    configure_logging()
    settings = get_settings()
    if args.model:
        settings = replace(settings, model=args.model)
    print(json.dumps({'env_exists': (ROOT / '.env').is_file(),
                      'key_present': bool(settings.api_key),
                      'google_genai': version('google-genai'),
                      'main_model':settings.model,'agent_model':settings.agent_model or settings.model,
                      'judge_model':settings.judge_model or settings.agent_model or settings.model,
                      'expected_embedding_model': settings.embedding_model == 'gemini-embedding-001'}))
    if not args.live or not settings.api_key:
        print('live_skipped')
        return 2 if args.live else 0
    gateway = GeminiGateway(settings)
    failed = False
    try:
        if args.list_models:
            with operation('configuration'):
                models = [{'name': model.name, 'generation_supported':
                           'generateContent' in (model.supported_actions or [])}
                          for model in gateway.client.models.list()
                          if model.name and re.fullmatch(r'models/gemini-[a-z0-9.-]+', model.name)
                          and 'flash' in model.name]
                print(json.dumps({'available_flash_models': models}))
            return
        # Uma chamada mínima de streaming, sem histórico ou documentos do usuário.
        try:
            with operation('generation'),request_slot(settings,settings.model):
                try:
                    generate = (gateway.client.models.generate_content if args.nonstream else
                                gateway.client.models.generate_content_stream)
                    response = generate(
                        model=settings.model, contents='Responda apenas OK.',
                        config=types.GenerateContentConfig(
                            max_output_tokens=16, thinking_config=types.ThinkingConfig(thinking_budget=0)),
                    )
                    chunks = [response] if args.nonstream else response
                    received = any_text = False
                    for chunk in chunks:
                        received = True
                        any_text = any_text or bool(chunk.text)
                    print(json.dumps({'stream_received': received, 'stream_has_text': any_text}))
                    if not any_text:
                        raise EmptyResponseError()
                except Exception as error:
                    print(json.dumps({'generation': safe_api_evidence(error)}))
                    raise
        except ChatFailure:
            failed = True
        if args.generation_only:
            return 2 if failed else 0
        # Teste RAG separado: sem fallback que mascare falha do provedor de embeddings.
        try:
            with operation('index'):
                index = DocumentIndex(settings.chroma_dir, settings.documents, gateway)
                print(json.dumps({'indexed_before': index.collection.count(),
                                  'document_chunks': len(index.chunks)}))
            with operation('index_sync'):
                try:
                    index.synchronize()
                except Exception as error:
                    print(json.dumps({'index_sync': safe_api_evidence(error)}))
                    raise
            with operation('retrieval'):
                try:
                    hits = index.search('Qual é a política de descontos?')
                except Exception as error:
                    print(json.dumps({'retrieval': safe_api_evidence(error)}))
                    raise
                print(json.dumps({'retrieved_count': len(hits),
                                  'policy_retrieved': any(h['source'] == 'politica_comercial.md' for h in hits)}))
        except ChatFailure:
            failed = True
    finally:
        gateway.client.close()
    return 2 if failed else 0


if __name__ == '__main__':
    try:
        exit_code = main()
    except ChatFailure:
        # A etapa já registrou somente os metadados seguros.
        exit_code = 2
    raise SystemExit(exit_code)
