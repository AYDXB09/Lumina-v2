"""
Embedder — wraps sentence-transformers all-MiniLM-L6-v2.

384-dimension vectors, matches the pgvector HNSW index on index_chunks.
Singleton — model loaded once on first use.
"""

from functools import lru_cache
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings. Returns list of 384-dim float vectors."""
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
