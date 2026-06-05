"""
Embedder — calls Gemini embedding API (gemini-embedding-001).

768-dimension vectors, matches the pgvector HNSW index on index_chunks.
Fully async — no local model, no GPU/CPU inference on Railway.
"""

import logging
import math
import httpx
from config import config

logger = logging.getLogger(__name__)

EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    f"/{config.GEMINI_EMBEDDING_MODEL}:batchEmbedContents"
)
BATCH_SIZE = 100   # Gemini batchEmbedContents limit


def _normalize(v: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return v
    return [x / norm for x in v]


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of strings. Returns list of 768-dim float vectors."""
    if not texts:
        return []

    results: list[list[float]] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            payload = {
                "requests": [
                    {
                        "model": f"models/{config.GEMINI_EMBEDDING_MODEL}",
                        "content": {"parts": [{"text": t}]},
                        "outputDimensionality": config.GEMINI_EMBEDDING_DIMS,
                    }
                    for t in batch
                ]
            }
            resp = await client.post(
                EMBED_URL,
                params={"key": config.GEMINI_API_KEY},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            for emb in data["embeddings"]:
                results.append(_normalize(emb["values"]))

    return results


async def embed_one(text: str) -> list[float]:
    vectors = await embed([text])
    return vectors[0]
