"""RAG persistente com índice identificado pelo conteúdo e modelo de embedding."""
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from agro_ai.observability import observe


def split_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('Tamanho e sobreposição de chunks inválidos.')
    return [text[start:start + size] for start in range(0, len(text), size - overlap)
            if text[start:start + size].strip()]


class DocumentIndex:
    def __init__(self, directory: Path, documents: Path, gateway):
        self.gateway = gateway
        self.chunks = []
        for path in sorted(documents.glob('*.md')):
            for number, chunk in enumerate(split_text(path.read_text(encoding='utf-8'))):
                self.chunks.append((f'{path.name}:{number}', chunk,
                                    {'source': path.name, 'chunk': number + 1}))
        if not self.chunks:
            raise ValueError('Nenhum documento Markdown encontrado.')
        signature = json.dumps(
            [gateway.settings.embedding_model, 768, self.chunks], ensure_ascii=False,
        )
        name = 'comercial-' + hashlib.sha256(signature.encode()).hexdigest()[:24]
        self.client = chromadb.PersistentClient(
            path=str(directory), settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=name, embedding_function=None, metadata={'hnsw:space': 'cosine'},
        )

    @observe('chroma.synchronize')
    def synchronize(self) -> int:
        existing = set(self.collection.get()['ids'])
        missing = [chunk for chunk in self.chunks if chunk[0] not in existing]
        if missing:
            embeddings = self.gateway.embed([chunk[1] for chunk in missing])
            self.collection.upsert(
                ids=[chunk[0] for chunk in missing],
                documents=[chunk[1] for chunk in missing],
                metadatas=[chunk[2] for chunk in missing], embeddings=embeddings,
            )
        return self.collection.count()

    @observe('chroma.retrieve',as_type='retriever')
    def search(self, question: str, limit: int = 3) -> list[dict]:
        if self.collection.count() == 0:
            return []
        result = self.collection.query(
            query_embeddings=self.gateway.embed([question], query=True),
            n_results=min(limit, self.collection.count()),
            include=['documents', 'metadatas', 'distances'],
        )
        return [dict(text=text, source=meta['source'], chunk=meta['chunk'], distance=distance)
                for text, meta, distance in zip(result['documents'][0],
                                                result['metadatas'][0], result['distances'][0])]
