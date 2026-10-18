"""Adaptador do SDK Google GenAI para embeddings e geração incremental."""
import time

from google import genai
from google.genai import types
from google.genai.errors import APIError

from agro_ai.config import Settings
from agro_ai.diagnostics import EmptyResponseError, LOGGER
from agro_ai.observability import observation,observe,annotate_current
from agro_ai.api_limits import request_slot,limit_evidence


class GeminiGateway:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise ValueError('Configure GEMINI_API_KEY no arquivo .env.')
        self.settings = settings
        self.client = genai.Client(
            vertexai=False,
            api_key=settings.api_key,
            http_options=types.HttpOptions(timeout=30000,
                                          retry_options=types.HttpRetryOptions(attempts=1)),
        )

    def close(self):
        self.client.close()

    @observe('gemini.embeddings',as_type='embedding')
    def embed(self, texts: list[str], *, query: bool = False) -> list[list[float]]:
        annotate_current(model_name=self.settings.embedding_model,input_characters=sum(map(len,texts)))
        with request_slot(self.settings,self.settings.embedding_model,'retrieval'):
            response = self.client.models.embed_content(
                model=self.settings.embedding_model,
                contents=texts,
                config=types.EmbedContentConfig(
                    task_type='RETRIEVAL_QUERY' if query else 'RETRIEVAL_DOCUMENT',
                    output_dimensionality=768,
                ),
            )
        if not response.embeddings or len(response.embeddings) != len(texts):
            raise ValueError('A API não retornou todos os embeddings.')
        vectors = [item.values for item in response.embeddings]
        if any(not vector for vector in vectors):
            raise ValueError('A API retornou um embedding vazio.')
        return vectors

    def stream(self, history: list[dict], system: str):
        contents = [types.Content(
            role='model' if item['role'] == 'assistant' else 'user',
            parts=[types.Part.from_text(text=item['content'])],
        ) for item in history]
        for attempt in range(2):
            received = False
            try:
                with observation('gemini.generate',as_type='generation',
                                 model_name=self.settings.model,attempt=attempt+1) as span:
                    started=time.perf_counter()
                    with request_slot(self.settings,self.settings.model):
                        for chunk in self.client.models.generate_content_stream(
                            model=self.settings.model, contents=contents,
                            config=types.GenerateContentConfig(system_instruction=system, temperature=0.2),
                        ):
                            span.usage(getattr(chunk,'usage_metadata',None))
                            if getattr(chunk,'model_version',None):
                                span.update(model_version=chunk.model_version)
                            if chunk.text:
                                if not received:
                                    span.update(first_token_ms=round((time.perf_counter()-started)*1000,3))
                                received = True
                                yield chunk.text
                    if not received:
                        raise EmptyResponseError()
                return
            except APIError as error:
                # Uma repetição somente para 503 antes de qualquer texto entregue.
                # Nunca repetir resposta parcial nem erros de chave/cota/modelo.
                if error.code != 503 or received or attempt == 1 or limit_evidence(error)['retry_after_seconds'] is not None:
                    raise
                LOGGER.warning('generation_retry http=503 attempt=2 delay_seconds=1')
                time.sleep(1)
