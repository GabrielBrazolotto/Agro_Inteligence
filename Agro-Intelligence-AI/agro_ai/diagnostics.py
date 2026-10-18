"""Diagnóstico por metadados permitidos; nunca serializa exceções ou requisições."""
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

import httpx
from google.genai.errors import APIError

LOGGER = logging.getLogger('agro_ai')


def configure_logging():
    if not any(getattr(handler, '_agro_safe', False) for handler in LOGGER.handlers):
        handler = logging.StreamHandler()
        handler._agro_safe = True
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    # Bibliotecas HTTP podem registrar URLs/headers. Não habilitar DEBUG do SDK.
    for name in ('httpx', 'httpcore', 'google.genai', 'chromadb'):
        logging.getLogger(name).setLevel(logging.CRITICAL)


class EmptyResponseError(Exception):
    pass


@dataclass
class ChatFailure(Exception):
    stage: str
    category: str
    code: int | None = None
    reference: str = ''

    def __str__(self):
        return f'{self.stage}:{self.category}:{self.code or "local"}:{self.reference}'

    @property
    def user_message(self):
        if self.category in ('daily_limit','cooldown','limit_state_unavailable'):
            message={'daily_limit':'O limite diário deste modelo foi identificado. As novas chamadas estão suspensas até o próximo reset diário.',
                     'cooldown':'As chamadas deste modelo estão pausadas para respeitar Retry-After ou o limite recebido. Aguarde antes de tentar novamente.',
                     'limit_state_unavailable':'Não foi possível verificar o estado local dos limites da API. Consulte o diagnóstico antes de repetir.'}[self.category]
            return f'{message} Referência: {self.reference}.'
        messages = {
            400: 'A API recusou a configuração da solicitação. Verifique a chave, o modelo e os parâmetros.',
            401: 'A autenticação foi recusada. Confira a chave configurada no .env.',
            403: 'A API negou acesso. Confira as permissões e restrições da chave e do projeto.',
            404: 'O modelo ou recurso não foi encontrado. Confira o modelo e sua disponibilidade na conta.',
            429: 'O limite de requisições ou a cota foi atingido. Confira os limites e o faturamento no Google AI Studio antes de tentar novamente.',
            500: 'O Gemini apresentou um erro interno. Tente novamente mais tarde.',
            502: 'O serviço Gemini está temporariamente indisponível. Tente mais tarde.',
            503: 'O serviço Gemini está temporariamente indisponível. Tente mais tarde.',
            504: 'O serviço Gemini excedeu o tempo de resposta. Tente mais tarde.',
        }
        message = messages.get(self.code, {
            'timeout': 'A conexão com a API excedeu o tempo limite. Tente mais tarde.',
            'connection': 'Não foi possível conectar à API. Verifique a conexão, o proxy e o firewall.',
            'empty_response': 'O Gemini não retornou texto utilizável. A resposta pode ter sido bloqueada ou vazia.',
        }.get(self.category, 'Não foi possível concluir esta etapa. Consulte a referência no terminal para diagnóstico.'))
        labels = {'configuration': 'configuração do Gemini', 'index': 'abertura do índice RAG',
                  'index_sync': 'indexação dos documentos RAG', 'retrieval': 'recuperação RAG',
                  'context': 'leitura do contexto comercial', 'generation': 'geração da resposta'}
        return f'Falha na {labels.get(self.stage, "operação")}. {message} Referência: {self.reference}.'


@contextmanager
def operation(stage):
    reference = uuid4().hex[:12]
    LOGGER.info('operation_start stage=%s reference=%s', stage, reference)
    try:
        yield
    except ChatFailure:
        raise
    except Exception as error:
        code = error.code if isinstance(error, APIError) and type(error.code) is int else None
        category = ('api' if isinstance(error, APIError) else
                    'timeout' if isinstance(error, httpx.TimeoutException) else
                    'connection' if isinstance(error, httpx.TransportError) else
                    'empty_response' if isinstance(error, EmptyResponseError) else 'local')
        if isinstance(error,APIError) and error.code==429:
            from agro_ai.api_limits import limit_evidence
            if limit_evidence(error)['daily_limit']:
                category='daily_limit'
        # Não usar str(error), repr(error), exc_info ou traceback: podem conter segredos.
        LOGGER.error('operation_failed stage=%s category=%s http=%s reference=%s',
                     stage, category, code, reference)
        raise ChatFailure(stage, category, code, reference) from None
    else:
        LOGGER.info('operation_ok stage=%s reference=%s', stage, reference)
