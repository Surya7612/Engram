import hashlib
import math
from typing import Iterable

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from engram.config import Settings
from engram.provenance.helpers import artifact_point_id

EMBED_DIM = 384


def _hash_embed(text: str, dim: int = EMBED_DIM) -> list[float]:
    """Deterministic local fallback when OpenAI is unavailable."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for i in range(dim):
        byte = digest[i % len(digest)]
        values.append((byte / 255.0) * 2 - 1)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


class EmbeddingClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        key = (settings.openai_api_key or "").strip() or None
        self._openai = OpenAI(api_key=key) if key else None

    @property
    def uses_openai(self) -> bool:
        return self._openai is not None

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        items = list(texts)
        if not items:
            return []
        if self._openai:
            response = self._openai.embeddings.create(
                model=self._settings.openai_embedding_model,
                input=items,
            )
            return [row.embedding for row in response.data]
        return [_hash_embed(text) for text in items]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class VectorStore:
    def __init__(self, settings: Settings, embedder: EmbeddingClient):
        self._settings = settings
        self._embedder = embedder
        self._collection = settings.qdrant_collection
        if settings.store == "local":
            local_path = settings.local_data_dir / "qdrant"
            local_path.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(local_path))
        else:
            self._client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)

    def ping(self) -> bool:
        try:
            self._client.get_collections()
            return True
        except Exception:
            return False

    def ensure_collection(self) -> None:
        dim = 1536 if self._embedder.uses_openai else EMBED_DIM
        names = {c.name for c in self._client.get_collections().collections}
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
            )

    def reset_collection(self) -> None:
        names = {c.name for c in self._client.get_collections().collections}
        if self._collection in names:
            self._client.delete_collection(self._collection)
        self.ensure_collection()

    def upsert_artifact(
        self,
        point_id: str,
        text: str,
        payload: dict,
    ) -> None:
        vector = self._embedder.embed_one(text)
        self._client.upsert(
            collection_name=self._collection,
            points=[
                qmodels.PointStruct(
                    id=artifact_point_id(point_id),
                    vector=vector,
                    payload={**payload, "text": text, "point_key": point_id},
                )
            ],
        )

    def search(self, query: str, top_k: int = 8, service_id: str | None = None) -> list[dict]:
        vector = self._embedder.embed_one(query)
        query_filter = None
        if service_id:
            query_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="service_ids",
                        match=qmodels.MatchAny(any=[service_id]),
                    )
                ]
            )
        result = self._client.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
            query_filter=query_filter,
        )
        return [
            {
                "score": hit.score,
                "payload": hit.payload or {},
            }
            for hit in result.points
        ]

    def close(self) -> None:
        closer = getattr(self._client, "close", None)
        if callable(closer):
            closer()
